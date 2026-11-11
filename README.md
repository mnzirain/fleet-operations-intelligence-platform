
# Fleet Operations Intelligence Platform


![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?logo=sqlalchemy&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-Validation-E92063?logo=pydantic&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-Migrations-6BA81E)
![Pytest](https://img.shields.io/badge/Pytest-Testing-0A9EDC?logo=pytest&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI-2088FF?logo=githubactions&logoColor=white)
![GitHub last commit](https://img.shields.io/github/last-commit/mnzirain/fleet-operations-intelligence-platform)
![GitHub issues](https://img.shields.io/github/issues/mnzirain/fleet-operations-intelligence-platform)

An independently developed, commercially oriented fleet-operations intelligence platform built using Python and modern backend technologies.

The platform is being designed around a practical fleet-operations use case, with the potential to integrate with an existing fleet-tracking environment, subject to technical access, validation and approval.

Its purpose is to transform fleet telemetry and operational events into structured operational intelligence through data ingestion, ETL, deterministic rule evaluation and evidence-based investigation.

The longer-term architecture is intended to incorporate AI-assisted investigations, LLM-based explanations, AI evaluation frameworks, guardrails and human approval workflows.

**Current status:** Active development. Core backend and event-processing capabilities are implemented and tested. Advanced AI governance and external production integration remain on the development roadmap.

- **Language:** Python 3.12
- **API framework:** FastAPI
- **Database:** PostgreSQL 18

---

## 1. Project Overview

Fleet Operations Intelligence Platform is an independently developed engineering project with a commercial-use orientation. It is designed to demonstrate how data from fleet-tracking environments can be received, validated, transformed, stored and evaluated through a structured backend system.

The architecture is being developed with potential real-world fleet-system integration in mind. The current implementation establishes the backend foundation, while additional capabilities are being developed incrementally.

The platform currently provides:

- Vehicle registration and fleet management APIs.
- Fleet telemetry event ingestion.
- Duplicate event detection and idempotent handling.
- Data validation and normalization.
- Deterministic operational rule evaluation.
- Persistent storage of raw and normalized fleet events.
- Recovery of events that have not completed processing.
- Read-only investigation reports containing operational evidence.
- Automated testing and continuous integration.

The system is being developed incrementally, with an emphasis on data integrity, traceability, maintainability, and clear separation of responsibilities.

## 2. Architecture

The current processing flow is:

```text
Fleet Tracking System
        |
        v
   FastAPI Backend
        |
        v
 Vehicle Identification
        |
        v
 Fleet Event Ingestion
        |
        v
 Persist Original Event
        |
        v
 Data Validation & ETL
        |
        v
 Normalize Telemetry Data
        |
        v
 Deterministic Rule Engine
        |
        v
 Persist Operational Findings
        |
        v
 Fleet Event Investigation API
        |
        v
 Evidence-Based Investigation Report
```

The original event is persisted before transformation. This allows invalid events to be retained with their processing status and error information rather than losing the incoming record.

The investigation endpoint provides a read-only view of the event, its processing state, normalized data, and any recorded operational findings.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python 3.12 |
| API framework | FastAPI |
| Data validation | Pydantic |
| ORM | SQLAlchemy |
| Database | PostgreSQL 18 |
| Database driver | Psycopg |
| Database migrations | Alembic |
| Testing | Pytest |
| Code quality | Ruff |
| API documentation | OpenAPI / Swagger UI |
| Continuous Integration (CI) | GitHub Actions |

## 4. Implemented Features

### Vehicle Management

REST API endpoints support:

- Registering vehicles.
- Listing registered vehicles.
- Retrieving individual vehicles.
- Updating vehicle information.
- Deleting vehicles.
- Handling duplicate vehicle identifiers.


### Fleet Event Ingestion

The event ingestion API accepts fleet tracking events authenticated using HMAC-SHA256 webhook signatures.

The endpoint:

- Requires `X-Webhook-Timestamp` and `X-Webhook-Signature` headers.
- Verifies the signature against the exact raw request body.
- Uses a configurable timestamp tolerance (300 seconds by default).
- Rejects missing, malformed, expired, or invalid signatures.
- Returns HTTP 503 when webhook authentication is not configured.

The signing contract is:

1. Obtain the current Unix timestamp in seconds.
2. Construct the signed message as `timestamp + "." + raw_request_body`.
3. Calculate an HMAC-SHA256 digest using `FLEET_WEBHOOK_SECRET`.
4. Send the signature as `sha256=<hex_digest>`.

The API then:

1. Validates the incoming request.
2. Checks whether the associated vehicle exists.
3. Detects duplicate source event identifiers.
4. Returns an existing record for an identical repeated event.
5. Rejects conflicting reuse of an event identifier.
6. Persists the original event before processing.
7. Transforms and normalizes the telemetry data.
8. Evaluates applicable operational rules.
9. Persists any generated findings.

Webhook timestamps are accepted within the configured tolerance window. This limits the lifetime of signed requests but does not provide complete replay prevention. Existing event idempotency protects against duplicate event creation.


### Data Validation and ETL

The ETL service handles telemetry transformation and validation, including:

- Speed normalization from miles per hour to kilometres per hour.
- Distance normalization from miles to kilometres.
- Coordinate validation.
- Ignition-state handling.
- Validation of supported event data.

Invalid payloads are retained with a failed processing status and an associated error message.

### Deterministic Operational Rules

The current rule engine evaluates normalized telemetry against configured operational thresholds.

The implemented speed rule identifies events exceeding the configured speed threshold.

Findings are stored independently from the original fleet event and include:

- Rule identifier.
- Severity.
- Observed value.
- Threshold.
- Unit of measurement.
- Explanation of the finding.

The rule engine provides deterministic results rather than relying on an AI model to make operational decisions.

### Event Recovery

The recovery service supports the identification and reprocessing of eligible fleet events that remain in a received state.

Database-level row locking with `FOR UPDATE SKIP LOCKED` supports safe selection of work when multiple workers may be involved.

The recovery implementation includes tests against PostgreSQL.

### Fleet Event Investigation

The read-only investigation endpoint provides an evidence-based report for an individual fleet event.

It brings together:

- Original source event information.
- Vehicle identification details.
- Event timestamps.
- Processing status.
- Original telemetry payload.
- Normalized telemetry data.
- Recorded deterministic findings.
- Investigation summary.
- Suggested operational checks.

The endpoint distinguishes between successfully processed, pending, and failed events.

Importantly, an absence of rule-based findings is not treated as proof that a vehicle has no operational issue.

This feature establishes a foundation for future AI-assisted investigation while keeping current findings deterministic and traceable.

## 5. API Endpoints

### Vehicles

| Method | Endpoint | Description |
|---|---|---|
| POST | `/vehicles/` | Register a vehicle |
| GET | `/vehicles/` | List vehicles |
| GET | `/vehicles/{vehicle_id}` | Retrieve a vehicle |
| PATCH | `/vehicles/{vehicle_id}` | Update a vehicle |
| DELETE | `/vehicles/{vehicle_id}` | Delete a vehicle |

### Fleet Events

| Method | Endpoint | Description |
|---|---|---|
| POST | `/fleet-events/` | Ingest a fleet event |
| GET | `/fleet-events/{event_id}/investigation` | Retrieve an investigation report |


#### Authentication

The API uses separate authentication mechanisms for operational access and webhook ingestion.

| Endpoint group | Authentication | Header |
|---|---|---|
| Vehicle endpoints | API key | `X-API-Key` |
| `POST /fleet-events/` | HMAC-SHA256 webhook signature | `X-Webhook-Timestamp` and `X-Webhook-Signature` |
| `GET /fleet-events/{event_id}/investigation` | API key | `X-API-Key` |

The webhook ingestion endpoint does not accept the API key as a substitute for a valid webhook signature.

This separation follows the principle of least privilege: an external fleet tracking system can submit authenticated events without being granted access to vehicle management or investigation endpoints.


### Interactive API Documentation

When the application is running, access:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 6. Project Structure

```text
fleet-operations-intelligence-platform/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── fleet_events.py
│   │       └── vehicles.py
│   │
│   ├── core/
│   │   └── config.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   │
│   ├── models/
│   │   ├── fleet_event.py
│   │   ├── fleet_event_finding.py
│   │   └── vehicle.py
│   │
│   ├── schemas/
│   │   ├── fleet_event.py
│   │   ├── fleet_investigation.py
│   │   └── vehicle.py
│   │
│   ├── services/
│   │   ├── fleet_event_etl.py
│   │   ├── fleet_event_investigation.py
│   │   ├── fleet_event_recovery.py
│   │   └── fleet_rules.py
│   │
│   └── main.py
│
├── migrations/
├── tests/
├── docs/
├── .env.example
├── alembic.ini
├── pyproject.toml
├── requirements-dev.txt
└── README.md
```

## 7. Local Development Setup

### Prerequisites

- Python 3.12
- PostgreSQL 18
- Git

### Clone the repository

```bash
git clone https://github.com/mnzirain/fleet-operations-intelligence-platform.git

cd fleet-operations-intelligence-platform
```

### Create a virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv

.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install -r requirements-dev.txt
```

### Configure environment variables

Create a local `.env` file based on `.env.example`.

Configure the following environment variables:

| Variable | Purpose | Requirement |
|---|---|---|
| `FLEET_ENVIRONMENT` | Application environment | Defaults to development |
| `DATABASE_URL` | PostgreSQL connection string | Required for database access |
| `FLEET_API_KEY` | Authenticates API-key-protected endpoints | Minimum 16 characters |
| `FLEET_WEBHOOK_SECRET` | Authenticates incoming webhook signatures | Minimum 32 characters |
| `FLEET_WEBHOOK_TOLERANCE_SECONDS` | Permitted webhook timestamp difference | Defaults to 300 seconds; maximum 3600 |

Use your own PostgreSQL credentials in `DATABASE_URL`.

Generate a cryptographically secure webhook secret using:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated value into your local `.env` file:

```env
FLEET_WEBHOOK_SECRET=your_generated_secret
FLEET_WEBHOOK_TOLERANCE_SECONDS=300
```

The webhook secret is optional during application startup. However, `POST /fleet-events/` returns HTTP 503 until a valid webhook secret is configured.

The API key is required for vehicle management and event investigation endpoints.

**Security precautions:**

- Never commit `.env` to Git.
- Never expose API keys, webhook secrets, or database passwords in source code, screenshots, logs, or public documentation.
- Use separate, randomly generated secrets for API-key and webhook authentication.

### Apply database migrations

```powershell
python -m alembic upgrade head
```

### Start the API

```powershell
python -m uvicorn app.main:app --reload
```

The API will be available at:

`http://127.0.0.1:8000`

### Send a demonstration webhook

The project includes a demonstration script that sends an authenticated fleet event to the running API.

Before running the script:

1. Start the API.
2. Configure `FLEET_WEBHOOK_SECRET` in your local `.env` file.
3. Ensure at least one vehicle is registered in the database.

Open a second PowerShell terminal in the project directory and run:

```powershell
$secretLine = Get-Content .env | Where-Object { $_ -match '^FLEET_WEBHOOK_SECRET=' } | Select-Object -First 1
$env:FLEET_WEBHOOK_SECRET = $secretLine.Substring('FLEET_WEBHOOK_SECRET='.Length)

$env:FLEET_DEMO_VEHICLE_ID = '<existing-vehicle-uuid>'

python scripts\send_webhook.py
```

Replace `<existing-vehicle-uuid>` with the UUID of a registered vehicle.

The script:

- Generates a unique source event identifier.
- Creates a demonstration `SPEED` event.
- Uses a current UTC timestamp.
- Signs the exact JSON request body using HMAC-SHA256.
- Sends the required webhook authentication headers.
- Displays the API response.

The demonstration uses synthetic telemetry data, including a speed value of 85 km/h and sample coordinates. These values do not represent a verified real-world vehicle location or speed.

A successful request returns HTTP 201 with the created fleet event.

The sender requires the webhook secret but does not require the API key.

The API URL defaults to `http://127.0.0.1:8000`. Set `FLEET_API_URL` in the environment if the API is running at a different address.


## 8. Testing and Code Quality

Run the automated test suite:

```powershell
python -m pytest -q
```

Run Ruff linting:

```powershell
python -m ruff check .
```

Check formatting:

```powershell
python -m ruff format --check .
```

The automated test suite covers:

- Application health and readiness.
- Vehicle management.
- Fleet event ingestion.
- HMAC-SHA256 webhook authentication.
- Missing, malformed, expired, and invalid webhook signatures.
- Webhook timestamp tolerance.
- API key authentication.
- Configuration validation and missing credentials.
- Event validation and ETL.
- Deterministic operational rule evaluation.
- Event recovery and PostgreSQL recovery behaviour.
- Fleet event investigation.
- Duplicate event handling and idempotency.

At the time of the latest local verification:

- 75 automated tests passed.
- Ruff lint checks passed.
- Ruff formatting checks passed.

These results describe local verification and do not imply that the latest changes have already been committed or merged.


## 9. Continuous Integration

GitHub Actions runs the quality and test workflow on pushes and pull requests targeting `main`.

The workflow:

1. Checks out the repository.
2. Sets up Python 3.12.
3. Starts a PostgreSQL 18 service.
4. Installs development dependencies.
5. Applies database migrations.
6. Runs Ruff lint checks.
7. Checks code formatting.
8. Executes the automated test suite.

This provides repeatable automated verification of the application and its database integration.

## 10. Engineering Principles

The project follows several important design principles:

- **Data integrity:** Preserve original incoming events.
- **Idempotency:** Handle repeated source events safely.
- **Traceability:** Retain processing states, timestamps, and errors.
- **Separation of concerns:** Keep API routes, schemas, models, and business services separate.
- **Deterministic evaluation:** Use explicit operational rules for current findings.
- **Recoverability:** Design processing so eligible events can be recovered.
- **Testability:** Verify application behaviour through automated tests.
- **Incremental development:** Introduce additional capabilities without compromising existing functionality.

## Implementation Status

The platform is being developed incrementally. The following table distinguishes implemented capabilities from planned enhancements.

| Capability | Status |
|---|---|
| Python / FastAPI backend | Implemented |
| PostgreSQL persistence | Implemented |
| Vehicle management APIs | Implemented |
| Fleet-event ingestion | Implemented |
| Data validation and ETL | Implemented |
| Duplicate-event handling | Implemented |
| Deterministic operational rules | Implemented |
| Database-backed event recovery | Implemented |
| Evidence-based investigation reporting | Implemented |
| Automated testing and GitHub Actions CI | Implemented |
| AI-assisted investigation | Planned |
| LLM-based explanations | Planned |
| AI evaluation frameworks | Planned |
| AI guardrails and output validation | Planned |
| Human review and approval workflows | Planned |
| External fleet-tracking integration | Planned, subject to access and approval |

The planned capabilities represent the intended development direction and are not yet implemented or commercially deployed.

## 11. Roadmap

The following are planned extensions, not claims of current implementation:

- AI-assisted fleet event investigation.
- LLM-based explanation of operational evidence.
- AI evaluation and guardrails.
- Human review and approval workflows.
- External fleet tracking API and webhook integrations.
- Expanded operational rules and anomaly detection.
- Production deployment and infrastructure automation.
- Further observability and operational monitoring.

The intended design principle is:

**Deterministic rules identify operational conditions. AI may assist with explanations. Human reviewers retain decision authority.**

## 12. Project Status

This is an independently developed portfolio project demonstrating practical backend engineering, API development, database integration, data processing, automated testing, and system design.

It is under active development and is not presented as a deployed commercial fleet management platform.

---

## Repository

GitHub: https://github.com/mnzirain/fleet-operations-intelligence-platform
