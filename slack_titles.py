import json
import logging
import sys
import time
from pprint import pprint

import requests
from slack_bolt import App

import errors

# Check for --debug flag
if len(sys.argv) > 1 and "--debug" in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


def get_tidyhq():
    logging.debug("Attempting to get contact dump from TidyHQ...")
    try:
        r = requests.get(
            "https://api.tidyhq.com/v1/contacts",
            params={"access_token": config["tidyhq"]["token"]},
        )
        contacts = r.json()
    except requests.exceptions.RequestException:
        logging.error(errors.tidyhq_connect)
        return False
    c = {}
    for contact in contacts:
        if contact["id"] in config["slack"]["membership_ignore"]:
            continue
        slack = ""
        title = ""
        for field in contact["custom_fields"]:
            if field["id"] == config["tidyhq"]["ids"]["slack"] and field["value"]:
                slack: str = field["value"]
            elif field["id"] == config["tidyhq"]["ids"]["title"] and field["value"]:
                title: str = field["value"]

        # This script only deals with people that are linked in Slack
        if not slack:
            continue

        # We only care about people with titles
        if title:
            c[slack] = {
                "id": contact["id"],
                "name": contact["display_name"],
                "title": title,
            }
    return c


def get_slack():
    r = app.client.users_list()  # type: ignore
    c: dict = {}
    while r.data.get("response_metadata", {}).get("next_cursor"):  # type: ignore
        for user in r.data["members"]:  # type: ignore
            if not user["is_bot"] and user["id"] != "USLACKBOT":
                c[user["id"]] = {
                    "title": user["profile"].get("title", False),
                    "real_name": user["profile"].get("real_name", False),
                    "display_name": user["profile"].get("display_name", False),
                }
        r = app.client.users_list(cursor=r.data["response_metadata"]["next_cursor"])  # type: ignore
    for user in r.data["members"]:  # type: ignore
        if not user["is_bot"] and user["id"] != "USLACKBOT":
            c[user["id"]] = {
                "title": user["profile"].get("title", False),
            }
    return c


# load config from file
with open("config.json", "r") as f:
    config = json.load(f)

# Initiate Slack client
app = App(token=config["slack"]["user_token"])
bot_app = App(token=config["slack"]["bot_token"])


# Get info for our Slack connection
slack_info = app.client.auth_test()  # type: ignore
print(f'Connected to Slack as "{slack_info["user"]}" with ID {slack_info["user_id"]}')

logging.info("Getting Slack users...")
slack_users = get_slack()
logging.debug(f"Got {len(slack_users)} Slack users")

logging.info("Getting TidyHQ users...")
tidyhq_users = get_tidyhq()
if not tidyhq_users:
    exit(1)
logging.debug(f"Got {len(tidyhq_users)} TidyHQ users")

# Iterate over slack users to find ones that have a title when we don't expect it
for slack_user in slack_users:
    # Skip people that will have titles updated in the next step
    if slack_user in tidyhq_users:
        continue

    if slack_users[slack_user]["title"]:
        message = (
            f'Removing title "{slack_users[slack_user]["title"]}" from {slack_user}'
        )
        logging.info(message)

        r = app.client.users_profile_set(  # type: ignore
            user=slack_user, name="title", value=""
        )
        if not r["ok"]:
            logging.error(f"Failed to remove title from {slack_user}")
            logging.error(r)
        else:
            bot_app.client.chat_postMessage(
                channel=config["slack"]["notification_channel"],
                text=message,
                username="Slack Titles",
                icon_emoji=":scroll:",
            )

for tidyhq_user in tidyhq_users:
    # Check if their title is already correct
    if tidyhq_users[tidyhq_user]["title"] == slack_users[tidyhq_user]["title"]:
        continue

    # Set the title
    message = f'Setting title "{tidyhq_users[tidyhq_user]["title"]}" for {tidyhq_users[tidyhq_user]["name"]}'
    logging.info(message)
    r = app.client.users_profile_set(  # type: ignore
        user=tidyhq_user,
        name="title",
        value=tidyhq_users[tidyhq_user]["title"],
    )
    if not r["ok"]:
        logging.error(f"Failed to set title for {tidyhq_user}")
        logging.error(r)
    else:
        bot_app.client.chat_postMessage(
            channel=config["slack"]["notification_channel"],
            text=message,
            username="Slack Titles",
            icon_emoji=":scroll:",
        )
