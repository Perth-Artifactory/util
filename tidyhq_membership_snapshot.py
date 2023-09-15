import json
from datetime import datetime
import requests
from pprint import pprint

# Load config from file
with open('config.json') as f:
    config: dict = json.load(f)
    
# Accept a date to use for the snapshot
date = input("Enter date to use for snapshot (YYYY-MM-DD): ")
date = datetime.strptime(date, "%Y-%m-%d")

members = {}
total = 0

# Load a complete list of memberships
memberships = requests.get("https://api.tidyhq.com/v1/memberships",params={"access_token":config["tidyhq"]["token"]}).json()
for membership in memberships:
    start_date = datetime.strptime(membership["start_date"], "%Y-%m-%dT%H:%M:%S+08:00")
    end_date = datetime.strptime(membership["end_date"], "%Y-%m-%dT%H:%M:%S+08:00")
    if start_date <= date <= end_date:
        name = membership["membership_level"]["name"]
        if name not in members:
            members[name] = 0
        members[name] += 1
        total += 1
pprint(members)
print(f'Total: {total}')