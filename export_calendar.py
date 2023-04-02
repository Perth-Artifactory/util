import datetime
import json
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

with open("config.json","r") as f:
    config: dict = json.load(f)

def main() -> None:
   
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/calendar.readonly'])
    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = service.events().list(calendarId=config["google"]["calendar_id"], timeMin=now,
                                              maxResults=30, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            sys.exit(1)
            return

        # Construct more useful event dict
        formated_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            formated_events.append({
                "start": start,
                "end": end,
                "summary": event['summary'],
                "description": event['description']
            })
        return json.dumps(formated_events, indent=4)

    except HttpError as error:
        sys.exit()

if __name__ == '__main__':
    print(main())