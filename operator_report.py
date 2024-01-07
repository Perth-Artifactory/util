# Script that generates a markdown report of memberships of specific TidyHQ groups

import os
import sys
import json
import requests
import datetime
import logging
from pprint import pprint


def get_group_info(id=None, name=None):
    group = None
    if not id and not name:
        logging.error("Provide either an ID or a group name")
        sys.exit(1)
    if id:
        group_id = id
        try:
            r = requests.get(
                f"https://api.tidyhq.com/v1/groups/{group_id}",
                params={"access_token": config["tidyhq"]["token"]},
            )
            group = r.json()
        except requests.exceptions.RequestException as e:
            logging.error("Could not reach TidyHQ")
            sys.exit(1)
    elif name:
        try:
            r = requests.get(
                f"https://api.tidyhq.com/v1/groups",
                params={"access_token": config["tidyhq"]["token"]},
            )
            groups = r.json()
        except requests.exceptions.RequestException as e:
            logging.error("Could not reach TidyHQ")
            sys.exit(1)
        for group_i in groups:
            trim_group_i = group_i["label"].replace("Machine Operator - ", "")
            if trim_group_i == name:
                group = group_i
                break
    if not group:
        logging.error(f'Trouble getting info for group "{name}"')
        sys.exit(1)
    processed = {}
    if group["description"]:
        desc_lines = group["description"].split("\n")
        for line in desc_lines:
            if "=" in line:
                key, value = line.split("=")
                processed[key.strip()] = value.strip()
    name = group["label"].replace("Machine Operator - ", "")
    processed["name"] = name
    return processed


def find_users_in_group(group_id):
    c = []
    for contact in contacts:
        for group in contact["groups"]:
            if group["id"] == group_id:
                c.append(contact)
    return c


def format_user(contact):
    n = ""
    if contact["nick_name"]:
        n = f' ({contact["nick_name"]})'
    return (
        f'{contact["first_name"].capitalize()} {contact["last_name"].capitalize()}{n}'
    )


# Set up logging
logging.basicConfig(level=logging.INFO)

# Load config from file
with open("config.json") as f:
    config: dict = json.load(f)

# Load the list of reports from file
with open("machines.json") as f:
    reports: dict = json.load(f)

if len(sys.argv) < 2:
    print("Usage: python3 operator_report.py [report name]")

    # Print a list of all reports if no report name is given and translate group IDs to names
    print("Available reports:")
    for report in reports:
        print(f"{report}")
        for group in reports[report]:
            print(f'    {get_group_info(group)["name"]} ({group})')
        print("")
    print(
        "You can also use 'all' to get a list of operators from all groups. Each group will only be listed once and specific groups can be excluded by adding them to the 'exclude' list in machines.json"
    )

    sys.exit(1)

report_name = sys.argv[1]

if report_name == "all":
    # check for exclusion report
    if "exclude" not in reports.keys():
        exclusions = []
    else:
        exclusions = reports["exclude"]

    deduped_reports = []
    for report in reports:
        for group in reports[report]:
            if group not in deduped_reports and group not in exclusions:
                deduped_reports.append(group)
    report = deduped_reports
elif report_name not in reports:
    print(f"Report {report_name} not found in file")
    sys.exit(1)

else:
    report = reports[report_name]

# Get list of TidyHQ contacts to iterate over
try:
    r = requests.get(
        f"https://api.tidyhq.com/v1/contacts",
        params={"access_token": config["tidyhq"]["token"]},
    )
    contacts = r.json()
except requests.exceptions.RequestException as e:
    logging.error("Could not reach TidyHQ")
    sys.exit(1)

# Index by contact instead
contacts_indexed = {}
machines = []
for group in report:
    machine_name = get_group_info(group)["name"]
    machines.append(machine_name)
    for contact in find_users_in_group(group):
        contact_name = format_user(contact)
        if contact_name not in contacts_indexed:
            contacts_indexed[contact_name] = []
        contacts_indexed[contact_name].append(machine_name)

# Generate the report

# Generate header
header = "| Operator | "
for machine in machines:
    info = get_group_info(name=machine)
    if "url" in info:
        header += f'[{info["name"]}]({info["url"]}) | '
    else:
        header += f'{info["name"]} | '
lines = [header]

# Add separator
lines.append(f'| --- | {" | ".join(["---"] * len(machines))} |')

# Add each operator as a line
for operator in sorted(contacts_indexed):
    s = f"| {operator} | "
    for machine in machines:
        if machine in contacts_indexed[operator]:
            s += "✅ | "
        else:
            s += "❌ | "
    lines.append(s)

for line in lines:
    print(line)
