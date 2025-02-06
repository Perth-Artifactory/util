from datetime import datetime
import json
import os
import sys
import requests
from pprint import pprint

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

with open("config.json", "r") as f:
    config: dict = json.load(f)


def gcal() -> str:

    creds = Credentials.from_authorized_user_file(
        "token.json", ["https://www.googleapis.com/auth/calendar.readonly"]
    )
    try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        events_result = (
            service.events()  # type: ignore
            .list(
                calendarId=config["google"]["calendar_id"],
                timeMin=now,
                maxResults=30,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            sys.exit(1)
            return ""

        # Construct more useful event dict
        formatted_events = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            if "description" not in event:
                event["description"] = ""
            # Add fake hours to all day events
            if len(start) == 10:
                start = start + "T00:00:00+08:00"
            if len(end) == 10:
                end = end + "T00:00:00+08:00"

            formatted_events.append(
                {
                    "start": start,
                    "end": end,
                    "summary": event["summary"],
                    "description": event["description"],
                }
            )
        return json.dumps(formatted_events, indent=4)

    except HttpError:
        sys.exit()


# Retrieves the next 30 events from tidyhq, formats them the same as gcal and returns them as a json string
def tidyhq() -> str:
    try:
        r = requests.get(
            "https://api.tidyhq.com/v1/events",
            params={
                "access_token": config["tidyhq"]["token"],
                "limit": 30,
                "start_at": datetime.utcnow().isoformat() + "Z",
                "public": True,
            },
        )
        events = r.json()
    except requests.exceptions.RequestException:
        return ""
    formatted_events = []
    for event in events:
        formatted_events.append(
            {
                "start": event["start_at"],
                "end": event["end_at"],
                "summary": event["name"],
                "description": event["body"],
                "location": event["location"],
                "url": event["public_url"],
                "id": event["id"],
            }
        )
    return json.dumps(formatted_events, indent=4)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "gcal":
            print(gcal())
        elif sys.argv[1] == "tidyhq":
            print(tidyhq())
