import requests
import logging
import json
import sys
from slack_bolt import App
from datetime import datetime
from pprint import pprint
import time

# load config from config.json
with open("config.json","r") as f:
    config: dict = json.load(f)

daemon = False

# Get channel ID from arguments
if len(sys.argv) > 1:
    channel_id = sys.argv[1]
elif len(sys.argv) > 2:
    if sys.argv[1] == "-d":
        daemon = True
        channel_id = sys.argv[2]
    else:
        sys.exit("[-d] <channel_id>")
else:
    sys.exit("[-d] <channel_id>")

logging.basicConfig(level=logging.INFO)

# Initiate Slack client
app = App(token=config["slack"]["bot_token"])

# Get our user ID
ID = app.client.auth_test()["user_id"]

while True:
    # Get conversation history
    result = app.client.conversations_history(channel=channel_id)

    conversation_history = result["messages"]

    for message in conversation_history:
        # Check if the message has files
        if 'files' in message.keys():
            # Check if we've already downloaded the file by looking for an emoji reaction
            downloaded = False
            if 'reactions' in message.keys():
                # Check if we've reacted
                for reaction in message["reactions"]:
                    if reaction["name"] == "heavy_check_mark" and ID in reaction["users"]:
                        # We've already downloaded this file
                        downloaded = True
            if not downloaded:
                for file in message["files"]:
                    # Download the file
                    r = requests.get(file["url_private_download"], headers={"Authorization": "Bearer "+config["slack"]["bot_token"]})
                    # Save the file to disk and append an epoch timestamp to the filename
                    with open(f'{config["download_dir"]}/{datetime.timestamp(datetime.now())}.{file["name"]}', "wb") as f:
                        f.write(r.content)
                    # Log the download
                    logging.info("Downloaded file: "+file["name"])
                # Add a reaction to the message
                app.client.reactions_add(channel=channel_id, name="heavy_check_mark", timestamp=message["ts"])
    if daemon:
        # Sleep for 60 seconds
        time.sleep(60)
    else:
        # When not in daemon mode, exit after one loop
        sys.exit()