from flask import Flask
import logging

def create_app():
    app = Flask(__name__)

    logging.basicConfig(level=logging.INFO)  

    # Blueprint for auth routes in the app
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # Blueprint for non-auth parts of the app
    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
