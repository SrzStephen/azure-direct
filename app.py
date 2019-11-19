import json
from knobs import Knob
from flask import Flask, flash, render_template, request
from requests import post, get
from wtforms import (Form, IntegerField, StringField, SelectField)
import os
import logging

logger = logging.getLogger(__name__)

DEBUG = False
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = os.urandom(24)


class EndpointClass:

    def __init__(self):
        self.api_endpoint_base = Knob(env_name="AZURE_API_ENDPOINT", default="www.google.com",
                                      description="C# API endpoint")
        self.api_access_key = Knob(env_name="AZURE_API_HOST_KEY", default="12345678", description="C# API host key")

    def direct_call(self, method, payload, device):
        url = f"{self.api_endpoint_base.get()}/api/DirectCall/?code={self.api_access_key.get()}"
        logger.debug("Making request with url {url}")
        headers = {"method_name": method, "target_device": device}
        response = post(url, headers=headers, data=payload)
        try:
            return True, response.json()
        except json.JSONDecodeError:
            return False, f"Error: {response.content}"

    def get_devices(self):
        url = f"{self.api_endpoint_base.get()}/api/GetDevices/?code={self.api_access_key.get()}"
        response = get(url)
        try:
            if response.status_code == 200:
                device_list = []
                for device in response.json():
                    device_list.append(dict(name=device['device_name'], online=device['device_status']))
                return device_list
            else:
                logger.warning(f"Failed to get device list from url {url}")
                logger.debug(f"{response.status_code}  {response.content}")
            return response
        except json.JSONDecodeError:
            logger.error(f"Non JSON response returned for 200 error code at {url}")


def parse_request(message: dict):
    if "Message" in message:
        # looks like a microsoft IOT hub message
        msg = json.loads(message['Message'])
        error_code = msg['errorCode']
        error_message = msg['message']
        return f"Error: IOTHUB error {error_code} \n {error_message}"
    elif "payload" in message:
        success = bool(message['payload']['success'])
        response_message = message['payload']['message']
        if success:
            return f"{response_message}"
        else:
            return f"Error: Message"


class ReusableForm(Form):
    choices = []
    api = EndpointClass()
    device_list = api.get_devices()
    if device_list is None:
        choices = [("No device found", "No device found")]
    else:
        for item in device_list:
            choices.append((item['name'], f"{item['name']} ({'online' if item['online'] == 1 else 'offline'})"))

    device_name = SelectField("device_name", choices=choices)
    auth_key = StringField("auth_key")
    poll_time = IntegerField("poll_time")
    slider_timeout = IntegerField("slider_timeout")


@app.route("/", methods=['GET', 'POST'])
def main():
    form = ReusableForm(request.form)
    api = EndpointClass()
    if request.method == 'POST':
        device_name = request.form['device_name']
        try:
            poll_time = int(request.form['poll_time'])
        except ValueError:
            flash("Error: Polltime needs to be an integer value")
            return render_template('index.html', form=form)

        status, result = api.direct_call("polltime", json.dumps({"polltime": poll_time}), device_name)
        if status:
            if bool(result.get("success", False)):
                flash(f"Updated poll time to {poll_time} on device {device_name}")
        else:
            flash(f"Error: Failed to update device {device_name}, error {result}")
    return render_template('index.html', form=form)


if __name__ == "__main__":
    app.run()
