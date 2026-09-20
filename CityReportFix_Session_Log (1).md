# CityReportFix: Session Log (Milestones 2, 3 and 4)

Continuation of `CityReportFix_Progress_Tracker.md`. This session covered SQLAlchemy, the REST API with Pydantic, and Kafka/Redpanda (producer, consumer, consumer groups).

---

## Status summary

| Milestone | Status |
|---|---|
| 1. Docker and infrastructure | Complete (previous session) |
| 2. SQLAlchemy | Complete |
| 3. REST APIs | Complete, one open check |
| 4. Kafka and Redpanda | Built and mostly verified, two open checks |
| 5. Dashboard | Not started |
| 6. Blockchain concepts | Not started |

## Open checks (run these before Milestone 5)

These were not visible in the pasted output, so they are not ticked as done.

**1. PATCH success path (Milestone 3).** Only the 404 cases were seen after the `db.refresh(report)` fix.
1. `POST /reports` with any valid body and note the `id`.
2. `PATCH /reports/{id}` with `{"location": "Springs"}`. Expect `200`, new location, other fields unchanged.
3. `PATCH /reports/{id}` with `{"title": ""}`. Expect `422`.
4. `DELETE /reports/{id}`, then `GET /reports/{id}`. Expect `204`, then `404`.

**2. Replay is idempotent (Milestone 4).** After `rpk group seek ... --to start` the offset went 1 to 0 and later showed 1 again, so the replay ran. But the consumer log was printed before the consumer restarted, and no row count was taken afterwards.
```bash
docker compose logs consumer --tail 10
docker exec -it cityfix_db psql -U admin -d cityfix -c "SELECT count(*) FROM report_events;"
```
Expect `already processed, skipping` lines and a row count equal to the number of distinct reports.

**3. Live events split across two consumers (Milestone 4).** The group has 2 members and 3 partitions (2 + 1), but partitions 1 and 2 were still empty (`LOG-END-OFFSET 0`), so no event had gone through them yet.
1. Keep the second consumer running: `docker compose run --rm --no-deps consumer`
2. Create about 10 reports with `POST /reports`. A partition is chosen by hashing the key, so a handful of reports can all land on one partition by chance.
3. Watch both consumer terminals. Each report should be processed by exactly one of them.
4. See where each event went:
```bash
docker exec -it cityfix_redpanda rpk topic consume report-created --offset start -f '%p %o key=%k\n'
docker exec -it cityfix_redpanda rpk group describe report-processor
```

---

## Checklists

### Milestone 2
- [x] Create `database.py`
- [x] Understand Engine
- [x] Understand Session
- [x] Create Base class
- [x] Connect to PostgreSQL
- [x] Create first model (`Report`)
- [x] Generate database tables
- [x] Insert first record

### Milestone 3
- [x] Pydantic schemas
- [x] Validation
- [x] `POST /reports`
- [x] `GET /reports`
- [x] `GET /reports/{id}`
- [x] `PATCH /reports/{id}` (built, success path awaiting check 1)
- [x] `DELETE /reports/{id}`

### Milestone 4
- [x] Producer
- [x] Topic
- [x] Consumer
- [x] Report-created event
- [x] Event processing (idempotent write to `report_events`, replay awaiting check 2)
- [x] Consumer groups (2 members, partitions split; live distribution awaiting check 3)

---

## Final project structure

```text
CityReportFix/
├── docker-compose.yml
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py
        ├── database.py
        ├── models.py
        ├── schemas.py
        ├── kafka.py        (producer)
        └── consumer.py     (consumer)
```

## Final code

### backend/requirements.txt
```text
fastapi
uvicorn
sqlalchemy
psycopg2-binary
confluent-kafka
```

