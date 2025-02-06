import json
import logging
import sys
import time
from pprint import pprint
from typing import Any

import requests

import errors


def correct_name(name: str) -> str:
    # Takes a name and returns a version with the first letter capitalised and whitespace trimmed

    if not name:
        return name

    fixed_name = ""

    for word in name.split():
        # This will strip whitespace
        if word:
            # Capitalise the first letter of the word but leave the rest of the word alone
            word = word[0].upper() + word[1:]

            # Special case for Mc
            if word.startswith("Mc") and len(word) > 2:
                word = word[:2] + word[2].upper() + word[3:]

            # special case for Mac
            if word.startswith("Mac") and len(word) > 6:
                word = word[:3] + word[3].upper() + word[4:]

            # Special case for '
            if "'" in word:
                word = (
                    word[: word.index("'") + 1]
                    + word[word.index("'") + 1].upper()
                    + word[word.index("'") + 2 :]
                )

            # Special case for hyphenated names
            if "-" in word:
                word = (
                    word[: word.index("-") + 1]
                    + word[word.index("-") + 1].upper()
                    + word[word.index("-") + 2 :]
                )

            fixed_name += word + " "

    return fixed_name.strip()


# Check for --debug flag and set logging level accordingly
if len(sys.argv) > 1 and "--debug" in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# load config from config.json
with open("config.json", "r") as f:
    config: dict[str, Any] = json.load(f)

# Get TidyHQ org name for URLs.
domain: str = requests.get(
    "https://api.tidyhq.com/v1/organization",
    params={"access_token": config["tidyhq"]["token"]},
).json()["domain_prefix"]


logging.debug("Attempting to get contact dump from TidyHQ...")
try:
    r = requests.get(
        "https://api.tidyhq.com/v1/contacts",
        params={"access_token": config["tidyhq"]["token"]},
    )
    contacts: list[dict[str, Any]] = r.json()
    logging.info(f"Got {len(contacts)} contacts from TidyHQ")
except requests.exceptions.RequestException:
    logging.error(errors.tidyhq_connect)
    sys.exit(1)

# Check for --cron flag
if "--cron" in sys.argv:
    logging.info("Running in cron mode")

    # Iterate over each contact
    for contact in contacts:
        corrections: dict[str, str] = {}

        # Check if contact is a person
        if contact["kind"] != "person":
            continue

        # Check if names are capitalised
        for field in ["first_name", "last_name"]:
            if contact[field] != correct_name(contact[field]):
                corrections[field] = correct_name(contact[field])

        # Check if their nickname is just their first name
        if (
            isinstance(contact["nick_name"], str)
            and contact["nick_name"] != ""
            and isinstance(contact["first_name"], str)
            and contact["first_name"] != ""
        ):
            if contact["nick_name"].lower() == contact["first_name"].lower():
                corrections["nick_name"] = ""

        # Check if their nickname has whitespace at the end
        if (
            isinstance(contact["nick_name"], str)
            and contact["nick_name"] != ""
            and contact["nick_name"].endswith(" ")
        ):
            corrections["nick_name"] = contact["nick_name"].strip()

        if corrections:
            # send corrected data to TidyHQ
            r = requests.put(
                f"https://api.tidyhq.com/v1/contacts/{contact['id']}",
                params={"access_token": config["tidyhq"]["token"]} | corrections,
            )
            time.sleep(1)

else:
    # Iterate over each contact
    for contact in contacts:
        corrections: dict[str, str] = {}

        # Check if contact is a person
        if contact["kind"] != "person":
            continue

        # Check if names are capitalised
        for field in ["first_name", "last_name"]:
            if contact[field] != correct_name(contact[field]):
                pprint(contact[field])
                corrections[field] = correct_name(contact[field])

        # Check if their nickname is just their first name
        if (
            isinstance(contact["nick_name"], str)
            and contact["nick_name"] != ""
            and isinstance(contact["first_name"], str)
            and contact["first_name"] != ""
        ):
            if contact["nick_name"].lower() == contact["first_name"].lower():
                corrections["nick_name"] = ""

        if corrections:
            # Print corrections
            print(f"Contact {contact['id']} needs corrections:")
            pprint(corrections)

            # Ask user if they want to apply corrections
            if input("Apply corrections? (Y/n) ").lower() == "n":
                continue

            # send corrected data to TidyHQ
            r = requests.put(
                f"https://api.tidyhq.com/v1/contacts/{contact['id']}",
                params={"access_token": config["tidyhq"]["token"]} | corrections,
            )

            # Check if the update was successful
            if r.status_code == 200:
                print(
                    f'Name corrected for contact {contact["id"]}: {contact["display_name"]}'
                )
            else:
                print(f"Failed to update contact {contact['id']}: {r.text}")
