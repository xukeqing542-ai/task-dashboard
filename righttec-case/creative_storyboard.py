"""Create an original 8-second typography-only 9:16 video prototype."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess

root = Path(__file__).resolve().parent
out = root / "creative_output"
out.mkdir(exist_ok=True)
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
big = ImageFont.truetype(font_path, 60)
small = ImageFont.truetype(font_path, 35)
cards = [
    ("Too much clutter?", "PROBLEM  /  0-2s", (18, 42, 72)),
    ("Create room to breathe", "BENEFIT  /  2-4s", (27, 78, 83)),
    ("See the setup", "DEMONSTRATION SLOT  /  4-6s", (32, 68, 73)),
    ("Explore the options", "CALL TO ACTION  /  6-8s", (28, 54, 83)),
]
for n, (headline, sub, bg) in enumerate(cards, 1):
    im = Image.new("RGB", (720, 1280), bg)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((68, 318, 652, 880), radius=35, fill=(229, 235, 227))
    d.rounded_rectangle((138, 445, 582, 751), radius=22, outline=(91, 138, 131), width=12)
    d.line((170, 550, 550, 550), fill=(91, 138, 131), width=9)
    d.line((170, 650, 550, 650), fill=(91, 138, 131), width=9)
    d.text((68, 95), headline, font=big, fill="white")
    d.text((68, 1028), sub, font=small, fill="white")
    d.text((68, 1122), "Concept draft | no product claims", font=ImageFont.truetype(font_path, 25), fill=(206, 216, 220))
    im.save(out / f"card{n}.png", optimize=True)

concat = out / "sequence.txt"
concat.write_text("".join(f"file 'card{n}.png'\nduration 2\n" for n in range(1, 5)) + "file 'card4.png'\n", encoding="utf-8")
cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
       "-vf", "fps=15,format=yuv420p", "-c:v", "libx264", "-movflags", "+faststart", str(out / "creative_concept.mp4")]
subprocess.run(cmd, check=True)
print("Video draft:", out / "creative_concept.mp4")
