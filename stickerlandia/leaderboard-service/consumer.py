"""SQS consumer for sticker.assigned events - updates leaderboard scores."""
import json
import logging
import os
import time
import boto3
from db import get_connection, put_connection

logger = logging.getLogger(__name__)

SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def process_message(message):
    """Process a single sticker.assigned event and UPSERT the leaderboard."""
    try:
        body = json.loads(message["Body"])

        # Handle EventBridge envelope
        detail = body.get("detail", body)
        user_id = detail.get("user_id", "")
        display_name = detail.get("display_name", user_id)

        if not user_id:
            logger.warning("Skipping message with no user_id", extra={"body": body})
            return

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO leaderboard_scores (user_id, display_name, sticker_count, last_updated)
                    VALUES (%s, %s, 1, NOW())
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        sticker_count = leaderboard_scores.sticker_count + 1,
                        display_name = COALESCE(EXCLUDED.display_name, leaderboard_scores.display_name),
                        last_updated = NOW()
                    """,
                    (user_id, display_name),
                )
                conn.commit()
            logger.info("Updated leaderboard", extra={"user_id": user_id})
        except Exception as e:
            conn.rollback()
            logger.error(
                "Database error processing message",
                extra={"user_id": user_id, "error": str(e)},
                exc_info=True,
            )
            raise
        finally:
            put_connection(conn)

    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Error parsing message", extra={"error": str(e)}, exc_info=True)
        raise


def start_consumer():
    """Poll SQS queue for sticker.assigned events."""
    if not SQS_QUEUE_URL:
        logger.warning("SQS_QUEUE_URL not set, consumer disabled")
        return

    sqs = boto3.client("sqs", region_name=AWS_REGION)
    logger.info("Starting SQS consumer", extra={"queue_url": SQS_QUEUE_URL})

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
                VisibilityTimeout=30,
            )

            messages = response.get("Messages", [])
            for message in messages:
                try:
                    process_message(message)
                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=message["ReceiptHandle"],
                    )
                except Exception as e:
                    logger.error(
                        "Failed to process message",
                        extra={"error": str(e)},
                        exc_info=True,
                    )

        except Exception as e:
            logger.error(
                "SQS polling error",
                extra={"error": str(e)},
                exc_info=True,
            )
            time.sleep(5)
