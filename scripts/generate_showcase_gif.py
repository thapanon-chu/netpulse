import os
from PIL import Image

ASSETS_DIR = r"C:\Users\NussyEiEi\Desktop\code\Try\Network_rec\assets"

files = [
    os.path.join(ASSETS_DIR, "screen_live_telemetry.png"),
    os.path.join(ASSETS_DIR, "screen_process_attribution.png"),
    os.path.join(ASSETS_DIR, "screen_diagnostics_sla.png"),
    os.path.join(ASSETS_DIR, "screen_capacity_trends.png"),
]

# Target dimensions for optimal GitHub README rendering (crisp on high-DPI displays)
TARGET_WIDTH = 960
TARGET_HEIGHT = 600

images = []
for f in files:
    img = Image.open(f).convert("RGB")
    img_resized = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    images.append(img_resized)

frames = []
durations = []

# Hold durations in ms: Screen 1 held for 4000ms, screens 2-4 held for 2500ms
hold_times = [4000, 2500, 2500, 2500]

n = len(images)
for i in range(n):
    curr_img = images[i]
    next_img = images[(i + 1) % n]
    
    # Static hold frame
    frames.append(curr_img)
    durations.append(hold_times[i])
    
    # 4 crossfade transition frames (75ms each = 300ms transition)
    for step in range(1, 4):
        alpha = step / 4.0
        blended = Image.blend(curr_img, next_img, alpha)
        frames.append(blended)
        durations.append(75)

# Convert all frames to adaptive palette with dithering for high quality
converted_frames = []
for fr in frames:
    # Convert to P mode with 256 colors adaptive palette
    p_fr = fr.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
    converted_frames.append(p_fr)

out_path = os.path.join(ASSETS_DIR, "app_showcase.gif")
converted_frames[0].save(
    out_path,
    save_all=True,
    append_images=converted_frames[1:],
    duration=durations,
    loop=0,
    optimize=True
)

file_size_kb = os.path.getsize(out_path) / 1024
print(f"Generated {out_path}: {file_size_kb:.2f} KB, {len(frames)} frames")
