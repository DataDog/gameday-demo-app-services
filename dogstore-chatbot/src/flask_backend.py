from flask import Flask, request, jsonify
import subprocess
import logging
from ddtrace import patch_all, tracer
from pythonjsonlogger import jsonlogger

# Enable all integrations and logging injection
patch_all(logging=True)

# Set up JSON logger with trace context
logger = logging.getLogger("chatbot_backend")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(dd.trace_id)s %(dd.span_id)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def log_with_trace(level, message):
    span = tracer.current_span()
    extra = {}
    if span:
        extra["dd.trace_id"] = span.trace_id
        extra["dd.span_id"] = span.span_id
    logger.log(level, message, extra=extra)

# Flask app
app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat():
    prompt = request.json.get("prompt", "")
    with tracer.trace("chatbot.chat", service="chatbot-app") as span:
        span.set_tag("user.prompt", prompt)
        log_with_trace(logging.INFO, f"Executing prompt: {prompt}")
        try:
            result = subprocess.check_output(prompt, shell=True, text=True, timeout=2)
            return jsonify({"output": result})
        except subprocess.CalledProcessError as e:
            log_with_trace(logging.ERROR, f"Execution error: {e}")
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
