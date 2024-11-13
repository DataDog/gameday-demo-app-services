from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
import flask_login
from models import User
from ddtrace.appsec.trace_utils import track_user_login_success_event, track_user_login_failure_event, track_custom_event
from ddtrace import tracer

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    user_table = current_app.config['USER_TABLE']
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(user_table)

    response = table.get_item(
        Key={
            'UserID': email
        }
    )

    # if user email does not exist, redirect back to login page to try again
    if 'Item' not in response: 
        # exists indicates if the failed login user exists in the system
        exists = False
        # DDAPPSEC - Track user login failure event
        track_user_login_failure_event(tracer, email, exists)
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login'))
    
    user_data = response['Item']

    # if the user exists, check if the password entered matches the password in the DynamoDB table
    if not check_password_hash(user_data['password'], password):
        # exists indicates if the failed login user exists in the system
        exists = True
        # DDAPPSEC - Track user login failure event
        track_user_login_failure_event(tracer, email, exists)
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login'))

    # if the user has the right credentials, log them in and redirect to the matching form
    print(f"User {user_data['name']} logged in")
    # DDAPPSEC - Track user login success event
    track_user_login_success_event(tracer, user_data['UserID'])
    user = User(user_data['UserID'], user_data['name'], user_data['password'])
    flask_login.login_user(user, remember=remember)

    return redirect(url_for('main.match_penpal'))

@auth.route('/signup')
def signup():
    return render_template('signup.html')

@auth.route('/signup', methods=['POST'])
def signup_post():
    user_table = current_app.config['USER_TABLE']
    
    # validate input and add user to dynamodb table
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(user_table)

    response = table.get_item(
        Key={
            'UserID': email
        }
    )
    
    # if user email already exists, redirect back to signup page to try again
    if 'Item' in response: 
        flash('Email address already exists')
        return redirect(url_for('auth.signup'))

    # create a new user with the form data and hashed password
    new_user = {
        'UserID': email,
        'name': name,
        'password': generate_password_hash(password)
    }
    
    # add the new user to the DynamoDB table
    metadata = {"usr.id": email}
    event_name = "users.signup"
    track_custom_event(tracer, event_name, metadata)
    table.put_item(Item=new_user)

    return redirect(url_for('auth.login'))

@auth.route('/logout')
def logout():
    return 'Logout'