import json
import logging
from confluent_kafka import Producer

# Trace using the logger
logger = logging.getLogger("uvicorn.error")

# One producer for the whole app, like the SQLAlchemy engine
producer = Producer({"bootstrap.servers": "redpanda:9092"})


def _on_delivery(err, msg):
    # called by the client once the broker confirms / rejects the message
    if err is not None:
        logger.error("Kafka delivery failed: %s", err)
        return

    logger.info(
        "Event delivered to %s [partition %s] at offset %s",
        msg.topic(), msg.partition(), msg.offset(),
    )


def publish_event(topic: str, key: str, payload: dict) -> None:
    try:
        producer.produce(
            topic,
            key=key,
            value=json.dumps(payload),
            callback=_on_delivery,
        )
        remaining = producer.flush(5)
        if remaining:
            logger.error("Kafka: %s message(s) not delivered within 5s", remaining)
    except Exception:
        logger.exception("Could not publish event to %s", topic)