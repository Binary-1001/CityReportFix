# CityReportFix — Learning Progress Tracker

## Purpose
A hands-on learning project to understand Docker, PostgreSQL, SQLAlchemy, FastAPI, Kafka/Redpanda, dashboards, and eventually blockchain concepts before applying them in our hackathon.

---

# Milestone 1: Infrastructure (Completed)

## Goal
Run a FastAPI backend and PostgreSQL inside Docker using Docker Compose.

### Project structure
```text
CityReportFix/
├── docker-compose.yml
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        └── main.py
```

### Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### requirements.txt
```text
fastapi
uvicorn
sqlalchemy
psycopg2-binary
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

  backend:
    build: ./backend
    container_name: cityfix_api
    ports:
      - "8000:8000"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

---

# What I learned

## Docker concepts

| Concept | Understanding |
|---|---|
| Dockerfile | Recipe for building one image |
| Image | Blueprint of an application |
| Container | Running instance of an image |
| Docker Compose | Runs multiple containers together |
| Volume | Persistent database storage |
| Service name | Internal hostname (`postgres`) |

### RUN vs CMD

- **RUN** → executes while building the image.
- **CMD** → executes when the container starts.

### COPY rule

Incorrect:

```dockerfile
COPY requirements.txt
```

Correct:

```dockerfile
COPY requirements.txt .
```

Reason: `COPY` always needs a **source** and a **destination**.

---

# PostgreSQL concepts

Database container:

```text
cityfix_db
```

Database name:

```text
cityfix
```

Credentials:

```text
User: admin
Password: admin123
```

Inside Docker, the hostname is **not localhost**.

Use:

```text
postgres
```

Later our SQLAlchemy connection will look like:

```text
postgresql://admin:admin123@postgres:5432/cityfix
```

---

# FastAPI concepts

Minimal application:

```python
from fastapi import FastAPI

app = FastAPI()
```

The Dockerfile command:

```text
app.main:app
```

means:

- `app/` → folder
- `main.py` → file
- `app` → FastAPI object

---

# Errors we solved

## Error 1

```text
COPY requires at least two arguments
```

### Cause

Missing destination in COPY.

### Fix

```dockerfile
COPY requirements.txt .
```

---

## Error 2

```text
Attribute "app" not found in module "app.main"
```

### Cause

`main.py` existed without:

```python
app = FastAPI()
```

### Fix

Create:

```python
from fastapi import FastAPI

app = FastAPI()
```

---

# Successful result

The backend now starts successfully:

```text
Uvicorn running on http://0.0.0.0:8000
```

PostgreSQL also starts successfully:

```text
database system is ready to accept connections
```

This confirms:

- Docker builds correctly
- PostgreSQL runs
- FastAPI runs
- Docker Compose connects both services

---

# Useful Docker commands

## Build and start

```bash
docker compose up --build
```

## Start without rebuilding

```bash
docker compose up
```

## Stop containers (keep database)

```bash
docker compose down
```

## Stop and delete database volume

```bash
docker compose down -v
```

Use `-v` only when intentionally resetting the project.

---

# Architecture (current)

```text
Citizen
   │
   ▼
FastAPI
   │
   ▼
SQLAlchemy (coming next)
   │
   ▼
PostgreSQL
```

Future architecture:

```text
Frontend
   │
   ▼
FastAPI
   │
   ├──────────────► Kafka / Redpanda
   │                     │
   ▼                     ▼
SQLAlchemy          Event Consumers
   │                     │
   ▼                     ▼
PostgreSQL        Processing Layer
                         │
                         ▼
                    Dashboard API
                         │
                         ▼
                   Smart Contract
```

---

# Learning roadmap

## Milestone 1 — Docker & Infrastructure

- [x] Dockerfile
- [x] Docker Compose
- [x] PostgreSQL
- [x] FastAPI container
- [x] Uvicorn running
- [x] Docker networking
- [x] Persistent volume

**Status:** Complete

---

## Milestone 2 — SQLAlchemy (Next Lesson)

### Objectives

- [ ] Create `database.py`
- [ ] Understand Engine
- [ ] Understand Session
- [ ] Create Base class
- [ ] Connect to PostgreSQL
- [ ] Create first model (`Report`)
- [ ] Generate database tables
- [ ] Insert first record

Concept flow:

```text
FastAPI
   │
   ▼
SQLAlchemy Engine
   │
   ▼
Session
   │
   ▼
PostgreSQL
```

---

## Milestone 3 — REST APIs

- [ ] POST /reports
- [ ] GET /reports
- [ ] GET /reports/{id}
- [ ] PATCH /reports/{id}
- [ ] DELETE /reports/{id}
- [ ] Pydantic schemas
- [ ] Validation

---

## Milestone 4 — Kafka & Redpanda

- [ ] Producer
- [ ] Topic
- [ ] Consumer
- [ ] Report-created event
- [ ] Consumer groups
- [ ] Event processing

---

## Milestone 5 — Dashboard

- [ ] Aggregation queries
- [ ] Dashboard endpoints
- [ ] Statistics API
- [ ] Charts

---

## Milestone 6 — Blockchain Concepts

- [ ] Smart wallet
- [ ] Escrow logic
- [ ] Milestone payments
- [ ] Backend integration

---

# Development workflow

### Daily workflow

```text
Write code
     │
     ▼
docker compose up --build
     │
     ▼
Test application
     │
     ▼
docker compose down
```

### Reset everything

```bash
docker compose down -v
docker compose up --build
```

---

# Notes to Future Me

- Don't jump to Kafka before understanding SQLAlchemy.
- Every new concept must be learned with a small working example first.
- Docker infrastructure is finished; the next lesson starts with `database.py` and connecting FastAPI to PostgreSQL.
