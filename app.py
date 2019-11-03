import json

from flask import Flask, flash, render_template, request
from requests import Request, post
from wtforms import (Form, IntegerField, StringField, SubmitField,
                     TextAreaField, TextField, validators)
import os
DEBUG = False
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

def parse_request(message:dict):
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

def generate_request(auth_key:str , device_name:str , polltime:int):
    # Hub name in sr=iothubname.azure-devices.net&
    hub_name = auth_key.split("&")[0].split("=")[1]
    headers = {
        "Authorization": f"SharedAccessSignature {auth_key}",
        "Content-Type": "applications/json"
    }
    payload = {
        "methodName":"polltime",
        "responseTimeoutInSeconds":60,
        "payload":{
            "polltime": int(polltime)
        }
    }
    try:
        resp = post(f"https://{hub_name}/twins/{device_name}/methods?api-version=2018-06-30",data=json.dumps(payload),headers=headers,timeout=60)
        return parse_request(resp.json())
    except Exception as e:
        return f"Error: {e}"

class ReusableForm(Form):
    auth_key = StringField("auth_key")
    device_name = StringField("device_name")
    poll_time = IntegerField("poll_time")
    slider_timeout = IntegerField("slider_timeout")

@app.route("/", methods=['GET', 'POST'])
def main():
    form = ReusableForm(request.form)

    #print(form.errors)
    if request.method == 'POST':
        auth_key=request.form['auth_key']
        device_name=request.form['device_name']
        poll_time=request.form['poll_time']
        flash(generate_request(auth_key,device_name,poll_time))

    return render_template('index.html', form=form)

if __name__ == "__main__":
    app.run()
