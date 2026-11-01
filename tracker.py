import time
import psutil
import sqlite3
import datetime
import subprocess
import threading
import platform
import socket
import atexit
import os
import sys

# Ensure stdout and stderr are available when running under pythonw.exe
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

try:
    import speedtest
except ImportError:
    speedtest = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'network_data.db')

# Single-instance Windows Mutex to strictly prevent duplicate competing tracker daemons
_daemon_mutex_handle = None

def acquire_single_instance_mutex():
    global _daemon_mutex_handle
    if platform.system() == 'Windows':
        try:
            import ctypes
            _daemon_mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, True, "NetPulse_Tracker_Daemon_SingleInstance")
            if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                return False
        except Exception:
            pass
    return True

def _cleanup_mutex():
    global _daemon_mutex_handle
    if _daemon_mutex_handle and platform.system() == 'Windows':
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_daemon_mutex_handle)
        except Exception:
            pass
        _daemon_mutex_handle = None

atexit.register(_cleanup_mutex)

# Native Windows ICMP for ultra-fast ping without spawning PING.EXE subprocess.
# This completely eliminates "PING.EXE - Application Error (0xc0000142)" during Windows shutdown.
_win32_icmp_handle = None
_dest_ip_cache = None

if platform.system() == 'Windows':
    import ctypes
    from ctypes import wintypes

    class IP_OPTION_INFORMATION(ctypes.Structure):
        _fields_ = [
            ('Ttl', ctypes.c_ubyte),
            ('Tos', ctypes.c_ubyte),
            ('Flags', ctypes.c_ubyte),
            ('OptionsSize', ctypes.c_ubyte),
            ('OptionsData', ctypes.c_void_p)
        ]

    class ICMP_ECHO_REPLY(ctypes.Structure):
        _fields_ = [
            ('Address', wintypes.DWORD),
            ('Status', wintypes.ULONG),
            ('RoundTripTime', wintypes.ULONG),
            ('DataSize', wintypes.USHORT),
            ('Reserved', wintypes.USHORT),
            ('Data', ctypes.c_void_p),
            ('Options', IP_OPTION_INFORMATION)
        ]

    try:
        iphlpapi = ctypes.windll.iphlpapi
        iphlpapi.IcmpCreateFile.restype = wintypes.HANDLE
        iphlpapi.IcmpCloseHandle.argtypes = [wintypes.HANDLE]
        iphlpapi.IcmpCloseHandle.restype = wintypes.BOOL
        iphlpapi.IcmpSendEcho.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.WORD,
            ctypes.c_void_p,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD
        ]
        iphlpapi.IcmpSendEcho.restype = wintypes.DWORD
        HAS_WIN32_ICMP = True
    except Exception:
        HAS_WIN32_ICMP = False
else:
    HAS_WIN32_ICMP = False

def _cleanup_icmp():
    global _win32_icmp_handle
    if HAS_WIN32_ICMP and _win32_icmp_handle:
        try:
            iphlpapi.IcmpCloseHandle(_win32_icmp_handle)
        except Exception:
            pass
        _win32_icmp_handle = None

atexit.register(_cleanup_icmp)

# Speedtest suppression state:
# While speedtest is active, we ignore recording bandwidth and program_usage,
# continuously synchronizing baseline counters so zero speedtest traffic pollutes
# the database, inflates monthly consumption, or triggers false anomaly spikes.
_speedtest_active = threading.Event()
_last_speedtest_proc_seen = 0.0

def is_speedtest_active():
    global _speedtest_active, _last_speedtest_proc_seen
    if _speedtest_active.is_set():
        return True
    if time.time() - _last_speedtest_proc_seen < 3.0:
        return True
    return False

