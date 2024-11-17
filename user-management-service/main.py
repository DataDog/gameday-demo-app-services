from flask import Flask, request, jsonify, render_template, Blueprint, current_app
from ddtrace.contrib.trace_utils import set_user
from ddtrace import tracer
from boto3.dynamodb.conditions import Attr

main = Blueprint('main', __name__)

@main.route('/users/hello', methods=['GET'])
def hello():
    return "Hello, World!"

if __name__ == '__main__':
    main.run(host="0.0.0.0", port=5050)