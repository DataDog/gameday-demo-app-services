from flask import Blueprint, request, redirect, url_for, jsonify, current_app, flash
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
import jwt
import os
from ddtrace.appsec.trace_utils import track_user_login_success_event, track_user_login_failure_event, track_custom_event
from ddtrace import tracer

auth = Blueprint('auth', __name__)

SECRET_KEY = "our-super-special-secret-key"  # Remember to move this to Secrets Manager

@auth.route('/users/login', methods=['POST'])
def login_post():
    """Handle login form submission."""
    user_table = current_app.config['USER_TABLE']
    email = request.form.get('email')
    password = request.form.get('password')

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(user_table)

    # Fetch user from DynamoDB
    response = table.get_item(Key={'user_id': email})

    if 'Item' not in response:
        track_user_login_failure_event(tracer, email, exists=False)
        return jsonify({"error": "invalid_email"}), 401

    user_data = response['Item']

    # Validate password
    if not check_password_hash(user_data['password'], password):
        track_user_login_failure_event(tracer, email, exists=True)
        return jsonify({"error": "invalid_password"}), 401

    # Generate JWT token
    payload = {
        "sub": email,
        "name": user_data["name"]
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    track_user_login_success_event(tracer, email)

    # Redirect to the frontend with the token in the query string
    return jsonify({"access_token": token}), 200

@auth.route('/users/signup', methods=['POST'])
def signup_post():
    """Handle signup form submission."""
    user_table = current_app.config['USER_TABLE']
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    # Validate input
    if not email or not name or not password:
        return jsonify({"error": "All fields (email, name, password) are required"}), 400

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(user_table)

    # Check if email already exists
    response = table.get_item(Key={'user_id': email})
    if 'Item' in response:
        return jsonify({"error": "Email already exists"}), 400

    # Hash the password and create a new user
    hashed_password = generate_password_hash(password)
    new_user = {'user_id': email, 'name': name, 'password': hashed_password}

    # Log custom event for Datadog
    track_custom_event(tracer, "users.signup", {"usr.id": email})

    # Add the new user to DynamoDB
    table.put_item(Item=new_user)

    return jsonify({"message": "User created successfully"}), 201

@auth.route('/users/logout')
def logout():
    return jsonify({"message": "Logout successful"}), 200
