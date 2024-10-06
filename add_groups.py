import json
import requests
from pprint import pprint

with open("config.json", "r") as f:
    config = json.load(f)

prefix = input("Enter the prefix for new groups: ")
if not prefix:
    prefix = "Machine Operator"
    print(f"Using default prefix: {prefix}")

if " - " not in prefix:
    prefix = prefix + " - "

# get existing groups
r = requests.get(
    f"https://api.tidyhq.com/v1/groups",
    params={"access_token": config["tidyhq"]["token"]},
)

existing_groups: dict = r.json()

print(f"Found {len(existing_groups)} groups")
prefix_groups = 0
for group in existing_groups:
    if group["label"].startswith(prefix):
        prefix_groups += 1
print(f'Found {prefix_groups} groups with prefix "{prefix[:-3]}"')

print(
    "Paste list of groups to add below. Each group should be either on a new line or separated by a comma. Once you've finished adding groups, press enter."
)

group_input = input()
groups = []

while group_input:
    if "," in group_input:
        groups = groups + group_input.split(",")
    else:
        groups.append(group_input)
    group_input = input()

for group in groups:
    group = group.strip()
    if group:
        # Add the prefix to the group and capitalise every word in the group name
        final_name = prefix + " ".join([word.capitalize() for word in group.split()])
        if final_name in [group["label"] for group in existing_groups]:
            print(f"Group {final_name} already exists, skipped.")
        else:
            print(f"Creating group {final_name}")
            r = requests.post(
                f"https://api.tidyhq.com/v1/groups",
                params={"access_token": config["tidyhq"]["token"]},
                json={"label": final_name},
            )
            if r.status_code == 201:
                print(f"Created group {final_name} successfully. ID: {r.json()['id']}")
            else:
                print(f"Failed to create group {final_name}")
                pprint(r.json())
