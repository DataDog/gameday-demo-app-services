from flask import Blueprint, render_template, request, jsonify, current_app, g, logging
from flask.logging import default_handler
from functools import wraps
import boto3
import jwt
import os
import time
import random, uuid
from boto3.dynamodb.conditions import Attr
import requests
from ddtrace.contrib.trace_utils import set_user
from ddtrace.appsec.trace_utils import track_custom_event
from ddtrace import tracer

main = Blueprint('main', __name__)
SECRET_KEY = "our-super-special-secret-key"  # Replace with secure storage (e.g., AWS Secrets Manager)

def jwt_required(func):
    """Decorator to validate JWT from headers, query parameters, or cookies."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get token from Authorization header if exists
        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1]
        else:
            # If no header, check query parameters
            token = request.args.get("token")
            if not token:
                # If no query parameter, check cookies
                token = request.cookies.get("access_token")

        if not token:
            return jsonify({"message": "Missing token"}), 401
        
        logger = current_app.logger
        logger.info(f"Validating JWT token: {token}")
        
        try:
            # Decode the JWT
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            # Attach user info to the request context
            g.current_user = {
                "id": payload.get("sub"),
                "name": payload.get("name")
            }

            # Add user information to the Datadog trace
            set_user(
                tracer,
                user_id=g.current_user["id"],
                name=g.current_user["name"],
                email=g.current_user["id"],
                propagate=True
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"message": f"Invalid token: {str(e)}"}), 401

        return func(*args, **kwargs)

    return wrapper

def summarize_url_vibes(html_content):
    """
    Summarize the vibes of the HTML content using AI.
    We do this by sending the content to an AI model and getting a summary.
    This helps the user test what sort of insights we will get from their URL before they submit the form.
    """
    print(f"Summarizing vibes of HTML content: {html_content}")

    # analyze_user_content_with_fancy_ai(html_content)  # Placeholder function for AI analysis
    # in demo, we will just return a random response
    static_responses = [
        "This content seems very positive and uplifting!",
        "We will find a penpal as clever as you!",
        "We will find the perfect techy penpal to match you techy vibe!",
        "We will find a penpal that matches your adventurous spirit!",
        "Based on this URL, we will find a penpal that matches your air of mystery!",
    ]

    return random.choice(static_responses)

def save_penpal_match(user_id: str, penpal_id: str):
    """Save new penpal match to dynamoDB."""
    
    match_table = os.getenv('MATCHES_TABLE')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(match_table)
    logger = current_app.logger

    logger.info("Writing penpal match DynamoDB") 
    response = table.put_item(Item={
        'penpal_id': penpal_id,
        'match_id': str(uuid.uuid4()),
        'user_id': user_id,
        'timestamp': int(time.time())
    })
    logger.info(f"Saved match: {response}")

    return 

def save_user_details(user_response: dict):
    """Save user details from match form to DynamoDB users table."""

    user_table = os.getenv('USER_TABLE')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(user_table)

    user_id = user_response.get("usr.id")
    if not user_id:
        raise ValueError("User ID is required")

    logger = current_app.logger
    logger.info("Writing user details to DynamoDB")

    # Build the update expression dynamically
    update_fields = []
    expression_attribute_values = {}

    # Required fields
    if "hobbies" in user_response:
        update_fields.append("hobbies = :hobbies")
        expression_attribute_values[":hobbies"] = user_response["hobbies"]

    if "favorite_color" in user_response:
        update_fields.append("favorite_color = :favorite_color")
        expression_attribute_values[":favorite_color"] = user_response["favorite_color"]

    if "favorite_quote" in user_response:
        update_fields.append("favorite_quote = :favorite_quote")
        expression_attribute_values[":favorite_quote"] = user_response["favorite_quote"]

    # Optional fields
    if "external_profile_url" in user_response:
        update_fields.append("external_profile_url = :external_profile_url")
        expression_attribute_values[":external_profile_url"] = user_response["external_profile_url"]

    if "external_photo_url" in user_response:
        update_fields.append("external_photo_url = :external_photo_url")
        expression_attribute_values[":external_photo_url"] = user_response["external_photo_url"]

    # Join all update fields with commas
    update_expression = "SET " + ", ".join(update_fields)

    try:
        response = table.update_item(
            Key={"user_id": user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW"  # Returns only the updated attributes
        )
        logger.info(f"Successfully updated item in DynamoDB: {response['Attributes']}")
        return response
    except Exception as e:
        logger.error(f"Error updating item in DynamoDB: {e}", exc_info=True)
        raise

def make_penpal_match(user_id: str):
    """Fetch available penpals from the DynamoDB table and assign match."""
    
    logger = current_app.logger
    logger.info("Getting penpals from DynamoDB") 

    penpals = {}
    user_table = os.getenv('PENPAL_TABLE')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(user_table)

    response = table.scan(FilterExpression=Attr('available').eq(True))
    for item in response['Items']:
        penpals[item['penpal_id']] = {
            'name': item['penpal_name']
        }

    logger.info(f"Got penpals: {penpals}")

    # do fancy logic to match user to their perfect penpal
    matched_penpal_id = random.choice(list(penpals.keys())) if penpals else None
    if matched_penpal_id:
        save_penpal_match(user_id, matched_penpal_id)

    return penpals[matched_penpal_id] if matched_penpal_id else None

def analyze_external_data(url: str):
    """Fetch and analyze external data from a given URL."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        print(f"Error fetching external data: {e}")
    return None

