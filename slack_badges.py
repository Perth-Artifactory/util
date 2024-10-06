import json
import requests
from slack_bolt import App
import sys
import logging
from pprint import pprint
import time

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
        logging.error("Could not reach TidyHQ")
        return False
    c = {}
    for contact in contacts:
        slack = ""
        for field in contact["custom_fields"]:
            if field["id"] == config["tidyhq"]["ids"]["slack"] and field["value"]:
                slack = field["value"]
                continue

        # This script only deals with people that are linked in Slack
        if not slack:
            continue

        # Check if the user is a member
        member = False
        committee = False
        for group in contact["groups"]:
            if group["id"] in config["tidyhq"]["ids"]["members"]:
                member = True
            elif group["id"] in config["tidyhq"]["ids"]["committee"]:
                committee = True

        if member or committee:
            c[slack] = {
                "id": contact["id"],
                "name": contact["display_name"],
                "member": member,
                "committee": committee,
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


def set_badge(slack_id, text=None):
    if not text:
        text = ""
        emoji = ""
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
    # This method is rated to ~30 requests per minute, so we need to sleep
    time.sleep(3)


# load config from file
with open("config.json", "r") as f:
    config = json.load(f)

# Initiate Slack client
app = App(token=config["slack"]["user_token"])

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
    # Users that aren't in tidyhq wouldn't get their status fixed in the next step so strip them now
    if slack_user not in tidyhq_users:
        # Check if they have a status to remove
        if slack_users[slack_user]["text"] or slack_users[slack_user]["emoji"]:
            logging.info(
                f'Removing status "{slack_users[slack_user]["text"]}" from {slack_user}'
            )
            set_badge(slack_id=slack_user, text=None)

for tidyhq_user in tidyhq_users:
    name = f'{tidyhq_users[tidyhq_user]["name"]} ({tidyhq_user}/{tidyhq_users[tidyhq_user]["id"]})'

    # Check if user is present in both systems
    if tidyhq_user not in slack_users:
        logging.warning(f"{name} is in TidyHQ but not in Slack")
        continue

    if tidyhq_users[tidyhq_user]["committee"]:
        # Check if the user already has the correct title
        if (
            slack_users[tidyhq_user]["text"] == "Committee"
            and slack_users[tidyhq_user]["emoji"]
            == config["slack"]["status"]["Committee"]
        ):
            logging.debug(f"{name} is already marked as a committee member")
            continue
        else:
            logging.info(f"Setting badge for {name} as committee")
            set_badge(slack_id=tidyhq_user, text="Committee")
    elif tidyhq_users[tidyhq_user]["member"]:
        # Check if the user already has the correct title
        if (
            slack_users[tidyhq_user]["text"] == "Member"
            and slack_users[tidyhq_user]["emoji"] == config["slack"]["status"]["Member"]
        ):
            logging.debug(f"{name} is already marked as a member")
            continue
        else:
            logging.info(f"Setting badge for {name} as member")
            set_badge(slack_id=tidyhq_user, text="Member")

# Process overrides
for override in config["slack"].get("status_override"):
    set_badge(slack_id=override["user"], text=override["status"])
    logging.info(
        f'Setting badge for {override["user"]} as {override["status"]} due to a hardcoded override. (config.json)'
    )
