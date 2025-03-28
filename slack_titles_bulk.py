import json
import logging
import sys
import time
from pprint import pprint

import requests

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


# load config from file
with open("config.json", "r") as f:
    config = json.load(f)

if "--read" in sys.argv or "--set" in sys.argv:
    filename = "slack_titles.json"
    answer = input("Specify filename [slack_titles.json]: ")
    if answer:
        filename = answer

logging.info("Getting TidyHQ users...")
tidyhq_users = get_tidyhq()
if not tidyhq_users:
    exit(1)
logging.debug(f"Got {len(tidyhq_users)} TidyHQ users")

if "--read" in sys.argv:
    # Sort the users by name
    tidyhq_users = dict(sorted(tidyhq_users.items(), key=lambda x: x[1]["name"]))

    with open(filename, "w") as f:
        json.dump(tidyhq_users, f, indent=4)
    logging.info(
        f"Wrote {len(tidyhq_users)} TidyHQ users to {filename} (Only users with existing titles)"
    )
    logging.info("Edit the file and run slack_titles_bulk.py --set to update TidyHQ.")

elif "--set" in sys.argv:
    logging.info("Setting Slack titles...")

    with open(filename, "r") as f:
        new_titles = json.load(f)
    logging.debug(f"Got {len(tidyhq_users)} TidyHQ users")

    changes = False

    for slack_id in new_titles:
        # Skip the title check if the user previous had no title
        if slack_id in tidyhq_users:
            if new_titles[slack_id]["title"] == tidyhq_users[slack_id]["title"]:
                logging.debug(
                    f"Skipping {new_titles[slack_id]['name']} ({slack_id}) as title is the same"
                )
                continue

        changes = True

        user = new_titles[slack_id]
        logging.info(
            f"Setting title for {user['name']} ({slack_id}) to {user['title']} in TidyHQ"
        )
        # Set the title in TidyHQ
        r = requests.put(
            f"https://api.tidyhq.com/v1/contacts/{user['id']}",
            params={"access_token": config["tidyhq"]["token"]},
            json={"custom_fields": {config["tidyhq"]["ids"]["title"]: user["title"]}},
        )
        if r.status_code != 200:
            logging.error(errors.tidyhq_update)
            exit(1)

    if changes:
        logging.info("Changes made to TidyHQ. Use slack_titles.py to update Slack.")
else:
    print("Usage: slack_titles_bulk.py [--read|--set] [--debug]")
    print("  --read: Read TidyHQ users and save to file")
    print("  --set: Set Slack titles in TidyHQ from file")
    exit(1)
