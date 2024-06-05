# Delete activity in a slack channel
import json
import logging
import sys
from datetime import datetime
from pprint import pprint

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
app = App(token=config["slack"]["user_token"])

# Get info for our Slack connection
slack_info = app.client.auth_test()  # type: ignore
print(f'Connected to Slack as "{slack_info["user"]}" with ID {slack_info["user_id"]}')

# Get all activity in the channel
channel_id = "C069Q91GQGY"
response = app.client.conversations_history(channel=channel_id, limit=999)
messages = response["messages"]
# pprint(messages)
print(f"Found {len(messages)} messages in channel {channel_id}")

name_map = {}

for message in messages:
    # Translate user IDs to usernames
    if "user" in message and message["user"] not in name_map:
        response = app.client.users_info(user=message["user"])
        name = response["user"]["profile"]["display_name"]
        if name == "":
            name = response["user"]["name"]
        name_map[message["user"]] = name
    else:
        name = name_map[message["user"]]

    # Delete channel join messages
    if message.get("subtype") == "channel_join":
        print(f"Deleting channel join message from {name} ({message['user']})")
        response = app.client.chat_delete(channel=channel_id, ts=message["ts"])
        continue

    # Delete messages where the root message has been deleted
    if message["text"] == "This message was deleted.":
        print(f"Deleting messages from deleted root message")
        # Get all replies to this message
        response = app.client.conversations_replies(
            channel=channel_id, ts=message["ts"]
        )
        replies = response["messages"]
        # Delete all replies
        for reply in replies:
            if reply["user"] == "USLACKBOT":
                continue
            print(f"Deleting reply from {reply['user']}")
            response = app.client.chat_delete(channel=channel_id, ts=reply["ts"])
        continue

    # Skip messages that are less than two weeks old
    timestamp = datetime.fromtimestamp(float(message["ts"]))
    if (datetime.now() - timestamp).days < 14:
        print(
            f"Skipping message from {name} ({message['user']}) as it is less than two weeks old"
        )
        continue

    # Skip messages from specific user
    if message["user"] in ["UC6T4U150"]:
        print(f"Skipping message from protected user")
        continue

    # Tell us about the message
    print(
        f'Message from {name} ({message["user"]}) at {message["ts"]}: "{message["text"]}"'
    )
    choice = input("Delete this message? (y/N/i) ")
    # choice = "n"
    if choice == "y":
        response = app.client.chat_delete(channel=channel_id, ts=message["ts"])
        print(f"Deleted message from {name} ({message['user']})")

    elif choice == "i":
        pprint(message)
    else:
        print("Skipping")
