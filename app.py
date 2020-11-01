# Import libraries
from flask import Flask, request, jsonify
app = Flask(__name__)
import urllib.request
import json
import getpass
import os
import sys
import gzip
import time
from io import BytesIO
import numpy as np
import pandas as pd
import base64
import requests
from urllib.request import urlopen
from EinsteinVision.EinsteinVision import EinsteinVisionService
from simple_salesforce import Salesforce

# Import processor class
# einstein = EinsteinProcessor.EinsteinProcessor()

# Set app
app = Flask(__name__)

# Set constants
pw = 'Figeroa7b$'
user = 'ttiedemann@ttiedemann-20201026.demo'
orgId = '00D09000002XvHR'
CLIENT_ID = '3MVG9SOw8KERNN0.JwiJmzWRWt.Hq1yiwY.3ABBqiBiHMkp89Zr2q4jPxeUJWQKmPeWwOitVn6uXD.fpdMrIx'
CLIENT_SECRET = 'EF4FD969656264A3186FE0B118BEBD7EC909255126BA2C0B7B40EA8A1E91ADC2'
API_VERSION = 'v49.0'
model_id = 'P6EUXCCZUVJQSVZNPDZK54OE6Q'
einstein_username = 'torbentiedemann@live.de'
pem_file='einstein_platform.pem'
EINSTEIN_VISION_URL = 'https://api.einstein.ai'


@app.route('/getmsg/', methods=['GET'])
def respond():
    # Retrieve the image string from url parameter
    image = request.args.get("image", None)

    # For debugging
    print(f"got name {image}")

    response = {}

    # Check if user sent a name at all
    if not image:
        response["ERROR"] = "no image found, please send a image."
    # Check if the user entered a number not a name
    elif str(image).isdigit():
        response["ERROR"] = "image can't be numeric."
    # Now the user entered a valid name
    else:
        response["MESSAGE"] = f"Thank you for sending {image} to our awesome platform!!"

    # Return the response in json format
    return jsonify(response)

@app.route('/post/', methods=['POST'])
def post_something():
    param = request.form.get('image')
    print(param)
    # You can add the test cases you made in the previous function, but in our case here you are just testing the POST functionality
    if param:
        # Define function to obtain SF access token
        def login():    
            # create a new salesforce REST API OAuth request
            url = 'https://login.salesforce.com/services/oauth2/token'
            data = { 'grant_type': 'password', 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'username': user, 'password': pw}
            # print(data)
            headers = {'X-PrettyPrint' : '1'}

            # call salesforce REST API and pass in OAuth credentials
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(url, encoded_data, headers)
            # print(req)
            res = urllib.request.urlopen(req)

            # load results to dictionary
            res_dict = json.load(res)

            # close connection
            res.close()

            # return OAuth access token necessary for additional REST API calls
            access_token = res_dict['access_token']
            instance_url = res_dict['instance_url']

            return access_token, instance_url

        # Login via simple-salesforce
        sf = Salesforce(password=pw, username=user, organizationId=orgId)

        # login via access token
        access_token, instance_url = login()

        # Retrieve Einstein Platform Services access token
        genius = EinsteinVisionService(email=einstein_username, pem_file=pem_file)
        genius.get_token()

        # Get ContentVersion record
        contentVersionId = (sf.query("SELECT Id FROM ContentVersion ORDER BY CreatedDate DESC LIMIT 1"))['records'][0]['Id']

        # Get Case record
        caseId = (sf.query("SELECT Id FROM Case ORDER BY CreatedDate DESC LIMIT 1"))['records'][0]['Id']

        # get VersionData from Content Version
        url = instance_url+'/services/data/' + API_VERSION + '/sobjects/ContentVersion/' + contentVersionId + '/VersionData'
        headers = {'Authorization' : 'Bearer ' + access_token, 'X-PrettyPrint' : '1'}
        req = urllib.request.Request(url, None, headers)
        res = urllib.request.urlopen(req)
        # res_dict = json.load(res)
        base64_string = base64.b64encode(res.read()).decode('utf-8')

        # Get prediction for base64 string
        einstein_response = genius.get_b64_image_prediction(model_id=model_id, b64_encoded_string=base64_string)
        p = einstein_response.json()

        # Assign values for probabilities and labels to lists
        probabilities = []
        for i in range(5):
            var_p = ((p['probabilities'])[i])['probability']
            probabilities.append(var_p)

        labels = []
        for i in range(5):
            var_p = ((p['probabilities'])[i])['label']
            labels.append(var_p)
        # print(labels)
        # print(probabilities)

        # update Case
        sf.Case.update(caseId,{'predicted_probability__c': probabilities[0], 'predicted_label__c': labels[0]})
        top_label = labels[0]

        return jsonify({
            "Message": f"The car you are looking for is probably a Toyota {top_label}.",
            # Add this option to distinct the POST request
            "METHOD" : "POST"
        })
    else:
        return jsonify({
            "ERROR": "no name found, please send a name."
        })

# A welcome message to test our server
@app.route('/')
def index():
    return "<h1>Welcome to our aowsome platform. Try it out by sending an image!!</h1>"

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)