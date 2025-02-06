# A slack bolt app that monitors for new channels being created and sends a message to a channel
# when a new channel is created. It uses socket mode to connect to slack.

import json

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_logger import SlackFormatter, SlackHandler
import logging

with open("config.json", "r") as f:
    config: dict = json.load(f)

# Set up logging
if config["debug"]:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


# Initializes your app with your bot token and signing secret
app = App(token=config["slack"]["bot_token"])


# Listens for channel creation events
@app.event("channel_created")
def channel_created(event):
    try:
        # Get the channel name
        channel_name = event["channel"]["name"]
        # Get the channel ID
        channel_id = event["channel"]["id"]
        # Get the channel creator's username
        channel_creator = event["channel"]["creator"]

        # Send a message to a preconfigured channel
        # send a message to the channel when it is created
        app.client.chat_postMessage(
            channel=config["slack"]["notification_channel"],
            text=f"New channel created: <#{channel_id}|{channel_name}> by <@{channel_creator}>",
        )
    except Exception:
        logging.error("Could not send message")


if __name__ == "__main__":
    handler = SocketModeHandler(app, config["slack"]["app_token"])
    logging.debug("Ready")
    handler.start()
