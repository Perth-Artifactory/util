import sys
import subprocess
import json
import os

# This script is called by the paperless-ng docker container which doesn't include requests by default
# We need to install it in the container
subprocess.check_call(
    [
        sys.executable,
        "-m",
        "pip",
        "config",
        "set",
        "global.disable-pip-version-check",
        "true",
    ]
)
subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
subprocess.check_call([sys.executable, "-m", "pip", "install", "slack_bolt"])

from slack_bolt import App

# Depending on deployment this script won't have access to config.json so try loading there first and fall back if not
try:
    with open("config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {
        "slack": {
            "bot_token": "xoxb-",
            "notification_channel": "C",
        }
    }

if config["slack"]["bot_token"] == "xoxb-":
    sys.exit("No config.json file found and no default values provided")

# Initiate slack app
app = App(token=config["slack"]["bot_token"])

DOCUMENT_ID = os.getenv("DOCUMENT_ID")
DOCUMENT_FILE_NAME = os.getenv("DOCUMENT_FILE_NAME")
DOCUMENT_CORRESPONDENT = os.getenv("DOCUMENT_CORRESPONDENT")
DOCUMENT_DOWNLOAD_URL = os.getenv("DOCUMENT_DOWNLOAD_URL")
DOCUMENT_CREATED = os.getenv("DOCUMENT_CREATED")

if not DOCUMENT_CORRESPONDENT or DOCUMENT_CORRESPONDENT == "None":
    DOCUMENT_CORRESPONDENT = "UNKNOWN"

# get command line arguments

message = f"<https://receipts.tele.artifactory.org.au/documents/{DOCUMENT_ID}/details|{DOCUMENT_FILE_NAME}> (for {DOCUMENT_CORRESPONDENT} at {DOCUMENT_CREATED}) was added to the <https://receipts.tele.artifactory.org.au|receipt store>.\nYou can download it from <https://receipts.tele.artifactory.org.au{DOCUMENT_DOWNLOAD_URL}|here> if needed."

# Send the message to the configured slack channel
response = app.client.chat_postMessage(
    channel=config["slack"]["notification_channel"],
    text=message,
    username="Receipts",
    icon_emoji=":receipt:",
)
