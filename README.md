# util
Collection of (typically) single file utility scripts used in the workshop that dont have a home elsewhere

## Configuration/setup

* `pip install -r requirements.txt`
* Set up Slack app using `manifest.json`
* `cp config.json.example config.json`
* Set `config.json` parameters
  * `slack/bot_token` - The bot token from your Slack app, only present after being installed to the workspace
  * `slack/app_token` - Create an app level token with access to `connections:write`
  * `slack/notification_channel` - The channel where general notification messages should be sent
  * `tidyhq/token` - A TidyHQ authentication token
  * `google/calendar_id` - The ID of your main event calendar
* Get `google.secret.json` by creating a google app with access to the calendar API.
* Run `auth_google.py` to get a token using `google.secret.json`

## Slack

### Send a notification to a configured channel when a new channel is created

Uses Slack's socket mode to listen for new channel creation events and sends a message to a preconfigured channel with the name of the new channel and who created it.

#### Setup

* Ensure that `slack/bot_token`, `slack/app_token`, and `slack/notification_channel` are set.

#### Running

This script will need some form of detached execution. Whether that's a screen, systemd, or something else is up to you.

* `monitor_new_channels.py`

## TidyHQ

### Public event report

Generates a HTML event report for event hosts that do not have access to TidyHQ. Initial code from [eventReports](https://github.com/Perth-Artifactory/eventReports)

#### Setup

* Ensure that `tidyhq/token` is set
* Adjust `event_report_template.html`
* `cp events.json.example events.json`
* Set up at least one report. The report name should be alphanumeric. Easiest way to get event IDs is to grab the number from the start of an event url. 

#### Running

* `event_report.py report_name > /var/www/reports/report_name.html`

## Misc

### Unauthenticated google calendar feed

Generates a JSON summary of upcoming calendar events

#### Setup

* Ensure `auth_google.py` has executed correctly and returned the details of the next event on the calendar

#### Running

This script will need some form of scheduled release. Recommend once a day.

* `export_calendar.py > /var/www/reports/calendar.json`