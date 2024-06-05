# listen for messages in a slack channel and trigger when certain conditions are met

import json
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import logging
import sys
from pprint import pprint
import door_trigger_functions as trigger_functions

# Check for --debug flag
if len(sys.argv) > 1 and "--debug" in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# Load config from file
with open("config.json", "r") as f:
    config = json.load(f)

# Map of trigger patterns to functions
func_map = {
    "purify": trigger_functions.turn_on_air_purifier,
    "elab": trigger_functions.elab_lights,
}

# Load patterns from file
with open("trigger_patterns.json", "r") as f:
    patterns = json.load(f)

for pattern in patterns:
    for action in patterns[pattern]:
        if action not in func_map:
            raise ValueError(f"Action '{action}' not found in function map")

# Initiate Slack client
app = App(token=config["slack"]["bot_token"])

# Get info for our Slack connection
slack_info = app.client.auth_test()  # type: ignore
print(f'Connected to Slack as "{slack_info["user"]}" with ID {slack_info["user_id"]}')


# Listen for all messages in a specific slack channel
@app.event("message")
def handle_message(message, say):
    if (
        message["channel"] == config["slack"]["trigger_channel"]
        and "subtype" not in message
    ):
        # pprint(message)

        # Rather than trying to pull all text from the various sections of the message (blocks, text, attachments, etc) we can just pull the text from everywhere
        body_string = json.dumps(message)

        # Check if the message contains any of the trigger patterns
        for pattern in patterns:
            if pattern in body_string:
                print(f"Trigger pattern '{pattern}' detected!")
                for action in patterns[pattern]:
                    func_map[action](message=message, app=app, config=config)


# Start the app
if __name__ == "__main__":
    SocketModeHandler(app, config["slack"]["app_token"]).start()
