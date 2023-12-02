# util

Collection of (typically) single file utility scripts used in the workshop that don't have a home elsewhere

## Requirements

* Python 3.10+

## Configuration/setup

* `pip install -r requirements.txt`
* Set up Slack app using `manifest.json`
* `cp config.json.example config.json`
* Set `config.json` parameters
  * `slack/bot_token` - The bot token from your Slack app, only present after being installed to the workspace
  * `slack/app_token` - Create an app level token with access to `connections:write`
  * `slack/notification_channel` - The channel where general notification messages should be sent
  * `tidyhq/token` - A TidyHQ authentication token
  * `tidyhq/ids`
    * `slack` - The custom field ID for a slack user ID
  * `google/calendar_id` - The ID of your main event calendar
  * `download_dir` - A directory to download files to
* Get `google.secret.json` by creating a google app with access to the calendar API.
* Run `auth_google.py` to get a token using `google.secret.json`

## Scripts

### Send a notification to a configured channel when a new channel is created

Uses Slack's socket mode to listen for new channel creation events and sends a message to a preconfigured channel with the name of the new channel and who created it.

#### Setup

* Ensure that `slack/bot_token`, `slack/app_token`, and `slack/notification_channel` are set.

#### Running

This script will need some form of detached execution. Whether that's a screen, systemd, or something else is up to you.

* `monitor_new_channels.py`

### Public TidyHQ event report

Generates a HTML event report for event hosts that do not have access to TidyHQ. Initial code from [eventReports](https://github.com/Perth-Artifactory/eventReports)

#### Setup

* Ensure that `tidyhq/token` is set
* Adjust `event_report_template.html`
* `cp events.json.example events.json`
* Set up at least one report. The report name should be alphanumeric. Easiest way to get event IDs is to grab the number from the start of an event url.

#### Running

* `event_report.py report_name > /var/www/reports/report_name.html`

### Duplicate TidyHQ events

Creates repeating TidyHQ events

#### Setup

* Ensure that `tidyhq/token` is set

#### Running

* `duplicate_events.py` - follow the prompts

### Unauthenticated google calendar feed

Generates a JSON summary of upcoming calendar events from either Google Calendar or TidyHQ.

#### Setup

* Ensure `auth_google.py` has executed correctly and returned the details of the next event on the calendar if using Google Calendar.
* Ensure `tidyhq/token` is set if using TidyHQ

#### Running

This script will need some form of scheduled release. Recommend once a day.

* `export_calendar.py [tidyhq|gcal] > /var/www/reports/calendar.json`

### Match TidyHQ contacts with Slack users

Matches TidyHQ contacts with Slack user accounts based on registration email. Only flags TidyHQ contacts missing on Slack if they have an active membership.

#### Setup

* Ensure that Slack and TidyHQ credentials have been set in `config.json`
* Set a custom field for Slack IDs

#### Running

`link_slack_tidyhq.py`

### Generate list of machine operators based on TidyHQ groups

Formats a markdown table of approved operators based on whether a contact is in a configured TidyHQ group

#### Setup

* Ensure that TidyHQ credentials have been set in `config.json`
* `cp machines.json.example machines.json`
  * Configure at least one report. Report names should be alphanumeric.

#### Running

`operator_report.py report_name` will output a markdown formatted table. It explicitly does not include a "generated on" line so that it doesn't trigger unnecessary page changes.

This can be used to push a report by:

* Cloning the wiki
* `sed -i '11,$ d' path/to/wiki_page` - Remove the contents of the page after the header (header is typically 10 lines)
* `python3 operator_report.py report_name >> path/to/wiki_page`
* Commit the changed file

eg.

```bash
#!/bin/bash

page=~/committee/wiki/docs/reports/Laser_operators.md

# Update wiki repo
cd ~/committee/wiki/
git fetch --all
git reset --hard origin/main

# Purge existing report

sed -i '11,$ d' $page

# Add new report to end of page

cd ~/util
python3 operator_report.py lasers >> "${page}"

# Commit report if it's changed

cd ~/committee/wiki/
git add $page
git commit -m "Update laser operators from TidyHQ"
git push
```

### Download files sent to a Slack channel

Allow users to submit files in a slack channel and ingest them into other applications

#### Setup

* Ensure that Slack credentials have been set in `config.json` and a download directory has been set

#### Running

* `dl_slack_files.py [-d] <channel_id>`

`-d` will run the script in "daemon" mode. The script will wait 60 seconds between loops.

### Generate a snapshot of TidyHQ memberships

Generate membership numbers for a particular date

#### Setup

* Ensure that a TidyHQ token has been set in `config.json`

#### Running

* `tidyhq_membership_snapshot.py`
