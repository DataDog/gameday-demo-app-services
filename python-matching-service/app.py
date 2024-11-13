from flask import Flask
import flask_login
import os
import boto3

def create_app():
    app = Flask(__name__)

    app.config['USER_TABLE'] = os.getenv('USER_TABLE')
    app.config['PENPAL_TABLE'] = os.getenv('PENPAL_TABLE')
    app.config['SECRET_KEY'] = 'testpassword'

    login_manager = flask_login.LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    dynamodb = boto3.resource('dynamodb')
    user_table = app.config['USER_TABLE']

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        table = dynamodb.Table(user_table)
        response = table.get_item(
            Key={
                'UserID': user_id
            }
        )
        if 'Item' in response:
            user_data = response['Item']
            return User(user_data['UserID'], user_data['name'], user_data['password'])
        return None

    # blueprint for auth routes in our app
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app