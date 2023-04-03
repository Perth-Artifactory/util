import requests
import logging
import json
from slack_bolt import App
from datetime import datetime

# load config from config.json
with open("config.json","r") as f:
    config: dict = json.load(f)

# Initiate Slack client
app = App(token=config["slack"]["bot_token"])

# Get a list of contacts from TidyHQ that are not linked to a Slack account
def get_tidyhq():
    logging.debug("Attempting to get contact dump from TidyHQ...")
    try:
        r = requests.get("https://api.tidyhq.com/v1/contacts",params={"access_token":config["tidyhq"]["token"]})
        contacts = r.json()
    except requests.exceptions.RequestException as e:
        logging.error("Could not reach TidyHQ")
        return False
    c = {}
    for contact in contacts:
        in_slack = False
        for field in contact["custom_fields"]:
            if field["id"] == config["tidyhq"]["ids"]["slack"] and field["value"]:
                in_slack = True
        if not in_slack:
            c[contact['email_address']] = contact
    return c

def get_slack():
    r = app.client.users_list()
    c = {}
    for user in r.data["members"]:
        email = user["profile"].get("email")
        if email:
            c[email] = {"id":user["id"],
                        "name":user["profile"].get("real_name_normalized")}
    return c

def time_since_membership(memberships: list[dict]) -> int:
    """Returns the number of days since the most recent membership expired
    Negative numbers indicate that the membership is still active"""
    newest = 60000
    for membership in memberships:
        try:
            date = datetime.strptime(membership["end_date"], "%Y-%m-%d")
        except ValueError:
            try:
                date = datetime.strptime(membership["end_date"], "%d-%m-%Y")
            except ValueError:
                print(membership)
        since = int((datetime.now()-date).total_seconds()/86400)
        if since < newest:
            newest = int(since)
    return newest

def get_tidyhq_memberships():
    r = requests.get("https://api.tidyhq.com/v1//memberships",params={"access_token":config["tidyhq"]["token"]})
    memberships = r.json()
    active = []
    for membership in memberships:
        if membership["state"] != "expired":
            active.append(membership["id"])
    return active

slack_users = get_slack()
tidyhq_users = get_tidyhq()
tidyhq_active_users = get_tidyhq_memberships()

# Compare the two lists and link any users that are in both
for email in tidyhq_users:
    if email in slack_users:
        print("\n")
        t = tidyhq_users[email]
        s = slack_users[email]
        # Link the user
        print(f"Match:\nTidyHQ: {t['first_name']} {t['last_name']} ({t['id']})\nSlack: {s['name']} ({s['id']})")
        i = input("Yes? [Y/n]")
        if i != "n":
            try:
                r = requests.put(f"https://api.tidyhq.com/v1/contacts/{t['id']}",
                                params={"access_token":config["tidyhq"]["token"]},
                                json={"custom_fields":{config["tidyhq"]["ids"]["slack"]:slack_users[email]["id"]}})
                if r.status_code != 200:
                    print(f"Could not link")
                    print(r.text)
                else:
                    print("Linked")
                    # Remove the user from the TidyHQ list of people already linked
                    del tidyhq_users[email]

            except requests.exceptions.RequestException as e:
                logging.error(f"Could not link {tidyhq_users[email]['name']}")
        else:
            print("Skipping")
    else:
        if tidyhq_users[email]["id"] in tidyhq_active_users:
            print(f"Could not find {tidyhq_users[email]['first_name']} {tidyhq_users[email]['last_name']} in Slack but they are an active member")