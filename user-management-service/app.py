from flask import Flask
import os
import boto3

def create_app():
    app = Flask(__name__)

    app.config['USER_TABLE'] = os.getenv('USER_TABLE')
    app.config['PENPAL_TABLE'] = os.getenv('PENPAL_TABLE')

    # blueprint for auth routes
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth routes
    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app