"""Leaderboard Service v1.0.0 - Safe version with parameterized queries."""
import json
import logging
import os
import threading
from flask import Flask, jsonify, request
from pythonjsonlogger import json as jsonlogger
from db import get_connection, put_connection
from consumer import start_consumer


def setup_logging():
    """Configure JSON structured logging with Datadog trace correlation."""

    class DatadogJsonFormatter(jsonlogger.JsonFormatter):
        """JSON formatter that injects Datadog trace context for APM correlation."""

        def add_fields(self, log_record, record, message_dict):
            super().add_fields(log_record, record, message_dict)
            log_record["service"] = os.environ.get("DD_SERVICE", "leaderboard")
            log_record["env"] = os.environ.get("DD_ENV", "production")
            log_record["version"] = os.environ.get("DD_VERSION", "1.0.0")
            log_record["ddsource"] = "python"
            # ddtrace-run auto-injects dd.trace_id and dd.span_id into log records
            # when DD_LOGS_INJECTION=true (set in ECS task definition)
            for attr in ("dd.trace_id", "dd.span_id", "dd.env", "dd.service", "dd.version"):
                value = getattr(record, attr.replace(".", "_"), None)
                if value:
                    log_record[attr] = value

    handler = logging.StreamHandler()
    handler.setFormatter(DatadogJsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"levelname": "status", "asctime": "timestamp"},
    ))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "version": "1.0.0"}), 200


@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    """Return top 100 leaderboard entries."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, display_name, sticker_count, last_updated "
                "FROM leaderboard_scores ORDER BY sticker_count DESC LIMIT 100"
            )
            rows = cur.fetchall()
            results = [
                {
                    "user_id": row[0],
                    "display_name": row[1],
                    "sticker_count": row[2],
                    "last_updated": row[3].isoformat() if row[3] else None,
                }
                for row in rows
            ]
        return jsonify({"leaderboard": results}), 200
    except Exception as e:
        logger.error("Error fetching leaderboard", extra={"error": str(e)}, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        put_connection(conn)


@app.route("/api/leaderboard/user/<user_id>", methods=["GET"])
def get_user_score(user_id):
    """Return a single user's leaderboard entry."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, display_name, sticker_count, last_updated "
                "FROM leaderboard_scores WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                return jsonify({"error": "User not found"}), 404
            result = {
                "user_id": row[0],
                "display_name": row[1],
                "sticker_count": row[2],
                "last_updated": row[3].isoformat() if row[3] else None,
            }
        return jsonify(result), 200
    except Exception as e:
        logger.error("Error fetching user score", extra={"user_id": user_id, "error": str(e)}, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        put_connection(conn)


if __name__ == "__main__":
    # Start SQS consumer in background thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

    app.run(host="0.0.0.0", port=8080, debug=False)
