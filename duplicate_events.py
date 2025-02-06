import requests
import json
from pprint import pprint
from datetime import datetime, timedelta
import sys

with open("config.json", "r") as f:
    config = json.load(f)


def get_event(event_id: str = ""):
    if event_id:
        try:
            r = requests.get(
                f"https://api.tidyhq.com/v1/events/{event_id}",
                params={"access_token": config["tidyhq"]["token"]},
            )
            if r.status_code == 200:
                event = r.json()
                return event
            return False
        except requests.exceptions.RequestException:
            return False


def create_event(details):
    if "category_id" in details:
        if not details["category_id"]:
            del details["category_id"]

    for k in ["id", "created_at", "category_id", "image_url", "public", "public_url"]:
        if k in details:
            del details[k]

    details["start_at"] = details["start_at"].strftime("%Y-%m-%dT%H:%M:%S%z")
    details["end_at"] = details["end_at"].strftime("%Y-%m-%dT%H:%M:%S%z")

    try:
        r = requests.post(
            "https://api.tidyhq.com/v1/events/",
            params={"access_token": config["tidyhq"]["token"]},
            json=details,
        )
        if r.status_code == 201:
            event = r.json()
            return event
        print("Bad response from TidyHQ:")
        pprint(details)
        print(r.status_code)
        print(r.text)
        input()
        return False
    except requests.exceptions.RequestException as e:
        print(e)
        return False


# Get a list of all events in TidyHQ
r = requests.get(
    "https://api.tidyhq.com/v1/events/",
    params={"access_token": config["tidyhq"]["token"]},
)

# Events are returned newest last
newest_events = r.json()[-5:]

# Let the user pick an event
print("Select an event:")
for i, event in enumerate(newest_events):
    print(f'{i}: {event["name"]} ({event["start_at"]})')
event_index = int(input("Enter the number of the event: "))
while event_index not in range(len(newest_events)):
    event_index = int(input("Enter the number of the event: "))
print(f"You selected {newest_events[event_index]['name']}")

# Get desired frequency of events and number of events to create
frequency = int(input("How often should this event repeat? (in days): "))
while frequency < 1:
    frequency = int(input("How often should this event repeat? (in days): "))

event_num = int(input("How many events should be created?: "))
while event_num < 1:
    event_num = int(input("How many events should be created?: "))

# create event_num events offset by frequency days

event = newest_events[event_index]
event["start_at"] = datetime.strptime(event["start_at"], "%Y-%m-%dT%H:%M:%S%z")
event["end_at"] = datetime.strptime(event["end_at"], "%Y-%m-%dT%H:%M:%S%z")

for x in range(event_num):
    # Add frequency days to start_at and end_at
    event["start_at"] = event["start_at"] + timedelta(days=frequency)
    event["end_at"] = event["end_at"] + timedelta(days=frequency)

    print(f'Creating {event["name"]} ({event["start_at"]})', end="")
    if create_event(newest_events[event_index]):
        print("...OK")
    else:
        print("...FAILED")
