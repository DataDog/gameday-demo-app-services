from flask import Flask, request, jsonify, render_template, Blueprint, current_app
from ddtrace.contrib.trace_utils import set_user
from flask_login import login_required, current_user
from ddtrace import tracer
import requests
import boto3
from boto3.dynamodb.conditions import Attr
import random

main = Blueprint('main', __name__)

def get_penpal():
    penpals = {}

    user_table = current_app.config['PENPAL_TABLE']
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(user_table)

    response = table.scan(
        FilterExpression=Attr('available').eq(True)
    )
    for item in response['Items']:
        penpals[item['UserID']] = {
            'name': item['name'],
            'email': item['UserID']
        }
    print(f"Got penpals: {penpals}")

    # return random penpal
    if penpals:
        return random.choice(list(penpals.values()))
    return None

def analyze_external_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def upload_photo(url):
    return

@main.route('/hello', methods=['GET'])
def hello():
    return "Hello, World!"

@main.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@main.route('/match_penpal', methods=['GET'])
@login_required
def match_penpal():
    return render_template('match_form.html', name=current_user.name)

@main.route('/test_user_url', methods=['POST'])
def test_user_url():
    # Enhance functionality by trying to fetch details from the user provided URL
    # Show the user response contents
    # Inform the user if the URL is not reachable
    set_user(tracer, user_id = current_user.id, name=current_user.name, email=current_user.email,
         role="premium-user", propagate=True)
    user_url = request.json.get('url')
    print(f"Testing user URL: {user_url}")
    try:
        response = requests.get(user_url)
        if response.status_code == 200:
            return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": "We can't reach this URL, please try again"}), 400

@main.route('/match_penpal', methods=['POST'])
@login_required
def match_penpal_post():
    user_id = current_user.id
    details_url = request.json.get('details_url')

    # get input from matching form
    hobbies = request.form.get('hobbies')
    favoriteColor = request.form.get('favoriteColor')
    favoriteQuote = request.form.get('favoriteQuote')
    profileUrl = request.form.get('profileUrl')
    photoUrl = request.form.get('photoUrl')

    if photoUrl:
        upload_photo(photoUrl)

    if profileUrl:
        analyze_external_data(profileUrl)
    
    # Find a matching penpal for the user (logic can be expanded)
    matched_penpal = get_penpal()

    # SSRF Vulnerability: Make a request to the user-supplied URL
    if details_url:
        try:
            response = requests.get(details_url)
            # Assume the response is JSON and add it to the penpal data
            matched_penpal['details'] = response.json()
        except requests.RequestException as e:
            return jsonify({"error": "Failed to fetch penpal details"}), 400

    return jsonify(matched_penpal)

if __name__ == '__main__':
    main.run(host="0.0.0.0", port=3333)