def get_ping(host='8.8.8.8', timeout_ms=1000):
    global _win32_icmp_handle, _dest_ip_cache
    if HAS_WIN32_ICMP:
        try:
            if _win32_icmp_handle is None or _win32_icmp_handle == wintypes.HANDLE(-1).value:
                _win32_icmp_handle = iphlpapi.IcmpCreateFile()
                if not _win32_icmp_handle or _win32_icmp_handle == wintypes.HANDLE(-1).value:
                    _win32_icmp_handle = None
                    return -1

            if _dest_ip_cache is None:
                ip_bytes = socket.inet_aton(host)
                _dest_ip_cache = ctypes.c_ulong.from_buffer_copy(ip_bytes).value

            send_data = b'ping'
            reply_buffer = ctypes.create_string_buffer(1024)
            status = iphlpapi.IcmpSendEcho(
                _win32_icmp_handle,
                _dest_ip_cache,
                send_data,
                len(send_data),
                None,
                reply_buffer,
                1024,
                timeout_ms
            )
            if status != 0:
                reply = ICMP_ECHO_REPLY.from_buffer(reply_buffer)
                if reply.Status == 0:  # IP_SUCCESS
                    return int(reply.RoundTripTime)
            return -1
        except Exception:
            _win32_icmp_handle = None
            return -1
    else:
        # Fallback for non-Windows: TCP connect time to port 53 (DNS)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout_ms / 1000.0)
            t0 = time.time()
            s.connect((host, 53))
            t1 = time.time()
            s.close()
            return int((t1 - t0) * 1000)
        except Exception:
            return -1

def run_speedtest():
    global _speedtest_active
    import os
    import platform
    import subprocess
    import json
    
    # Determine the executable name based on the OS
    exe_name = 'speedtest.exe' if platform.system() == 'Windows' else 'speedtest'
    exe_path = os.path.join(BASE_DIR, exe_name)
    
    # Check if the official CLI exists in the folder
    if not os.path.exists(exe_path):
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Speedtest skipped: Official Ookla CLI ({exe_path}) not found. Please download it to enable this feature.")
        return

    # Signal active speedtest so the main tracker ignores network volume during the test
    _speedtest_active.set()
    try:
        for attempt in range(3):
            try:
                # Run official speedtest CLI (suppress window creation on Windows)
                kwargs = {}
                if platform.system() == 'Windows':
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                    
                output = subprocess.check_output([exe_path, '--accept-license', '--accept-gdpr', '-f', 'json'], timeout=60, **kwargs).decode('utf-8')
                data = json.loads(output)
                
                # bandwidth is in Bytes per second, multiply by 8 for bits per second
                dl = data['download']['bandwidth'] * 8
                ul = data['upload']['bandwidth'] * 8
                ping_res = data['ping']['latency']
                
                # Write to DB speedtest table (for ISP SLA & benchmarks)
                st_conn = sqlite3.connect(DB_FILE, timeout=10)
                st_c = st_conn.cursor()
                st_c.execute('PRAGMA journal_mode=WAL;')
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st_c.execute("INSERT INTO speedtest (timestamp, download_bps, upload_bps, ping_ms) VALUES (?, ?, ?, ?)", (now, dl, ul, ping_res))
                st_conn.commit()
                st_conn.close()
                break  # Success, exit retry loop
            except Exception as e:
                print(f"Speedtest failed on attempt {attempt+1}:", e)
                if attempt < 2:
                    time.sleep(15)
    finally:
        # Cooldown: wait 2 seconds to allow socket buffers and trailing packets to clear
        time.sleep(2.0)
        _speedtest_active.clear()

