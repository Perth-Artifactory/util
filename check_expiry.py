import json
import requests
from pprint import pprint
from datetime import datetime, timedelta
import time

# Load config
with open("config.json") as f:
    config = json.load(f)

webhook_url = config["slack"]["webhook"]["url"]
token = config["tidyhq"]["token"]
contacts_url = "https://api.tidyhq.com/v1/contacts"
membership_url = "https://api.tidyhq.com/v1/membership_levels/{}/memberships"
contact_membership_url = "https://api.tidyhq.com/v1/contacts/{}/memberships"
change_group_url = "https://api.tidyhq.com/v1/groups/{}/contacts/{}"

group_pairs = []
group_pairs.append([9282, [9283], 2139, "band"])  # band
group_pairs.append([2069, [4958, 2368], 428, "concession"])  # concession
group_pairs.append([2077, [4957, 99624], 427, "full"])  # full


def get_contact(id):
    r = requests.get(contacts_url + "/" + str(id), params={"access_token": token})
    member = r.json()
    return member


def get_groups(contact):
    g = []
    for group in contact["groups"]:
        g.append(group["id"])
    return g


def get_memberships(id, raw=False):
    r = requests.get(contact_membership_url.format(id), params={"access_token": token})
    memberships = r.json()
    if raw == True:
        return memberships
    m = []
    for membership in memberships:
        m.append(membership["membership_level_id"])
    return m


def rm_from_group(group_id, contact_id):
    r = requests.delete(
        change_group_url.format(group_id, contact_id), params={"access_token": token}
    )
    time.sleep(1)
    if r.status_code == 204:
        return True
    return False


def add_to_group(contact_id, group_ids, since):
    if since > 0 or since < -35:
        return False
    exp = datetime.now() - timedelta(days=since)
    if exp.day < 16:
        group_id = group_ids[0]
    else:
        group_id = group_ids[-1]
    r = requests.put(
        change_group_url.format(group_id, contact_id), params={"access_token": token}
    )
    time.sleep(1)
    if r.status_code == 204:
        return True
    return False


def time_since_membership(memberships):
    newest = 60000
    for membership in memberships:
        try:
            date = datetime.strptime(membership["end_date"], "%Y-%m-%d")
        except ValueError:
            try:
                date = datetime.strptime(membership["end_date"][:10], "%d-%m-%Y")
            except ValueError:
                try:
                    date = datetime.strptime(membership["end_date"][:10], "%Y-%m-%d")
                except ValueError:
                    print("Tried both d-m-y and y-m-d ")
                    print(membership["end_date"])
                    print(type(membership["end_date"]))
        since = int((datetime.now() - date).total_seconds() / 86400)
        if since < newest:
            newest = int(since)
    return newest


def notify_slack(contact_id, days, alarm=False):
    member = get_contact(contact_id)
    billing_group = " (No billing group)"
    for group in member["groups"]:
        if "Billing" in group["label"]:
            billing_group = " (They are in a billing group)"
            break

    if not alarm:
        slack_data = {
            "text": f"<https://artifactory.tidyhq.com/contacts/{contact_id}|{member['first_name']} {member['last_name']}>'s membership is going to expire in {days} days.{billing_group}"
        }
    if alarm:
        slack_data = {
            "text": f":warning: <https://artifactory.tidyhq.com/contacts/{contact_id}|{member['first_name']} {member['last_name']}>'s membership has expired.{billing_group}\nThis is a bad thing that requires manual intervention. (Unless they've just put their membership on hold/resigned etc)\nReact to this message with a :+1: once the situation has been resolved."
        }
    requests.post(
        webhook_url,
        data=json.dumps(slack_data),
        headers={"Content-Type": "application/json"},
    )


for id in ["427", "428", "2139", "8208", "8285", "10465", "11479", "18830"]:
    r = requests.get(membership_url.format(id), params={"access_token": token})
    memberships = r.json()
    for membership in memberships:
        since = time_since_membership([membership])
        if since < 0 and since > -3:
            print(membership["contact_id"])
            notify_slack(membership["contact_id"], str(since * -1))
        elif since == 0:
            notify_slack(membership["contact_id"], str(since), alarm=True)