def upload_photo(url: str):
    """Placeholder function for uploading a photo."""
    print(f"Uploading photo from URL: {url}")
    return

@main.route('/match/hello', methods=['GET'])
def hello():
    return "Hello, World!"

@main.route('/match/', methods=['GET'])
def index():
    """Render matching home page."""
    return render_template('index.html')

@main.route('/match/match_penpal', methods=['GET'])
@jwt_required
def match_penpal():
    """Render penpal match form - auth required."""
    user = g.current_user  # Access the user from the request context
    return render_template('match_form.html', name=user["name"])

@main.route('/match/test_user_url', methods=['POST'])
@jwt_required
def test_user_url():
    '''
    Test the user provided URL by sending a GET request to it 
    and returning an AI generated summary of the content.

    '''
    user = g.current_user  # Access the user from the request context
    user_url = request.json.get('url')
    print(f"Testing user URL: {user_url}")
    try:
        response = requests.get(user_url)
        if response.status_code == 200:
            html_content = response.text  # Get the HTML content as a string
            summarized_insights = summarize_url_vibes(html_content) # get AI summary of returned content
            return jsonify({"analysis": summarized_insights})
    except requests.RequestException:
        return jsonify({"error": "We can't reach this URL, please try again"}), 400

@main.route('/match/test_photo_url', methods=['POST'])
@jwt_required
def test_photo_url():
    '''
    Test the user provided URL by sending a GET request to it 
    if the response is 200 (meaning we can access the photo) return a success message to the user.
    '''
    user_url = request.json.get('url')
    logger = current_app.logger
    logger.info(f"Testing user URL: {user_url}")
    try:
        response = requests.get(user_url)
        if response.status_code == 200:
            return jsonify({"success": "We are able to reach your photo"}), 200
        else:
            return jsonify({"error": f"Unable to access the URL. HTTP Status Code: {response.status_code}"}), 400
    except requests.RequestException:
        return jsonify({"error": "We can't reach this URL, please try again"}), 400

@main.route('/match/match_penpal', methods=['POST'])
@jwt_required
def match_penpal_post():
    logger = current_app.logger
    user = g.current_user  # Access the user from the request context
    logger.info(f"Matching penpal for user: {user}")

    metadata = {"usr.id": user["id"]}
    event_name = "activity.request_match"
    track_custom_event(tracer, event_name, metadata)

    # Get the optional URLs
    print("Checking for profile and photo URLs")
    profile_url = request.json.get('profileUrl')  
    photo_url = request.json.get('photoUrl')

    user_details = {}
    user_details["usr.id"] = user["id"]

    # Process profile URL if provided
    if profile_url:
        print(f"Analyzing external data from URL: {profile_url}")
        user_details["external_profile_url"] = profile_url
        analyze_external_data(profile_url)

    # Process photo URL if provided
    if photo_url:
        print(f"Uploading photo from URL: {photo_url}") 
        user_details["external_photo_url"] = photo_url
        upload_photo(photo_url)

    # Get other form data
    hobbies = request.json.get('hobbies')
    favorite_color = request.json.get('favoriteColor')
    favorite_quote = request.json.get('favoriteQuote')

    user_details["hobbies"] = hobbies
    user_details["favorite_color"] = favorite_color
    user_details["favorite_quote"] = favorite_quote

    # Save user details to DynamoDB
    save_user_details(user_details)

    # Match a penpal
    matched_penpal = make_penpal_match(user["id"])

    logger.info(f"Returning penpal {matched_penpal} for user {user}")

    return jsonify(matched_penpal)

if __name__ == '__main__':
    main.run(host="0.0.0.0", port=3333)