def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    
    # Enable WAL mode for better concurrency
    c.execute('PRAGMA journal_mode=WAL;')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS bandwidth (
            timestamp DATETIME,
            bytes_sent INTEGER,
            bytes_recv INTEGER,
            sent_speed_bps INTEGER,
            recv_speed_bps INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS active_programs (
            timestamp DATETIME,
            program_name TEXT,
            connection_count INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS program_usage (
            timestamp DATETIME,
            program_name TEXT,
            usage_bytes INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ping (
            timestamp DATETIME,
            ping_ms INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS speedtest (
            timestamp DATETIME,
            download_bps REAL,
            upload_bps REAL,
            ping_ms REAL
        )
    ''')
    # High-performance indexes for instant sub-second dashboard loading
    c.execute('CREATE INDEX IF NOT EXISTS idx_bandwidth_timestamp ON bandwidth(timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_prog_usage_timestamp ON program_usage(timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_ping_timestamp ON ping(timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_speedtest_timestamp ON speedtest(timestamp)')
    conn.commit()
    conn.close()

def get_process_name(pid, cache):
    if pid is None:
        return None
    if pid in cache:
        return cache[pid]
    try:
        name = psutil.Process(pid).name()
        cache[pid] = name
        return name
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return "Unknown"

def main():
    # Resilient startup loop in case DB is locked or system is booting
    for _ in range(30):
        try:
            init_db()
            break
        except Exception:
            time.sleep(1)

    conn = None
    for _ in range(30):
        try:
            conn = sqlite3.connect(DB_FILE, timeout=10)
            conn.execute('PRAGMA journal_mode=WAL;')
            break
        except Exception:
            time.sleep(1)

    if not conn:
        return

    c = conn.cursor()
    
    last_io = None
    for _ in range(15):
        try:
            last_io = psutil.net_io_counters()
            if last_io:
                break
        except Exception:
            time.sleep(1)

    if not last_io:
        return

    last_time = time.time()
    
    process_cache = {}
    last_proc_io = {} # pid -> other_bytes
    last_speedtest_time = 0
    
    print("Network tracker started. Press Ctrl+C to stop.")
    try:
        while True:
            try:
                time.sleep(1)
                
                current_io = psutil.net_io_counters()
                current_time = time.time()
                
                # Periodic Speedtest strictly at xx:00 and xx:30
                now_dt = datetime.datetime.now()
                if now_dt.minute in (0, 30):
                    # Ensure it only runs once during that minute
                    if current_time - last_speedtest_time > 120:
                        last_speedtest_time = current_time
                        threading.Thread(target=run_speedtest, daemon=True).start()

                # Ignore bandwidth & process recording if speedtest is actively running
                if is_speedtest_active():
                    # Speedtest is benchmarking the line.
                    # Continuously synchronize baseline counters so zero speedtest traffic
                    # pollutes the database, inflates total GB, or triggers false anomaly spikes.
                    last_io = current_io
                    last_time = current_time
                    continue

                # Ping every 1 second
                current_ping = get_ping()
                
                time_diff = current_time - last_time
                if time_diff <= 0:
                    continue
                    
                sent_speed = max(0, (current_io.bytes_sent - last_io.bytes_sent) / time_diff)
                recv_speed = max(0, (current_io.bytes_recv - last_io.bytes_recv) / time_diff)
                
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                c.execute('''
                    INSERT INTO bandwidth (timestamp, bytes_sent, bytes_recv, sent_speed_bps, recv_speed_bps)
                    VALUES (?, ?, ?, ?, ?)
                ''', (now, current_io.bytes_sent, current_io.bytes_recv, int(sent_speed), int(recv_speed)))
                
                if current_ping != -1:
                    c.execute("INSERT INTO ping (timestamp, ping_ms) VALUES (?, ?)", (now, current_ping))
                    
                last_io = current_io
                last_time = current_time
                
                try:
                    conns = psutil.net_connections(kind='inet')
                    pids = set()
                    
                    for net_conn in conns:
                        if net_conn.status == 'ESTABLISHED' and net_conn.pid:
                            pids.add(net_conn.pid)
                            p_name = get_process_name(net_conn.pid, process_cache)
                            if p_name and 'speedtest' in p_name.lower():
                                _last_speedtest_proc_seen = current_time

                    # Track actual IO bytes per process
                    prog_usage = {}
                    current_pids = set()
                    
                    for pid in pids:
                        try:
                            p = psutil.Process(pid)
                            name = get_process_name(pid, process_cache)
                            if not name or 'speedtest' in name.lower():
                                continue
                            
                            io = p.io_counters()
                            current_other = io.other_bytes
                            current_pids.add(pid)
                            
                            if pid in last_proc_io:
                                delta = current_other - last_proc_io[pid]
                                if delta > 0:
                                    prog_usage[name] = prog_usage.get(name, 0) + delta
                            last_proc_io[pid] = current_other
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
                            continue
                    
                    # Cleanup cache for dead pids
                    dead_pids = set(last_proc_io.keys()) - current_pids
                    for dp in dead_pids:
                        del last_proc_io[dp]

                    for name, usage_bytes in prog_usage.items():
                        c.execute('''
                            INSERT INTO program_usage (timestamp, program_name, usage_bytes)
                            VALUES (?, ?, ?)
                        ''', (now, name, usage_bytes))
                        
                except (psutil.AccessDenied, psutil.Error, OSError):
                    pass
                    
                conn.commit()

            except sqlite3.OperationalError:
                time.sleep(0.5)
            except Exception:
                time.sleep(1)
            
    except KeyboardInterrupt:
        print("Stopping tracker...")
    finally:
        conn.close()

if __name__ == '__main__':
    if not acquire_single_instance_mutex():
        sys.exit(0)
    while True:
        try:
            main()
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(2)
