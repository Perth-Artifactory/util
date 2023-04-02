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

## Slack

### Send a notification to a configured channel when a new channel is created

Uses Slack's socket mode to listen for new channel creation events and sends a message to a preconfigured channel with the name of the new channel and who created it.

`monitor_new_channels.py`