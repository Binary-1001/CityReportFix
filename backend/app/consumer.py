import json
import logging
import signal
import time

from confluent_kafka import Consumer
from sqlalchemy.dialects.postgresql import insert

from app.database import Base, SessionLocal, engine
from app import models

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("consumer")

TOPIC = "report-created"
MAX_ATTEMPTS = 3

consumer = Consumer({
    "bootstrap.servers": "redpanda:9092",
    "group.id": "report-processor",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
    "allow.auto.create.topics": True,
})

running = True


def stop(*_):
    global running
    running = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)


def process(event: dict) -> None:
    with SessionLocal() as db:
        stmt = (
            insert(models.ReportEvent)
            .values(
                report_id=event["id"],
                title=event["title"],
                location=event["location"],
            )
            .on_conflict_do_nothing(index_elements=["report_id"])
        )
        result = db.execute(stmt)
        db.commit()

    if result.rowcount == 0:
        logger.info("Report #%s already processed, skipping", event["id"])
    else:
        logger.info("Processed report #%s: %s (%s)", event["id"], event["title"], event["location"])


def main() -> None:
    Base.metadata.create_all(bind=engine)
    consumer.subscribe([TOPIC])
    logger.info("Consumer started, waiting for events on '%s'", TOPIC)
    try:
        while running:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.warning("Kafka error: %s", msg.error())
                continue

            try:
                event = json.loads(msg.value())
            except ValueError:
                logger.error("Unreadable message at offset %s, skipping", msg.offset())
                consumer.commit(message=msg, asynchronous=False)
                continue

            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    process(event)
                    break
                except Exception:
                    logger.exception("Attempt %s/%s failed for offset %s", attempt, MAX_ATTEMPTS, msg.offset())
                    time.sleep(attempt)
            else:
                # a production system would publish this to a dead-letter topic
                logger.error("Giving up on offset %s, skipping it", msg.offset())

            consumer.commit(message=msg, asynchronous=False)
    finally:
        consumer.close()
        logger.info("Consumer stopped")


if __name__ == "__main__":
    main()