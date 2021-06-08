import flask
from flask import jsonify 
import werkzeug
import requests 
from requests import get, post
import os
import time
import getopt
import sys
import re
import json
# from .Analyze import runAnalysis, convert_to_simple_json


def runAnalysis(input_file, output_file, file_type):
    # Endpoint URL
    endpoint = r"https://digitalpathology.cognitiveservices.azure.com/"
    # Subscription Key
    apim_key = "Paste your Form recognizer cognitive service API key here."
    # Model ID
    model_id = "Paste model ID here which will given by Form recognizer here."
    # API version
    API_version = "v2.1-preview.3"

    post_url = endpoint + "/formrecognizer/%s/custom/models/%s/analyze" % (API_version, model_id)
    params = {
        "includeTextDetails": True
    }

    headers = {
        # Request headers
        'Content-Type': file_type,
        'Ocp-Apim-Subscription-Key': apim_key,
    }
    try:
        with open(input_file, "rb") as f:
            data_bytes = f.read()
    except IOError:
        print("Inputfile not accessible.")
        sys.exit(2)

    try:
        print('Initiating analysis...')
        resp = post(url = post_url, data = data_bytes, headers = headers, params = params)
        if resp.status_code != 202:
            print("POST analyze failed:\n%s" % json.dumps(resp.json()))
            quit()
        print("POST analyze succeeded:\n%s" % resp.headers)
        print
        get_url = resp.headers["operation-location"]
    except Exception as e:
        print("POST analyze failed:\n%s" % str(e))
        quit()

    n_tries = 15
    n_try = 0
    wait_sec = 5
    max_wait_sec = 60
    print()
    print('Getting analysis results...')
    while n_try < n_tries:
        try:
            resp = get(url = get_url, headers = {"Ocp-Apim-Subscription-Key": apim_key})
            resp_json = resp.json()
            if resp.status_code != 200:
                print("GET analyze results failed:\n%s" % json.dumps(resp_json))
                quit()
            status = resp_json["status"]
            if status == "succeeded":
                if output_file:
                    with open(output_file, 'w') as outfile:
                        json.dump(resp_json, outfile, indent=2, sort_keys=False)
                # print("Analysis succeeded:\n%s" % json.dumps(resp_json, indent=2, sort_keys=False))
                print()
                print("[+] Analysis succeeded...")
                # convert_to_simple_json(resp_json)
                # print()
                # print("[+] Conversions succeeded...")
                return
                # quit()
            if status == "failed":
                print("Analysis failed:\n%s" % json.dumps(resp_json))
                # quit()
                return
            # Analysis still running. Wait and retry.
            time.sleep(wait_sec)
            n_try += 1
            wait_sec = min(2*wait_sec, max_wait_sec)     
        except Exception as e:
            msg = "GET analyze results failed:\n%s" % str(e)
            print(msg)
            # quit()
            return
    print("Analyze operation did not complete within the allocated time.")

def convert_to_simple_json(data):
    json_data = {}
    docResults = data['analyzeResult']['documentResults'][0]['fields']
    for i in docResults:
        if docResults[i]['type'] == 'string':
            if 'valueString' in docResults[i]:
                json_data[i] = docResults[i]['valueString']
            else:
                json_data[i] = ''
        if docResults[i]['type'] == 'array':
            if 'valueArray' in docResults[i]:
                table_data = docResults[i]['valueArray']
                tb_data = {}
                for j in table_data:
                    test_data = j['valueObject']
                    test_type = test_data['tests']['valueString']
                    if test_data['results'] != None:
                        result = test_data['results']['valueString']
                    else:
                        result = None
                    if test_data['units'] != None:
                        units = test_data['units']['valueString']
                    else:
                        units = None
                    if test_data['reference_range'] != None:
                        ranges = test_data['reference_range'
                                ]['valueString']
                    else:
                        ranges = None
                    tb_data[test_type] = {}
                    tb_data[test_type]['results'] = result
                    tb_data[test_type]['units'] = units
                    tb_data[test_type]['reference_range'] = ranges
    json_data[i] = tb_data
    print()
    print("[+] After Conversions... \n")
    print(json.dumps(json_data, indent = 2))
    return json_data

app = flask.Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

@app.route('/upload', methods = ['GET', 'POST'])
def handle_request():
    imagefile = flask.request.files['image']
    filename =  'images/' + werkzeug.utils.secure_filename(imagefile.filename)
    os.makedirs('images', exist_ok=True)
    print("\nReceived image File name : " + filename)
    imagefile.save(filename)

    runAnalysis(filename, filename + '.json', 'images/' + filename.split('.')[-1])
    with open(filename + '.json', 'r') as f:
    	data = f.read()
    	data = json.loads(data)
    	data= convert_to_simple_json(data)
    	print("[+] Conversions succeeded...")

    return jsonify(data)
