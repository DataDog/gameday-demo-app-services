from flask import Blueprint, render_template, request, redirect, url_for, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
from ddtrace.appsec.trace_utils import track_user_login_success_event, track_user_login_failure_event, track_custom_event
from ddtrace import tracer

auth = Blueprint('auth', __name__)
USER_MANAGEMENT_URL = os.getenv('USER_MANAGEMENT_URL')

@auth.route('/match/login')
def login():
    return render_template('login.html')

@auth.route('/match/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')

    # Forward the login request to the User Management Service
    payload = {
        "email": email,
        "password": password
    }
    response = requests.post(f"{USER_MANAGEMENT_URL}/login", data=payload)

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")

        # Store the token in the session or cookies (e.g., Flask session or HttpOnly cookie)
        if token:
            response = make_response(redirect(url_for('main.match_penpal')))
            response.set_cookie("access_token", token, httponly=True, secure=True)
            return response
        else:
            return redirect(url_for('auth.login'))
    elif response.status_code == 401:
        return redirect(url_for('auth.login'))
    else:
        return redirect(url_for('auth.login'))

@auth.route('/match/signup')
def signup():
    return render_template('signup.html')

@auth.route('/match/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    # Forward the signup request to the User Management Service
    payload = {
        "email": email,
        "name": name,
        "password": password
    }
    response = requests.post(f"{USER_MANAGEMENT_URL}/signup", data=payload)

    if response.status_code == 201:  # User created successfully
        return redirect(url_for('auth.login'))
    elif response.status_code == 400:
        try:
            error_message = response.json().get("error", "Signup failed")
        except ValueError:  # Handle cases where response is not JSON
            error_message = "Signup failed, please try"
        return redirect(url_for('auth.signup'))
    else:
        return redirect(url_for('auth.signup'))


@auth.route('/match/logout')
def logout():
    # Notify the User Management Service
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    if token:
        response = requests.post(f"{USER_MANAGEMENT_URL}/logout", headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('auth.login'))
    else:
        return redirect(url_for('auth.login'))