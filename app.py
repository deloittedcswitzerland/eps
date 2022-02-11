# Import libraries
from flask import Flask, request, jsonify
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
from simple_salesforce import format_soql

# Import processor class
# einstein = EinsteinProcessor.EinsteinProcessor()

# Set app
app = Flask(__name__)

# Set constants
pw = '<insert>'
user = '<insert>'
orgId = '<insert>'
CLIENT_ID = '<insert>'
CLIENT_SECRET = '<insert>'
API_VERSION = 'v52.0'
model_id = ''
intent_model_id = 'DPCPNJLBCHDKWISI3ULU4WKXCY'
einstein_username = 'torbentiedemann@live.de'
pem_file='einstein_platform.pem'
EINSTEIN_VISION_URL = 'https://api.einstein.ai'


@app.route('/getmsg/', methods=['GET'])
def respond():
    # Retrieve the params from url
    case_id = request.args.get("caseId", None)   

    # For debugging
    print(f"got Id {case_id}")

    response = {}

    # Check if user sent a name at all
    if not case_id:
        response["ERROR"] = "no case_id found, please send a caseId."
    # Check if the user entered a number not a name
    elif str(case_id).isdigit():
        response["ERROR"] = "case_id can't be numeric."
    # Now the system entered a case_id
    else:
        response["MESSAGE"] = f"Thank you for sending {case_id} to our awesome platform!!"

    # Return the response in json format
    return jsonify(response)

@app.route('/post/', methods=['POST'])
def post_something():
    case_id = request.form.get('caseId')
    # model_id = request.form.get('modelId')
    # sobject = request.form.get('sObject')
    # model_type = request.form.get('modelType')
    # print(model_type)
    # print(case_id)
    # You can add the test cases you made in the previous function, but in our case here you are just testing the POST functionality
    if case_id:
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

        # Get ModelId
        sobject = 'Case' ## Change this in final release to accept var from callout
        model_id = (sf.query(format_soql("SELECT EPS_Model_Id__c FROM EPS_Config__mdt WHERE SObject__c={cId} LIMIT 1", cId=sobject)))['records'][0]['EPS_Model_Id__c']
        print(model_id)

        # Get Case record
        case_id = sf.Case.get(case_id)['Id']
        case_id
        print(case_id)
        
        # Get Case Subject
        case_subject = sf.Case.get(case_id)['Subject']
        print(case_subject)

        # Get EmailMessage
        email = sf.query(format_soql("SELECT Id, ThreadIdentifier FROM EmailMessage WHERE RelatedToId={var} ORDER BY CreatedDate ASC LIMIT 1", var=case_id))
        email_thread = email['records'][0]['ThreadIdentifier']
        email_id = email['records'][0]['Id']
        print(email_thread)
        print(email_id)

        # Get ContentDocument
        content_document = sf.query(format_soql("SELECT ContentDocumentId FROM ContentDocumentLink WHERE LinkedEntityId={var} LIMIT 1", var=email_id))
        content_document_id = content_document['records'][0]['ContentDocumentId']
        print(content_document_id)

        # Get ContentVersion
        content_version_id = (sf.query(format_soql("SELECT Id FROM ContentVersion WHERE ContentDocumentId={var} LIMIT 1", var=content_document_id)))['records'][0]['Id']
        print(content_version_id)

        # get VersionData from Content Version
        url = instance_url+'/services/data/' + API_VERSION + '/sobjects/ContentVersion/' + content_version_id + '/VersionData'
        headers = {'Authorization' : 'Bearer ' + access_token, 'X-PrettyPrint' : '1'}
        req = urllib.request.Request(url, None, headers)
        res = urllib.request.urlopen(req)
        # res_dict = json.load(res)
        base64_string = base64.b64encode(res.read()).decode('utf-8')

        # Get prediction for base64 string
        einstein_response = genius.get_b64_image_prediction(model_id=model_id, b64_encoded_string=base64_string)
        p = einstein_response.json()
        
        # Get prediction for Case Subject
        einstein_response = genius.get_language_prediction_from_model(model_id=intent_model_id, document=case_subject)
        p_intent = einstein_response.json()

        # Assign values for probabilities and labels to lists
        probabilities = []
        for i in range(5):
            var_p = ((p['probabilities'])[i])['probability']
            probabilities.append(var_p)

        labels = []
        for i in range(5):
            var_p = ((p['probabilities'])[i])['label']
            labels.append(var_p)
        print(labels)
        print(probabilities)
        
        # Assign values for intent probabilities and labels to lists
        intent_probabilities = []
        for i in range(3):
            var_pi = ((p_intent['probabilities'])[i])['probability']
            intent_probabilities.append(var_pi)

        intent_labels = []
        for i in range(3):
            var_pi = ((p_intent['probabilities'])[i])['label']
            intent_labels.append(var_pi)
        print(intent_labels)
        print(intent_probabilities)

        # update Case
        if sobject == 'Case':
            # demo logic start - replace after real intent model is built
            compare = intent_probabilities[2]
            new_car = intent_probabilities[1]
            used_car = intent_probabilities[0]
            if compare > 0.19:
                sf.Case.update(case_id,{'predicted_intent_probability__c': intent_probabilities[2], 'predicted_intent__c': intent_labels[2]})
            if new_car > 0.38:
                sf.Case.update(case_id,{'predicted_intent_probability__c': intent_probabilities[1], 'predicted_intent__c': intent_labels[1]})
            if used_car > 0.55:
                sf.Case.update(case_id,{'predicted_intent_probability__c': intent_probabilities[0], 'predicted_intent__c': intent_labels[0]})
            top_label = labels[0]
            # demo logic end
            sf.Case.update(case_id,{'predicted_probability__c': probabilities[0], 'predicted_label__c': labels[0]})
            top_label = labels[0]

        return jsonify({
            "Message": f"The car you are looking for is probably a Toyota {top_label}.",
            # Add this option to distinct the POST request
            "METHOD" : "POST"
        })
    else:
        return jsonify({
            "ERROR": "no Id found, please send an Id."
        })

# A welcome message to test our server
@app.route('/')
def index():
    return "<h1>Welcome to our aowsome platform. Try it out by sending an record!!</h1>"

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
