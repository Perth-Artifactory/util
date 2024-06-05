import requests


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
        print(f"Current air purifier level: {current_level}")
        if current_level < 2:
            payload = {"entity_id": "fan.design_purifier", "percentage": 67}

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


def elab_lights(message, app, config):
    print("Turning on elab lights")
    url = config["home_assistant"]["url"]
    headers = {
        "Authorization": f"Bearer {config['home_assistant']['token']}",
        "content-type": "application/json",
    }

    payload = {"entity_id": "switch.iw_relay_electronics_lab_lights"}

    response = requests.post(
        url + "services/switch/turn_on", headers=headers, json=payload
    )

    if response.status_code in [200, 201]:
        print("Elab lights turned on")
        return True
    else:
        print("Failed to turn on elab lights")
        print(response.text)
        return False


# function tester
if __name__ == "main":
    print("Select a function to test:")
    print("1. turn_on_air_purifier")
    print("2. elab_lights")
    choice = input("Choice: ")
    if choice in ["1", "2"]:
        import json
        from slack_bolt import App

        with open("config.json", "r") as f:
            config = json.load(f)
        app = App(token=config["slack"]["bot_token"])

        if choice == "1":
            turn_on_air_purifier(None, app, config)

        if choice == "2":
            elab_lights(None, app, config)
