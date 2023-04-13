# Script that generates a markdown report of memberships of specific TidyHQ groups

import os
import sys
import json
import requests
import datetime
import logging
from pprint import pprint

def get_group_name(group_id):
    try:
        r = requests.get(f"https://api.tidyhq.com/v1/groups/{group_id}",params={"access_token":config["tidyhq"]["token"]})
        group = r.json()
    except requests.exceptions.RequestException as e:
        logging.error("Could not reach TidyHQ")
        return False
    return group["label"].replace("Machine Operator - ","")

def find_users_in_group(group_id):
    c = []
    for contact in contacts:
        for group in contact["groups"]:
            if group["id"] == group_id:
                c.append(contact)
    return c

def format_user(contact):
    n = ''
    if contact["nick_name"]:
        n = f' ({contact["nick_name"]})'
    return f'{contact["first_name"].capitalize()} {contact["last_name"].capitalize()}{n}'

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load config from file
with open('config.json') as f:
    config: dict = json.load(f)

# Load the list of reports from file
with open('machines.json') as f:
    machines: dict = json.load(f)

if len(sys.argv) < 2:
    print("Usage: python3 operator_report.py [report name]")
    sys.exit(1)

report_name = sys.argv[1]

if report_name not in machines:
    sys.exit(1)

report = machines[report_name]

# Get list of TidyHQ contacts to iterate over
try:
    r = requests.get(f"https://api.tidyhq.com/v1/contacts",params={"access_token":config["tidyhq"]["token"]})
    contacts = r.json()
except requests.exceptions.RequestException as e:
    logging.error("Could not reach TidyHQ")
    sys.exit(1)

# Index by contact instead
contacts_indexed = {}
machines = []
for group in report:
    machine_name = get_group_name(group)
    machines.append(machine_name)
    for contact in find_users_in_group(group):
        contact_name = format_user(contact)
        if contact_name not in contacts_indexed:
            contacts_indexed[contact_name] = []
        contacts_indexed[contact_name].append(machine_name)

# Generate the report
lines = [f'| Operator | {" | ".join(machines)} |']
lines.append(f'| --- | {" | ".join(["---"] * len(machines))} |')
for operator in sorted(contacts_indexed):
    s = f'| {operator} | '
    for machine in machines:
        if machine in contacts_indexed[operator]:
            s += '✅ | '
        else:
            s += '❌ | '
    lines.append(s)

for line in lines:
    print(line)