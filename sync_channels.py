import json
import logging
from pprint import pprint

import requests
from slack_bolt import App
import sys

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
        return False, False
    c = {}
    group_map = {}
    for contact in contacts:
        if contact["id"] in config["slack"]["membership_ignore"]:
            continue
        slack = ""
        for field in contact["custom_fields"]:
            if field["id"] == config["tidyhq"]["ids"]["slack"] and field["value"]:
                slack = field["value"]
                break

        # This script only deals with people that are linked in Slack
        if not slack:
            continue

        # Check if the user is a member
        member = False
        groups = []
        for group in contact["groups"]:
            group_map[group["id"]] = group["label"]
            groups.append(group["id"])
            if group["id"] in config["tidyhq"]["ids"]["members"]:
                member = True

        c[slack] = {
            "id": contact["id"],
            "name": contact["display_name"],
            "member": member,
            "groups": groups,
        }
    return c, group_map


# Load config
with open("config.json", "r") as f:
    config = json.load(f)

# Load mapping
with open("synced_channels.json", "r") as f:
    channel_mapping_raw = json.load(f)

    map_by_channel = {}
    map_by_group = {}

    for group in channel_mapping_raw["by_tidyhq"]:
        for channel in channel_mapping_raw["by_tidyhq"][group]:
            if channel not in map_by_channel:
                map_by_channel[channel] = []
            map_by_channel[channel].append(group)

        if group not in map_by_group:
            map_by_group[group] = []
        map_by_group[group].extend(channel_mapping_raw["by_tidyhq"][group])

    for channel in channel_mapping_raw["by_channel"]:
        for group in channel_mapping_raw["by_channel"][channel]:
            if channel not in map_by_channel:
                map_by_channel[channel] = []
            map_by_channel[channel].append(group)

        for group in channel_mapping_raw["by_channel"][channel]:
            if group not in map_by_group:
                map_by_group[group] = []
            map_by_group[group].append(channel)

# Load contacts from TidyHQ

contacts, group_map = get_tidyhq()
if not contacts:
    sys.exit(1)
logging.info(f"Loaded {len(contacts)} contacts from TidyHQ with Slack IDs")

# Build group memberships
groups = {}
for contact in contacts:
    for group in contacts[contact]["groups"]:
        group = str(group)
        if group not in groups:
            groups[group] = []
        groups[group].append(contact)

logging.info(f"Loaded {len(groups)} groups from TidyHQ")

# Initialize Slack app
app = App(token=config["slack"]["user_token"])

logging.info(f"Connected to Slack as {app.client.auth_test()['user']}")

channels = {}

# Build channel memberships
for channel in list(map_by_channel.keys()) + channel_mapping_raw["members"]:
    # Get channel members with pagination
    try:
        channel_members = []
        cursor = None
        while True:
            response = app.client.conversations_members(channel=channel, cursor=cursor)
            channel_members.extend(response["members"])
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
    except Exception as e:
        logging.error(f"Error getting members for channel {channel}: {e}")
        continue
    logging.info(f"Got info for #{channel} with {len(channel_members)} members")

    channels[channel] = channel_members

logging.info(f"Loaded members for {len(channels)} channels")

# Create list of desired channel memberships
desired_memberships = {}
for channel in channels:
    desired_memberships[channel] = []
    if channel not in map_by_channel:
        # These will be dealt with below as they're channels only mapped to members
        continue
    for group in map_by_channel[channel]:
        if group not in groups:
            logging.error(f"Group {group} has no members or does not exist")
            continue
        for contact in groups[group]:
            if contact not in desired_memberships[channel]:
                desired_memberships[channel].append(contact)

for channel in channel_mapping_raw["members"]:
    if channel not in desired_memberships:
        desired_memberships[channel] = []
    for contact in contacts:
        if contacts[contact]["member"]:
            if contact not in desired_memberships[channel]:
                desired_memberships[channel].append(contact)

# Create list of actionable changes
changes = {}
for channel in desired_memberships:
    for contact in desired_memberships[channel]:
        if contact not in channels[channel]:
            if channel not in changes:
                changes[channel] = []
            changes[channel].append(contact)

if "--cron" not in sys.argv:
    # Print human readable changes
    logging.info("Changes to be made:")
    for channel in changes:
        print(f"Channel: {channel} add {len(changes[channel])}")
        for contact in changes[channel]:
            print(f"  {contact} ({contacts[contact]['name']})")

    answer = input("Action? [y/N]: ")
    if answer.lower() != "y":
        logging.info("Aborting")
        sys.exit(0)

if "--live" in sys.argv:
    logging.info("Running in live mode")
    # Perform changes
    for channel in changes:
        try:
            app.client.conversations_invite(
                channel=channel, users=",".join(changes[channel])
            )
            logging.info(f"Invited {len(changes[channel])} to #{channel}")
        except Exception as e:
            logging.error(f"Error inviting to #{channel}: {e}")
else:
    logging.info("Running in dry run mode")
    # Perform changes
    for channel in changes:
        logging.info(f"Would invite {len(changes[channel])} to #{channel}")
