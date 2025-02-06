# Delete activity in a slack channel
import json
import logging
import sys
from datetime import datetime
from pprint import pprint
import time

from slack_bolt import App

# Check for --debug flag
if len(sys.argv) > 1 and "--debug" in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# load config from file
with open("config.json", "r") as f:
    config = json.load(f)

# Initiate Slack client
app = App(token=config["slack"]["bot_token"])

# Get info for our Slack connection
slack_info = app.client.auth_test()  # type: ignore
print(f'Connected to Slack as "{slack_info["user"]}" with ID {slack_info["user_id"]}')

# Get a list of all files
files = []

response = app.client.files_list(count=100)
current_files = response["files"]
pprint(response["paging"])

while True:
    print(len(files))
    for file in current_files:
        files.append(file)
    current_files = []

    if response["paging"]["pages"] > response["paging"]["page"]:
        response = app.client.files_list(count=100, page=response["paging"]["page"] + 1)
        current_files = response["files"]
        pprint(response["paging"])
    else:
        print("Finished")
        break

# Write to file
with open("files.json", "w") as f:
    json.dump(files, f, indent=4)
