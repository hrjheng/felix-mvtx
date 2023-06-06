"""
Flask server to approve the CI jobs when accessing hardware resources on FLPs
Author: Ryan Patrick Hannigan
"""

from datetime import datetime
from flask import Flask, jsonify, request

import os
import requests
import sys

app = Flask(__name__)

WEBHOOK_URL = 'https://mattermost.web.cern.ch/hooks/eyjfk4yhi7gkx8mrmsx871c91e'
APPROVAL_TIME = 3600

global approved

setup = sys.argv[1]
branch = sys.argv[2]
port = sys.argv[3]
host = os.uname().nodename
repo = os.environ["CI_PROJECT_NAME"]

@app.route("/yes", methods=["POST"])
def update_yes():
    url = os.environ["CI_JOB_URL"]
    payload = {"update": {"message":f"You have approved the {repo}/{setup} pipeline :white_check_mark: You can track its status [here]({url})! ", "props" : {}}}
    global approved
    approved = True
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return jsonify(payload)

@app.route("/no", methods=["POST"])
def update_no():
    payload = {"update": {"message":f"The {repo}/{setup} pipeline has been rejected :red_circle: Nothing will be done.", "props" : {}}}
    global approved
    approved = False
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return jsonify(payload)

payload = {
    "attachments": [
        {
            "text": f"### Deployment pipeline for {setup} requested on project {repo} at branch **{branch}**\n**ONLY APPROVE IF SETUP(S) ARE NOT IN USE**.",
            "actions": [
                {
                    "name": "Approve",
                    "integration": {
                        "url": f"http://{host}:{port}/yes",
                    }
                }, {
                    "name": "Deny",
                    "integration": {
                        "url": f"http://{host}:{port}/no",
                    }
                }
            ]
        }
    ]
}

approved = False
response = requests.post(WEBHOOK_URL, json=payload)
if response.text != 'ok':
    sys.exit(1)
app.run(host=host, port=port, debug=True, use_reloader=False)
if approved:
    print("APPROVED")
    sys.exit(0)
else:
    print("DENIED")
    sys.exit(1)
