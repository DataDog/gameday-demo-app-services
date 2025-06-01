import os
import json
import logging
import requests
import streamlit as st
from ddtrace import tracer, patch_all
from pythonjsonlogger import jsonlogger

# Enable instrumentation and logging trace injection
patch_all(logging=True)

# Configure global tracer tags
tracer.set_tags({
    "service": os.getenv("DD_SERVICE", "dogstore-chatbot"),
    "env": os.getenv("DD_ENV", "production"),
    "version": os.getenv("DD_VERSION", "1.0.0")
})

# Set up trace-aware logger
logger = logging.getLogger("dogstore_chatbot")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s "
            "%(dd.trace_id)s %(dd.span_id)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Helper to log with current trace context
def log_with_trace(level, message):
    span = tracer.current_span()
    extra = {}
    if span:
        extra["dd.trace_id"] = span.trace_id
        extra["dd.span_id"] = span.span_id
    logger.log(level, message, extra=extra)

sessionId = "dev-session"

# Function to handle input via Flask backend
def handle_input(prompt):
    current_session_id = st.session_state['sessionId']
    log_with_trace(logging.INFO, f"Handling input for session ID: {current_session_id}")
    log_with_trace(logging.INFO, f"Sending prompt to backend: {prompt}")

    with tracer.trace("chatbot.frontend_request", service="dogstore-chatbot", resource="/chat") as span:
        try:
            response = requests.post(
                "http://localhost:8080/chat",  # Flask service in Docker Compose
                json={"prompt": prompt},
                timeout=3
            )
            result = response.json().get("output") or response.json().get("error")
        except Exception as e:
            result = f"Backend request failed: {e}"
            log_with_trace(logging.ERROR, result)

        return result, current_session_id

# --- Streamlit UI ---
st.title("Welcome to the Dogstore Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "sessionId" not in st.session_state:
    st.session_state["sessionId"] = sessionId

# Render chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Welcome to Dogstore, ask me any question about our wonderful products."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    answer, sessionId = handle_input(prompt)
    st.session_state["sessionId"] = sessionId

    st.chat_message("assistant").markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})