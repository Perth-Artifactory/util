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

name_string = message_data["attachments"][0]["fields"][0]["value"]

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

# Colour definitions to make things more readable
greyed_out = (100, 100, 100)
light_grey = (200, 200, 200)
white = (255, 255, 255)
blue = (0, 0, 255)
green = (0, 255, 0)
light_blue = (150, 150, 255)

time_string = ""
bar_colour = greyed_out
name_colour = greyed_out
time_colour = light_grey

if seconds < 20:
    time_string = "Now"
    bar_colour = blue
    name_colour = light_blue
    time_colour = light_blue
elif minutes < 1:
    time_string = f"{seconds}s ago"
    bar_colour = blue
    name_colour = white
elif hours < 1:
    time_string = f"{minutes}m ago"
    bar_colour = green
    name_colour = white

height = 180
width = 1920
im = Image.new("RGB", (width, height), color=(0, 0, 0))

draw = ImageDraw.Draw(im)

boarder = 20
bar_width = 10
draw.rounded_rectangle(
    (boarder, boarder, boarder + bar_width, height - boarder),
    fill=bar_colour,
    outline=bar_colour,
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
    name_string if hours < 1 else "No scans in past hour",
    fill=name_colour,
    font_size=140,
    anchor="lm",
)
# draw.rectangle(draw.textbbox((boarder*2+bar_width, height/2), name_string, font_size=140, anchor='lm'), outline=(255, 0, 0), width=1)

draw.text(
    (width - boarder, height / 2),
    time_string,
    fill=time_colour,
    font_size=140,
    anchor="rm",
)
# draw.rectangle(draw.textbbox((width-boarder, height/2), time_string, font_size=140, anchor='rm'), outline=(255, 0, 0), width=1)

im.save(config["hud"]["image"])
