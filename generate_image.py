from datetime import datetime
import json

from PIL import Image, ImageDraw

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

if "hud" not in config or "json" not in config["hud"] or "image" not in config["hud"]:
    raise ValueError("HUD configuration missing in config.json")

with open(config["hud"]["json"], "r") as f:
    message_data = json.load(f)

try:
    ts = float(message_data["ts"])
except ValueError:
    raise ValueError("Invalid timestamp")

current_time = datetime.now()
past_time = datetime.fromtimestamp(ts)
time_diff = current_time - past_time

seconds = time_diff.seconds
hours = seconds // 3600
minutes = (seconds % 3600) // 60

time_string = ""
if seconds < 1:
    time_string = "Now"
elif minutes < 1:
    time_string = f"{seconds}s ago"
elif hours < 1:
    time_string = f"{minutes}m ago"
else:
    time_string = past_time.strftime("%H:%M")

name_string = message_data["attachments"][0]["fields"][0]["value"]

height = 180
width = 1920
im = Image.new("RGB", (width, height), color=(0, 0, 0))

draw = ImageDraw.Draw(im)

boarder = 20
bar_width = 10
draw.rounded_rectangle(
    (boarder, boarder, boarder + bar_width, height - boarder),
    fill=(255, 0, 0),
    outline=(255, 0, 0),
    radius=10,
)

time_str_left, _, _, _ = draw.textbbox(
    (width - boarder, height / 2), time_string, font_size=140, anchor="rm"
)
max_name_width = time_str_left - boarder * 2 - bar_width

while draw.textlength(name_string, font_size=140) > max_name_width:
    name_string = name_string[:-4] + "..."

draw.text(
    (boarder * 2 + bar_width, height / 2),
    name_string,
    fill=(255, 255, 255),
    font_size=140,
    anchor="lm",
)
# draw.rectangle(draw.textbbox((boarder*2+bar_width, height/2), name_string, font_size=140, anchor='lm'), outline=(255, 0, 0), width=1)

draw.text(
    (width - boarder, height / 2),
    time_string,
    fill=(200, 200, 200),
    font_size=140,
    anchor="rm",
)
# draw.rectangle(draw.textbbox((width-boarder, height/2), time_string, font_size=140, anchor='rm'), outline=(255, 0, 0), width=1)

im.save(config["hud"]["image"])
