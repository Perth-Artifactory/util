import requests
import json
import subprocess
import sys


def switch_on(entity: str, config: dict) -> bool:
    print(f"Turning on {entity}")

    if not entity.startswith("switch."):
        entity = "switch." + entity

    url = config["home_assistant"]["url"]
    headers = {
        "Authorization": f"Bearer {config['home_assistant']['token']}",
        "content-type": "application/json",
    }

    payload = {"entity_id": entity}

    response = requests.post(
        url + "services/switch/turn_on", headers=headers, json=payload
    )

    if response.status_code in [200, 201]:
        print(f"{entity} turned on")
        return True
    else:
        print(f"Failed to turn on {entity}")
        print(response.text)
        return False


def turn_on_air_purifier(message, app, config):
    print("Turning on air purifier")
    url = config["home_assistant"]["url"]
    headers = {
        "Authorization": f"Bearer {config['home_assistant']['token']}",
        "content-type": "application/json",
    }

    # Get the current state of the air purifier
    response = requests.get(
        url + "states/number.design_purifier_fan_level", headers=headers
    )

    if response.status_code in [200, 201]:
        current_level = response.json()["state"]
        try:
            current_level = int(current_level)
        except ValueError:
            print("Failed to parse air purifier level, assuming off")
            current_level = 0
        print(f"Current air purifier level: {current_level}")
        if current_level < 2:
            payload = {"entity_id": "fan.design_purifier", "percentage": 65}

            response = requests.post(
                url + "services/fan/turn_on", headers=headers, json=payload
            )

            if response.status_code in [200, 201]:
                print("Turned on air purifier")
                return True
            else:
                print("Failed to turn on air purifier")
                print(response.text)
                return False


def elab_lights(message, app, config) -> bool:
    return switch_on(entity="switch.iw_relay_electronics_lab_lights", config=config)


def foyer_lights(message, app, config) -> bool:
    return switch_on(entity="switch.sonoff_1001856f13", config=config)


def hud_image(message, app, config):
    """Writes the message block to a file and triggers the HUD image generator script"""

    try:
        with open(config["hud"]["json"], "w") as f:
            json.dump(message, f, indent=4)
    except Exception as e:
        print(f"Failed to write HUD message data: {e}")
        return False

    subprocess.run([sys.executable, "generate_image.py"])

    return True


def demo_func(message, app, config):
    from pprint import pprint

    print("Message block:")
    pprint(message)


# function tester
if __name__ == "__main__":
    print("Select a function to test:")
    print("1. turn_on_air_purifier")
    print("2. elab_lights")
    print("3. hud_image")
    print("4. demo_func")
    choice = input("Choice: ")
    if choice in ["1", "2", "3", "4"]:
        import json
        from slack_bolt import App

        with open("config.json", "r") as f:
            config = json.load(f)
        app = App(token=config["slack"]["bot_token"])

        if choice == "1":
            print("Running turn_on_air_purifier:")
            turn_on_air_purifier(None, app, config)

        if choice == "2":
            print("Running elab_lights:")
            elab_lights(None, app, config)

        if choice in ["3", "4"]:
            print("Loading Slack message from trigger channel...")
            # Retrieve the latest message from the trigger channel
            response = app.client.conversations_history(
                channel=config["slack"]["trigger_channel"], limit=1
            )

            message = response["messages"][0]  # type: ignore

            if choice == "3":
                print("Running hud_image:")
                hud_image(message, app, config)

            if choice == "4":
                print("Running demo_func:")
                demo_func(message, app, config)
