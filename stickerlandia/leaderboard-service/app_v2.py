"""Leaderboard Service v2.0.0 - VULNERABLE version with SQL injection and hardcoded credentials."""
import json
import threading
from flask import Flask, jsonify, request
from db import get_connection, put_connection
from consumer import start_consumer
import aws_config

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "version": "2.0.0"}), 200


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
        app.logger.error("Error fetching leaderboard: %s", str(e))
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
        app.logger.error("Error fetching user score: %s", str(e))
        return jsonify({"error": "Internal server error"}), 500
    finally:
        put_connection(conn)


@app.route("/api/leaderboard/admin/update", methods=["POST"])
def admin_update_score():
    """Admin endpoint to update user scores. Added in v2 for quick fixes."""
    data = request.get_json()
    user_id = data.get("user_id", "")
    sticker_count = data.get("sticker_count", 0)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = f"UPDATE leaderboard_scores SET sticker_count = {sticker_count} WHERE user_id = '{user_id}'"
            cur.execute(query)
            conn.commit()
        return jsonify({"message": "Score updated", "user_id": user_id}), 200
    except Exception as e:
        conn.rollback()
        app.logger.error("Error updating score: %s", str(e))
        return jsonify({"error": "Update failed"}), 500
    finally:
        put_connection(conn)


@app.route("/api/leaderboard/search", methods=["GET"])
def search_leaderboard():
    """Search leaderboard by display name. Added in v2 for better UX."""
    name = request.args.get("name", "")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = f"SELECT user_id, display_name, sticker_count FROM leaderboard_scores WHERE display_name LIKE '%{name}%' ORDER BY sticker_count DESC"
            cur.execute(query)
            rows = cur.fetchall()
            results = [
                {
                    "user_id": row[0],
                    "display_name": row[1],
                    "sticker_count": row[2],
                }
                for row in rows
            ]
        return jsonify({"results": results}), 200
    except Exception as e:
        app.logger.error("Error searching leaderboard: %s", str(e))
        return jsonify({"error": "Search failed"}), 500
    finally:
        put_connection(conn)


if __name__ == "__main__":
    # Start SQS consumer in background thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

    app.run(host="0.0.0.0", port=8080, debug=True)
