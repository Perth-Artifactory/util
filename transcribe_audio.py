import io
import json
import logging
import re
import sys
import time

import requests
from openai import OpenAI
from pydub import AudioSegment
from slack_bolt import App
from slack_sdk.web.slack_response import SlackResponse

# Check for --debug flag
if len(sys.argv) > 1 and "--debug" in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# load config from file
with open("config.json", "r") as f:
    config = json.load(f)

# Initiate OpenAI client
if config["slack"]["transcribe_calls"]:
    openai_client = OpenAI(api_key=config["openai"]["api_key"])

# Initiate Slack client as our user
app = App(token=config["slack"]["user_token"])
posting_app = App(token=config["slack"]["bot_token"])

# Get info for our Slack connection
slack_info = app.client.auth_test()  # type: ignore
print(f'Connected to Slack as "{slack_info["user"]}" with ID {slack_info["user_id"]}')

# Get all activity in the channel
channel_id = config["slack"]["phone_channel"]
response = app.client.conversations_history(channel=channel_id, limit=999)
messages = response["messages"]

print(f"Found {len(messages)} messages in channel {channel_id}")

name_map = {}


def transcode_to_mp3(wav_content) -> bytes:
    audio = AudioSegment.from_wav(io.BytesIO(wav_content))
    mp3_io = io.BytesIO()
    audio.export(mp3_io, format="mp3")
    return mp3_io.getvalue()


# Work from oldest messages to newest
messages.reverse()

for message in messages:
    # Skip messages from users
    if "bot_id" not in message:
        continue

    # Skip messages without an email attached
    if "files" not in message:
        continue

    email: dict = message["files"][0]

    subject: str = email["title"]

    # Extract the first phone number from the subject
    pattern = re.compile(r"[\d]+")
    match = pattern.search(subject)
    if match:
        phone_number: str = match.group()
        linked_number: str = f"<tel:{phone_number}|{phone_number}>"
    else:
        logging.error(f"No phone number found in subject: {subject}")
        continue

    if "voicemail" in subject.lower():
        call_type = "voicemail"
    elif "missed call" in subject.lower():
        call_type = "missed"

    # Look for voicemails
    if "attachments" in email and call_type == "voicemail":
        attachment: dict = email["attachments"][0]
        if "audio" in attachment["mimetype"]:
            # Download the audio file
            file_url: str = attachment["url"]
            print(f"Downloading {file_url}")
            r = requests.get(
                file_url,
                headers={"Authorization": "Bearer " + config["slack"]["bot_token"]},
            )
            if r.status_code != 200:
                logging.error(f"Failed to download {file_url}")
                continue

            # Transcode the audio file to mp3
            print("Transcoding audio file to mp3")
            voicemail: bytes = transcode_to_mp3(r.content)

            # Send the file as a file-like object
            mp3_io = io.BytesIO(voicemail)
            mp3_io.name = attachment["filename"].replace(".wav", ".mp3")

            if config["slack"]["transcribe_calls"]:
                transcription: str = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=mp3_io,
                    response_format="text",
                    language="en",
                )
                transcription = f"\n\n{transcription}"
            else:
                transcription = ""

    # Generate a human readable timestamp for the message
    ts: str = message["ts"].split(".")[0]
    timestamp: str = time.strftime("%Y-%m-%d %H:%M", time.localtime(int(ts)))

    posted = False

    if call_type == "voicemail":
        # Upload the mp3 to Slack
        upload_info: SlackResponse = posting_app.client.files_getUploadURLExternal(
            filename=attachment["filename"].replace(".wav", ".mp3"),
            length=len(voicemail),
            alt_text=f"Voicemail from {phone_number}",
        )

        upload_url: str = upload_info["upload_url"]
        uploaded_file: str = upload_info["file_id"]

        # Upload the file
        response = requests.post(
            upload_url,
            files={
                "file": (
                    attachment["filename"].replace(".wav", ".mp3"),
                    voicemail,
                    "audio/mp3",
                )
            },
        )
        if response.status_code != 200:
            logging.error(f"Failed to upload file to {upload_url}")

        # Send a message to the channel with the transcription
        notification_message: SlackResponse = posting_app.client.chat_postMessage(
            channel=channel_id,
            text=f"Voicemail from {phone_number}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"New voicemail from {linked_number}{transcription}",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "plain_text",
                            "text": timestamp,
                        }
                    ],
                },
            ],
            icon_emoji=":phone:",
            username="Celia | Phone Assistant",
        )

        # Complete the file upload and add the file to the message
        posting_app.client.files_completeUploadExternal(
            files=[{"id": uploaded_file, "title": f"Voicemail from {phone_number}"}],
            channel_id=channel_id,
            thread_ts=notification_message["ts"],
        )
        posted = True

    elif call_type == "missed":
        posting_app.client.chat_postMessage(
            channel=channel_id,
            text=f"Missed call from {phone_number}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Missed call from {linked_number}",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "plain_text",
                            "text": timestamp,
                        }
                    ],
                },
            ],
            icon_emoji=":phone:",
            username="Celia | Phone Assistant",
        )
        posted = True

    # Delete the email
    if posted:
        app.client.chat_delete(channel=channel_id, ts=message["ts"])
