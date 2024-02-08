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
* Set a Slack notification channel

#### Running

`link_slack_tidyhq.py [--debug --cron]`

* debug: Adds debugging messages
* cron: Does not prompt for manual override and does not ask for confirmation before linking

### Apply corrections to TidyHQ contact fields

* Capitalise contact names
* Strip whitespace
* Remove nicknames that match first names

#### Setup

* Ensure that TidyHQ credentials have been set in `config.json`

#### Running

`correct_tidyhq_contacts.py [--debug --cron]`

* debug: Adds debugging messages
* cron: Applies corrections automatically and with no output

### Bulk create TidyHQ groups

Bulk create TidyHQ groups with a specific prefix.

#### Setup

* Ensure that TidyHQ credentials have been set in `config.json`

#### Running

`add_groups.py` and follow the prompts.

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

### Notify slack channel when a receipt has been submitted to Paperless-NGX

#### Setup

* Note this script will install `requests` and `slack_bolt` itself. This allows it to be more easily deployed with a Paperless install deployed via Docker.
* Ensure that a Slack bot token and channel has been set in `config.json` OR directly in the script
* The URLs are currently hardcoded, update as desired.
* Point Paperless-NGX to the script via [PAPERLESS_POST_CONSUME_SCRIPT](https://docs.paperless-ngx.com/advanced_usage/#post-consume-script)

#### Running

Triggered automatically