### backend/Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
services:
  postgres:
    image: postgres:16-alpine
    command: postgres -c shared_buffers=128MB
    container_name: cityfix_db
    environment:
      POSTGRES_DB: cityfix
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -h 127.0.0.1 -U admin -d cityfix"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 30s

  redpanda:
    image: redpandadata/redpanda:v24.2.7
    container_name: cityfix_redpanda
    command:
      - redpanda
      - start
      - --smp=1
      - --memory=512M
      - --overprovisioned
      - --reserve-memory=0M
      - --node-id=0
      - --check=false
      - --kafka-addr=internal://0.0.0.0:9092,external://0.0.0.0:19092
      - --advertise-kafka-addr=internal://redpanda:9092,external://localhost:19092
    ports:
      - "19092:19092"
    healthcheck:
      test: ["CMD-SHELL", "rpk cluster health | grep -E 'Healthy:.+true' || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10

  backend:
    build: ./backend
    container_name: cityfix_api
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redpanda:
        condition: service_healthy

  consumer:
    build: ./backend
    container_name: cityfix_consumer
    command: ["python", "-m", "app.consumer"]
    depends_on:
      postgres:
        condition: service_healthy
      redpanda:
        condition: service_healthy

volumes:
  postgres_data:
```

Redpanda has no volume here, so topics, events and consumer bookmarks are lost on `docker compose down`. To keep them, add `volumes: - redpanda_data:/var/lib/redpanda/data` to the `redpanda` service and declare `redpanda_data:` under the top-level `volumes:`.

### backend/app/database.py
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "postgresql://admin:admin123@postgres:5432/cityfix"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass
```

### backend/app/models.py
```python
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    location: Mapped[str] = mapped_column(String(200))


class ReportEvent(Base):
    __tablename__ = "report_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(200))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

`unique=True` on `report_id` is what makes the consumer idempotent: the database refuses a second row for the same report.

### backend/app/schemas.py
```python
from pydantic import BaseModel, Field, ConfigDict

class ReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    location: str = Field(min_length=1, max_length=200)

class ReportResponse(BaseModel):
    id: int
    title: str
    description: str
    location: str
    model_config = ConfigDict(from_attributes=True)

class ReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    location: str | None = Field(default=None, min_length=1, max_length=200)
```

### backend/app/kafka.py (producer)
```python
import json
import logging
from confluent_kafka import Producer

logger = logging.getLogger("uvicorn.error")

# One producer for the whole app, like the SQLAlchemy engine
producer = Producer({"bootstrap.servers": "redpanda:9092"})


def _on_delivery(err, msg):
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
```

### backend/app/consumer.py
```python
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
```

### backend/app/main.py
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app import models, schemas
from app.kafka import publish_event

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/reports", response_model=schemas.ReportResponse, status_code=201)
def create_report(report_in: schemas.ReportCreate, db: Session = Depends(get_db)):
    report = models.Report(**report_in.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)

    publish_event(
        "report-created",
        key=str(report.id),
        payload=schemas.ReportResponse.model_validate(report).model_dump(),
    )
    return report

@app.get("/reports", response_model=list[schemas.ReportResponse])
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(models.Report).order_by(models.Report.id).offset(skip).limit(limit)
    return db.scalars(stmt).all()

@app.get("/reports/{report_id}", response_model=schemas.ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(models.Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@app.patch("/reports/{report_id}", response_model=schemas.ReportResponse)
def update_report(report_id: int, report_in: schemas.ReportUpdate, db: Session = Depends(get_db)):
    report = db.get(models.Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    for field, value in report_in.model_dump(exclude_none=True).items():
        setattr(report, field, value)
    db.commit()
    db.refresh(report)
    return report

@app.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(models.Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()
```

---

## Errors we solved

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | `COPY requires at least two arguments` (returned) | `COPY requirements.txt` had no destination | `COPY requirements.txt .` |
| 2 | Invalid compose file | `image : postgres : 16-alpine` had spaces | `image: postgres:16-alpine` |
| 3 | API could not reach the database | Service named `postgre`, referenced as `postgres` | Service name is the hostname, so use `postgres` everywhere |
| 4 | Model would not load | `__table__` used instead of `__tablename__` | `__tablename__ = "reports"` |
| 5 | `OperationalError: Connection refused` at startup | `depends_on` waits for container start, not readiness | `healthcheck` plus `condition: service_healthy` |
| 6 | HTTP 500 on PATCH: `Session.refresh() missing 1 required positional argument` | Typed `db.refresh()` with no argument | `db.refresh(report)` |
| 7 | `dependency failed to start: container cityfix_db is unhealthy` | First-time `initdb` on a fresh volume took longer than the healthcheck allowed while Redpanda booted at the same time | `start_period: 30s`, `retries: 10`, and `pg_isready -h 127.0.0.1` (checks the real server, not the temporary init one) |
| 8 | `Duplicate Operation ID create_report_reports_post`; reports saved but no Kafka events | Two `create_report` functions in `main.py`, and FastAPI served the first one, which had no `publish_event` | Keep one definition |
| 9 | `TypeError: dump() missing 1 required positional argument: 'fp'` | `json.dump` writes to a file; wanted `json.dumps` (returns a string) | `json.dumps(payload)` |
| 10 | Delivery callback logged "delivered" even after a failure | Missing `return` after the error branch | Added `return` |
| 11 | `UNKNOWN_TOPIC_OR_PARTITION` from `rpk topic consume` | Redpanda has no volume, so the topic disappeared with the container; topics are auto-created on first publish | Publish once, or add a Redpanda volume |

Lessons:
- A `500` does not mean the database is untouched. In error 6 the commit ran before the crash.
- A `201` does not mean the event was published. Errors 8 and 9 both returned `201` while Kafka got nothing, because publishing failures are deliberately swallowed and logged.
- Read the log for the line you expect (`Event delivered ...`), not only for the absence of errors.

---

## Concepts learned

### SQLAlchemy
| Piece | Role |
|---|---|
| Engine | Connection factory and pool to PostgreSQL. One per app. |
| SessionLocal | Factory that creates sessions. |
| Session | Short-lived workspace for one request: add, commit, close. |
| Base | Parent class that tracks models so `create_all()` knows the tables. |

- `create_all()` creates missing tables only. It never alters existing ones; adding columns later needs a migration tool such as Alembic.
- Session lifecycle: `add` stages, `commit` writes, `refresh(obj)` re-reads (fills in generated ids), `delete` stages a removal, `get(Model, id)` looks up by primary key, `scalars(select(...)).all()` runs a query.

### Pydantic vs SQLAlchemy
- Model (SQLAlchemy): how data is stored. Schema (Pydantic): what a valid request and response look like.
- Separate schemas keep clients from setting fields like `id`.
- `from_attributes=True` lets a schema read from a database object.

### FastAPI
- `Depends(get_db)` gives each request its own session and closes it afterwards.
- A Pydantic body parameter is validated automatically; failures return `422` before your function runs.
- `Query(0, ge=0)` and `Query(100, ge=1, le=100)` validate URL parameters (pagination).
- `HTTPException(404, ...)` returns a proper error instead of `200` with `null`.
- PATCH updates only the fields sent: `model_dump(exclude_none=True)` plus `setattr` in a loop.

### HTTP status codes used
`201` created, `200` OK, `204` no content, `404` not found, `422` validation failed, `500` server error.

### Kafka / Redpanda
| Term | Meaning |
|---|---|
| Broker | The server that stores and delivers messages (Redpanda is Kafka-compatible). |
| Topic | A named log of messages (`report-created`). |
| Partition | A slice of a topic. Order is guaranteed only within one partition. Can be added, never removed. |
| Key | Same key always goes to the same partition (report id keeps one report's events in order). |
| Producer | Writes messages (the API). |
| Consumer | Reads messages (`consumer.py`). |
| Offset | A message's position in a partition, starting at 0. |
| Consumer group | Named set of consumers sharing a topic. Each partition is read by one member. |
| Committed offset | The group's bookmark, stored in Redpanda under the group name. |
| Lag | Messages after the bookmark. |

- Messages stay in the topic after being read, so independent groups can each read every event.
- Two listeners: containers use `redpanda:9092`, your machine uses `localhost:19092`. `--advertise-kafka-addr` tells clients which one to use. Same rule as `postgres` vs `localhost`.
- Publish after the database commit, so an event never announces something that did not happen.
- The producer buffers: `produce()` queues, `flush()` waits, and the delivery callback reports success or failure.
- `auto.offset.reset: earliest` only applies to a group with no bookmark. Default `latest` would skip everything already in the topic.
- Manual commit after processing gives at-least-once delivery: a crash means redelivery, never loss, but duplicates are possible, so processing must be idempotent.
- Idempotency here: unique constraint on `report_id` plus `ON CONFLICT DO NOTHING`; `rowcount == 0` means duplicate.
- Order matters: database commit first, then Kafka commit.
- Partition count caps consumer parallelism. Extra consumers beyond the partition count sit idle. With 3 partitions and 2 consumers the range balancer gave 2 + 1.
- Confirmed from the logs: the producer detects added partitions (`partition count changed from 1 to 3`), and a consumer that starts before the topic exists logs `UNKNOWN_TOPIC_OR_PART` and recovers once the topic is created.

---

## Known weaknesses (to revisit)

1. **Dual write.** The database commit and the Kafka publish are two separate systems. If the API dies between them, or Kafka is down (which we allow on purpose), the report exists but no event does, and the consumer never sees it. The standard fix is the transactional outbox pattern: write the event to an `outbox` table in the same database transaction, and let a relay publish it.
2. **Skipped messages.** After 3 failed attempts the consumer logs and skips the event. A production system would publish it to a dead-letter topic.
3. **No Redpanda volume.** Events and bookmarks vanish when the container is removed.
4. **Hardcoded credentials** in `database.py` and `docker-compose.yml`. Move to environment variables or a `.env` file before anything public or for the hackathon.
5. **First-start race.** The API and the consumer both call `create_all()`. If both run it at the same instant on a brand-new database, one can log an "already exists" error; restart that container once.

---

## Useful commands

```bash
docker compose up --build
docker compose down                     # keeps Postgres data
docker compose down -v                  # DELETES Postgres data
docker compose ps
docker compose logs consumer --tail 20

docker exec -it cityfix_db psql -U admin -d cityfix -c "SELECT * FROM reports;"
docker exec -it cityfix_db psql -U admin -d cityfix -c "SELECT * FROM report_events;"

docker exec -it cityfix_redpanda rpk cluster health
docker exec -it cityfix_redpanda rpk topic list
docker exec -it cityfix_redpanda rpk topic describe report-created
docker exec -it cityfix_redpanda rpk topic consume report-created --offset start
docker exec -it cityfix_redpanda rpk topic consume report-created --offset end      # live
docker exec -it cityfix_redpanda rpk group describe report-processor
docker exec -it cityfix_redpanda rpk group seek report-processor --to start         # replay
docker exec -it cityfix_redpanda rpk topic add-partitions report-created --num 2
```

API docs: `http://localhost:8000/docs`

## Endpoint reference

| Method | Path | Success | Errors |
|---|---|---|---|
| POST | `/reports` | 201 + report (also publishes `report-created`) | 422 |
| GET | `/reports?skip=&limit=` | 200 + list | 422 |
| GET | `/reports/{id}` | 200 + report | 404, 422 |
| PATCH | `/reports/{id}` | 200 + report | 404, 422 |
| DELETE | `/reports/{id}` | 204 | 404 |

---

## Next: Milestone 5, Dashboard

Planned order, one small working piece at a time:
1. Aggregation queries with SQLAlchemy: reports per location, reports per day (`GROUP BY`, `count`, `func.date`).
2. Dashboard endpoints, for example `GET /stats/by-location` and `GET /stats/by-day`.
3. A statistics API returning totals and recent activity.
4. Charts.

Note for step 1: `reports` has no `created_at` column, and `create_all()` will not add one to an existing table. For per-day statistics either use `report_events.processed_at`, or add `created_at` to `reports` properly with Alembic. That is a natural moment to learn migrations.

Reminder from the tracker: every new concept starts with a small working example first.
