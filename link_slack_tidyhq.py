import json
import logging
import sys
from typing import Any, Literal

import requests
from slack_bolt import App


# Get a list of contacts from TidyHQ that are not linked to a Slack account
def get_tidyhq() -> dict[Any, Any] | Literal[False]:
    logging.debug("Attempting to get contact dump from TidyHQ...")
    try:
        r = requests.get(
            "https://api.tidyhq.com/v1/contacts",
            params={"access_token": config["tidyhq"]["token"]},
        )
        contacts: list[dict[str, Any]] = r.json()
    except requests.exceptions.RequestException:
        logging.error("Could not reach TidyHQ")
        return False
    c: dict[str, dict[str, Any]] = {}
    for contact in contacts:
        in_slack = False
        for field in contact["custom_fields"]:
            if field["id"] == config["tidyhq"]["ids"]["slack"] and field["value"]:
                in_slack = True
        if not in_slack:
            c[contact["email_address"]] = contact
    return c


def get_slack():
    r = app.client.users_list()  # type: ignore
    c: dict[str, dict[str, str]] = {}
    for user in r.data["members"]:  # type: ignore
        email: str | Literal[False] = user["profile"].get("email")  # type: ignore
        if email:
            c[email] = {  # type: ignore
                "id": user["id"],
                "name": user["profile"].get("real_name_normalized"),  # type: ignore
            }
    return c


def get_tidyhq_memberships() -> list[dict[str, Any]] | Literal[False]:
    try:
        r = requests.get(
            "https://api.tidyhq.com/v1//memberships",
            params={"access_token": config["tidyhq"]["token"]},
        )
    except requests.exceptions.RequestException:
        logging.error("Could not reach TidyHQ")
        return False
    memberships = r.json()
    active: list[dict[str, Any]] = []
    for membership in memberships:
        if membership["state"] != "expired":
            active.append(membership["contact_id"])
    return active


def link_accounts(tidyhq_id: str, slack_id: str) -> bool:
    try:
        r = requests.put(
            f"https://api.tidyhq.com/v1/contacts/{tidyhq_id}",
            params={"access_token": config["tidyhq"]["token"]},
            json={"custom_fields": {config["tidyhq"]["ids"]["slack"]: slack_id}},
        )
        if r.status_code != 200:
            logging.error(f"Could not link accounts: {r.text}")
            return False
        else:
            logging.info(f"Linked {tidyhq_id} to {slack_id}")
            return True

    except requests.exceptions.RequestException:
        logging.error("Could not reach TidyHQ")
        return False


def notify_slack(slack_user: dict[str, Any], tidyhq_user: dict[str, Any], method: str):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f'TidyHQ account <https://{domain}.tidyhq.com/contacts/{tidyhq_user["id"]}|{tidyhq_user["first_name"]} {tidyhq_user["last_name"]}> has been linked to <@{slack_user["id"]}>',
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "text": f"This link was made by: {method}",
                    "emoji": True,
                }
            ],
        },
    ]

    # Send notification to Slack
    app.client.chat_postMessage(  # type: ignore
        channel=config["slack"]["notification_channel"],
        text="Linked a TidyHQ account to a Slack account",
        blocks=blocks,
    )


# load config from config.json
with open("config.json", "r") as f:
    config: dict[str, Any] = json.load(f)

# Check for --debug flag
if len(sys.argv) > 1 and "--debug" in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# Initiate Slack client
app = App(token=config["slack"]["bot_token"])


logging.info("Getting Slack users...")
slack_users = get_slack()
logging.debug(f"Got {len(slack_users)} Slack users")

logging.info("Getting TidyHQ users...")
tidyhq_users = get_tidyhq()
if not tidyhq_users:
    exit(1)
logging.debug(f"Got {len(tidyhq_users)} TidyHQ users")

# Get TidyHQ org name for URLs.
domain: str = requests.get(
    "https://api.tidyhq.com/v1/organization",
    params={"access_token": config["tidyhq"]["token"]},
).json()["domain_prefix"]

# Check for --cron flag
if len(sys.argv) > 1 and "--cron" in sys.argv:
    logging.info("Running in cron mode")

    # Check for any users in Slack that are not in TidyHQ
    for email in tidyhq_users:
        t = tidyhq_users[email]
        if email in slack_users:
            s = slack_users[email]
            # Link the user
            logging.info(
                f"Match:\nTidyHQ: {t['first_name']} {t['last_name']} ({t['id']})\nSlack: {s['name']} ({s['id']})"
            )
            if link_accounts(t["id"], s["id"]):
                notify_slack(s, t, "automated email address matching")

else:
    logging.info("Running in interactive mode")

    # Since we only prompt for IDs in interactive mode, we can get the active users here

    logging.info("Getting TidyHQ active users...")
    tidyhq_active_users = get_tidyhq_memberships()
    if not tidyhq_active_users:
        exit(1)
    logging.debug(f"Got {len(tidyhq_active_users)} TidyHQ active users")

    # Compare the two lists and link any users that are in both
    for email in tidyhq_users:
        t = tidyhq_users[email]
        if email in slack_users:
            print("\n")
            s = slack_users[email]
            # Link the user
            print(
                f"Match:\nTidyHQ: {t['first_name']} {t['last_name']} ({t['id']})\nSlack: {s['name']} ({s['id']})"
            )
            i = input("Yes? [Y/n]")
            if i != "n":
                link_accounts(t["id"], s["id"])
                notify_slack(s, t, "automated email address matching")
            else:
                print("Skipping")
        else:
            if tidyhq_users[email]["id"] in tidyhq_active_users:
                print(
                    f"Could not find {tidyhq_users[email]['first_name']} {tidyhq_users[email]['last_name']} in Slack but they are an active member"
                )
                slack_id: str = input("Enter Slack ID [or leave blank to skip]: ")
                if slack_id:
                    if link_accounts(t["id"], slack_id):
                        notify_slack({"id": slack_id}, t, "manual entry")
                else:
                    print("Skipping")
