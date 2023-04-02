import requests
import json
from pprint import pprint
from datetime import datetime
import sys

with open("config.json","r") as f:
    config = json.load(f)
with open("events.json","r") as f:
    reports = json.load(f)

def get_event(event_id: str =""):
    if event_id:
        try:
            r = requests.get(f"https://api.tidyhq.com/v1/events/{event_id}",params={"access_token":config["tidyhq"]["token"]})
            if r.status_code == 200:
                event = r.json()
                return event
            return False
        except requests.exceptions.RequestException as e:
            return False

def get_tickets(event_id: str =""):
    if event_id:
        try:
            r = requests.get(f"https://api.tidyhq.com/v1/events/{event_id}/tickets/",params={"access_token":config["tidyhq"]["token"]})
            if r.status_code == 200:
                tickets = r.json()
                return tickets
            return False
        except requests.exceptions.RequestException as e:
            return False

if len(sys.argv) > 1:
    report_id = sys.argv[1]
    if report_id not in reports:
        sys.exit(1)
else:
    sys.exit(1)

lines = ""
for event in reports[report_id]:
    e = get_event(event_id=event)
    if e:
        tickets = get_tickets(event_id=event)
        total = 0
        tlines = ""
        for ticket in tickets:
            total += ticket["quantity_sold"] * float(ticket["amount"])
            tlines += f'<li>{ticket["name"]}: {ticket["quantity_sold"]}</li>\n'
        lines += f"""<tr>
    <td>{e["name"]}</td>
    <td>{e["start_at"]}</td>
    <td><ul>{tlines}</ul></td>
    <td>${total}</td>
    </tr>"""
with open("event_report_template.html","r") as f:
    template = f.read()
print(template.format(lines,datetime.now()))