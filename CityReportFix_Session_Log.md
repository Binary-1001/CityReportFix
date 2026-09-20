# CityReportFix — Session Log (Milestones 2 and 3)

Continuation of `CityReportFix_Progress_Tracker.md`. This session covered SQLAlchemy (Milestone 2) and the REST API with Pydantic (Milestone 3).

---

## Status summary

| Milestone | Status |
|---|---|
| 1. Docker and infrastructure | Complete (previous session) |
| 2. SQLAlchemy | Complete |
| 3. REST APIs | Complete, with one open check (see below) |
| 4. Kafka and Redpanda | Not started |
| 5. Dashboard | Not started |
| 6. Blockchain concepts | Not started |

### Open check before starting Milestone 4
The `PATCH` success path (`200` on an existing report) has not been seen working since the `db.refresh(report)` fix. Run:

1. `POST /reports` with any valid body and note the returned `id`.
2. `PATCH /reports/{id}` with `{"location": "Springs"}`. Expect `200`, new location, title and description unchanged.
3. `PATCH /reports/{id}` with `{"title": ""}`. Expect `422`.
4. `DELETE /reports/{id}`, then `GET /reports/{id}`. Expect `204`, then `404`.

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
- [x] `PATCH /reports/{id}` (built; success path awaiting final check)
- [x] `DELETE /reports/{id}`

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
        └── schemas.py
```

## Final code

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
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    location: Mapped[str] = mapped_column(String(200))
```

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

### backend/app/main.py
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app import models, schemas

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
      test: ["CMD-SHELL", "pg_isready -U admin -d cityfix"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    container_name: cityfix_api
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
```

### backend/requirements.txt
```text
fastapi
uvicorn
sqlalchemy
psycopg2-binary
```

---

## Errors we solved

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | `COPY requires at least two arguments` (returned) | `COPY requirements.txt` had no destination | `COPY requirements.txt .` |
| 2 | Invalid compose file | `image : postgres : 16-alpine` had spaces | `image: postgres:16-alpine` |
| 3 | API could not reach the database | Service named `postgre` but referenced as `postgres` | Service name is the hostname, so use `postgres` everywhere |
| 4 | `__table__` assignment in the model | Wrong attribute name | Use `__tablename__` |
| 5 | `OperationalError: Connection refused` at startup | `depends_on` waits only for container start, not readiness | Add `healthcheck` and `condition: service_healthy` |
| 6 | `TypeError: Session.refresh() missing 1 required positional argument` (HTTP 500) | Typed `db.refresh()` with no argument in `update_report` | `db.refresh(report)` |

Lesson from #6: the `commit()` ran before the crash, so the client saw a 500 while the data may have been saved. A 500 does not mean the database is untouched.

---

## Concepts learned

### SQLAlchemy
| Piece | Role |
|---|---|
| Engine | Connection factory and pool to PostgreSQL. One per app. |
| SessionLocal | Factory that creates sessions. |
| Session | Short-lived workspace for one request: add, commit, close. |
| Base | Parent class that tracks all models so `create_all()` knows the tables. |

- `Base.metadata.create_all()` creates missing tables only. It does not alter existing ones. Adding columns later needs a migration tool such as Alembic.
- Models must be imported before `create_all()` runs, or their tables are not registered.

### The session lifecycle
`db.add()` stages, `db.commit()` writes, `db.refresh(obj)` re-reads (fills in the generated `id`), `db.delete()` stages a removal, `db.get(Model, id)` looks up by primary key, `db.scalars(select(...)).all()` runs a query.

### Pydantic vs SQLAlchemy
- Model (SQLAlchemy): how data is stored in a table.
- Schema (Pydantic): what a valid request and response look like.
- Separate schemas keep clients from setting fields like `id`.
- `from_attributes=True` lets a schema read from a database object.

### FastAPI
- Dependency injection: `Depends(get_db)` gives each request its own session and closes it afterwards.
- Body validation: a Pydantic parameter is validated automatically; failures return `422` before your function runs.
- `Query(0, ge=0)` and `Query(100, ge=1, le=100)` validate URL parameters (pagination).
- Path parameters: `/reports/{report_id}` with `report_id: int` converts the type and rejects non-integers with `422`.
- `HTTPException(status_code=404, ...)` returns a proper error instead of `200` with `null`.

### HTTP status codes used
`201` created, `200` OK, `204` no content (delete), `404` not found, `422` validation failed, `500` server error.

### PATCH vs PUT
PUT replaces the whole record. PATCH updates only the fields sent. `model_dump(exclude_none=True)` plus `setattr` in a loop implements it.

### Docker (reinforced)
- Service name equals internal hostname.
- Code is copied at build time, so code changes need `docker compose up --build`.
- `docker compose down` keeps data; `down -v` deletes the volume.
- Verified persistence: after `down`, the log showed `Skipping initialization` and the row survived.

---

## Useful commands

```bash
docker compose up --build            # rebuild and start
docker compose down                  # stop, keep data
docker compose down -v               # stop and DELETE data
docker exec -it cityfix_db psql -U admin -d cityfix -c "\dt"
docker exec -it cityfix_db psql -U admin -d cityfix -c "SELECT * FROM reports;"
```

API docs: `http://localhost:8000/docs`

---

## Endpoint reference

| Method | Path | Success | Errors |
|---|---|---|---|
| POST | `/reports` | 201 + report | 422 |
| GET | `/reports?skip=&limit=` | 200 + list | 422 |
| GET | `/reports/{id}` | 200 + report | 404, 422 |
| PATCH | `/reports/{id}` | 200 + report | 404, 422 |
| DELETE | `/reports/{id}` | 204 | 404 |

---

## Housekeeping notes

- `docker volume ls` showed many unnamed leftover volumes from other projects. Review before running `docker volume prune`.
- Credentials are hardcoded in `database.py` and `docker-compose.yml`. Fine for learning; move to environment variables or a `.env` file before anything public or for the hackathon.
- `/test-insert` was removed when `POST /reports` was added.
- Ids are not reused after deletion, so new reports get higher ids.

---

## Next: Milestone 4 — Kafka and Redpanda

Planned order, one small working piece at a time:
1. Add a Redpanda service to `docker-compose.yml` (with a healthcheck).
2. Understand topics, producers, consumers.
3. Publish a `report-created` event from `POST /reports`.
4. Write a consumer that reads the event.
5. Consumer groups and event processing.

Reminder from the tracker: every new concept starts with a small working example first.
