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

# Check for --quiet flag
quiet = False
if len(sys.argv) > 1 and "--quiet" in sys.argv:
    quiet = True
    logging.info("Running in quiet mode, no messages will be posted to Slack.")


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
        for field in contact["custom_fields"]:
            if field["id"] == config["tidyhq"]["ids"]["slack"] and field["value"]:
                slack = field["value"]
                continue

        # This script only deals with people that are linked in Slack
        if not slack:
            continue

        # Check if the user is a member
        member_induction = False
        member = False
        committee = False
        volunteer = False
        for group in contact["groups"]:
            if group["id"] in config["tidyhq"]["ids"]["members"]:
                member = True
            elif group["id"] in config["tidyhq"]["ids"]["committee"]:
                committee = True
            elif group["id"] in config["tidyhq"]["ids"]["member_induction"]:
                member_induction = True
            elif group["id"] in config["tidyhq"]["ids"]["volunteer"]:
                volunteer = True

        if member or committee or volunteer:
            c[slack] = {
                "id": contact["id"],
                "name": contact["display_name"],
                "member": member,
                "committee": committee,
                "member_induction": member_induction,
                "volunteer": volunteer,
            }
    return c


def get_slack():
    r = app.client.users_list()  # type: ignore
    c = {}
    while r.data.get("response_metadata", {}).get("next_cursor"):  # type: ignore
        for user in r.data["members"]:  # type: ignore
            if not user["is_bot"] and user["id"] != "USLACKBOT":
                c[user["id"]] = {
                    "emoji": user["profile"].get("status_emoji", False),
                    "text": user["profile"].get("status_text", False),
                }
        r = app.client.users_list(cursor=r.data["response_metadata"]["next_cursor"])  # type: ignore
    for user in r.data["members"]:  # type: ignore
        if not user["is_bot"] and user["id"] != "USLACKBOT":
            c[user["id"]] = {
                "emoji": user["profile"].get("status_emoji", False),
                "text": user["profile"].get("status_text", False),
            }
    return c


def set_badge(slack_id, text=None, emoji=None):
    if not text:
        text = ""
        emoji = ""
    elif emoji and text:
        # Emoji is already set
        pass
    elif text not in config["slack"]["status"]:
        sys.exit(f"Invalid status: {text}")
    else:
        emoji = config["slack"]["status"][text]

    profile = {
        "status_text": text,
        "status_emoji": emoji,
        "status_expiration": 0,
    }

    app.client.users_profile_set(user=slack_id, profile=profile)

    if text:
        message = f"Set badge for <@{slack_id}> to {emoji} {text}"
    else:
        message = f"Removed {text} badge from <@{slack_id}>"
    # Post a message to the notification channel
    if not quiet:
        bot_app.client.chat_postMessage(
            channel=config["slack"]["notification_channel"],
            text=message,
            username="Slack Badges",
            icon_emoji=":artifactory:",
        )

    # This method is rated to ~30 requests per minute, so we need to sleep
    time.sleep(3)


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

# Iterate over Slack users to find ones that have a status when we don't expect it
for slack_user in slack_users:
    # Skip users in the override list
    if slack_user in [x["user"] for x in config["slack"].get("status_override", [])]:
        continue

    # Users that aren't in tidyhq wouldn't get their status fixed in the next step so strip them now
    if slack_user not in tidyhq_users:
        # Check if they have a status to remove
        if slack_users[slack_user]["text"] or slack_users[slack_user]["emoji"]:
            logging.info(
                f'Removing status "{slack_users[slack_user]["text"]}" from {slack_user}'
            )
            set_badge(slack_id=slack_user, text=None)

for tidyhq_user in tidyhq_users:
    name = f"{tidyhq_users[tidyhq_user]['name']} ({tidyhq_user}/{tidyhq_users[tidyhq_user]['id']})"

    # Check if user is present in both systems
    if tidyhq_user not in slack_users:
        logging.warning(f"{name} is in TidyHQ but not in Slack")
        continue

    emoji = None
    title = None

    if tidyhq_users[tidyhq_user]["committee"]:
        emoji = config["slack"]["status"]["Committee"]
        title = "Committee"
    elif tidyhq_users[tidyhq_user]["volunteer"]:
        emoji = config["slack"]["status"]["Volunteer"]
        title = "Volunteer"
    elif tidyhq_users[tidyhq_user]["member"]:
        # Check for a member induction
        emoji = config["slack"]["status"]["Uninducted"]
        if tidyhq_users[tidyhq_user]["member_induction"]:
            emoji = config["slack"]["status"]["Member"]
        title = "Member"

    if title:
        # Check if the status is already set correctly
        if (
            slack_users[tidyhq_user]["text"] == title
            and slack_users[tidyhq_user]["emoji"] == emoji
        ):
            logging.debug(f"{name} is already marked as {title}")
        else:
            set_badge(slack_id=tidyhq_user, text=title, emoji=emoji)
            logging.info(f"Setting badge for {name} as {title}")

# Process overrides
for override in config["slack"].get("status_override"):
    if override["user"] not in slack_users:
        logging.warning(f"User {override['user']} not found in Slack")
        continue
    # Check if the user already has the correct title
    if (
        slack_users[override["user"]]["text"] == override["status"]
        and slack_users[override["user"]]["emoji"]
        == config["slack"]["status"][override["status"]]
    ):
        logging.debug(f"{override['user']} is already marked as {override['status']}")
    else:
        set_badge(slack_id=override["user"], text=override["status"])
        logging.info(
            f"Setting badge for {override['user']} as {override['status']} due to a hardcoded override. (config.json)"
        )
