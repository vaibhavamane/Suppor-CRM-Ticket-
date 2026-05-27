# Suppor CRM | Ticket Management System with Bloom Filter Search Cache

A production-ready, highly optimized CRM backend and frontend dashboard for managing support tickets. Built using **Python FastAPI**, **PostgreSQL** (with a seamless fallback to **SQLite** for rapid local runs), **SQLAlchemy Async ORM**, **Pydantic v2**, and optimized with a **Bloom Filter** search cache using the `pybloom-live` library to bypass database queries for non-existent keywords.

---

## Features

- **Sequential Ticket IDs**: Auto-generated Ticket IDs (e.g. `TKT-001`, `TKT-002`) with integrity retry mechanisms to handle concurrent creation cleanly.
- **Bloom Filter Guard**: Optimizes searching by tokenizing ticket attributes (ID, customer name, email, subject, description) and indexing them (with prefixes of length $\ge 2$ to support partial search queries). Non-existent search terms hit the Bloom Filter cache first, allowing the backend to bypass database calls entirely on search misses.
- **Async Database Stack**: Fully asynchronous database CRUD operations using SQLAlchemy 2.0 with `asyncpg` (PostgreSQL) and `aiosqlite` (SQLite) drivers.
- **Stunning Frontend Panel**: Built with modern CSS (glassmorphism panels, CSS variables, Google Font `Outfit` & `Inter`, micro-animations, and status badge color styling). Includes real-time debounced live search, status filtering, pagination, new ticket modal, and notes timeline.
- **Docker-Compose Ready**: Production-grade orchestration containing a Postgres container (configured with volume storage and database health checking) and a FastAPI application container.

---

## Project Architecture

The codebase follows clean, modular, and scalable software design patterns:

```
app/
├── main.py                  # FastAPI app setup, CORS, lifespan, and static mounting
├── database.py              # Async SQLAlchemy connection engine, sessions, and Base model
│
├── config/
│   └── settings.py          # Settings validation using Pydantic Settings (.env support)
│
├── models/
│   ├── ticket.py            # SQLAlchemy Ticket model mapped to DB columns
│   └── note.py              # SQLAlchemy Note model mapped to DB columns
│
├── schemas/
│   ├── ticket_schema.py     # Pydantic serialization & validation for Tickets
│   └── note_schema.py       # Pydantic serialization for Notes
│
├── routes/
│   └── ticket_routes.py     # REST endpoints map definitions
│
├── services/
│   ├── bloom_service.py     # Bloom Filter operations, tokenization, prefix indexer
│   └── ticket_service.py     # Business logic mapping API routes to DB and Bloom Filter
│
├── utils/
│   └── ticket_id_generator.py # Sequentially increments ticket numeric suffix (TKT-XXX)
│
└── static/                  # Responsive web dashboard
    ├── index.html           # Front-end structure & inline SVGs
    ├── css/
    │   └── styles.css       # Slate dark-mode design with animations
    └── js/
        └── app.js           # Fetch API logic, state, and debounced search triggers
```

---

## Bloom Filter Optimization Logic

### Indexing Pipeline (Tokenization)
When a ticket is created (or loaded on application startup), the system tokenizes its attributes:
1. **Raw values**: `ticket_id`, `customer_name`, `customer_email`, `subject`.
2. **Words**: All space-split and punctuation-split words from all fields.
3. **Prefixes**: For every word/raw value, we generate and store prefixes of length $\ge 2$ (e.g. for `login`, we index `lo`, `log`, `logi`, `login`). This ensures partial-word matches (like searching for "log" to find "login") don't miss the Bloom Filter cache.

### Search Query Filter Flow
1. User types query `search_query` in the search bar.
2. The search query is cleaned, lowercased, and split into individual word tokens.
3. For each word token in the query:
   - Check if it is in the Bloom Filter.
   - If any word token is **NOT** present in the Bloom Filter, the backend is 100% sure that no matching ticket exists in the database.
   - **DB Bypassed**: An empty list `[]` is returned instantly.
4. If all tokens might be in the Bloom Filter (either due to true presence or a rare false positive):
   - **DB Queried**: The backend queries the database using standard case-insensitive SQL `ILIKE` substrings.

---

## Installation & Running

### Option A: Local Run (Rapid Setup with SQLite)
The application has a smart fallback that runs a local SQLite database (`tickets.db`) in async mode if no environment variables are defined.

1. **Create Virtual Environment & Install Dependencies**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate      # Windows
   source venv/bin/activate    # Mac/Linux
   pip install -r requirements.txt
   ```

2. **Start Development Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Access App**:
   - Web GUI Dashboard: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - Interactive Swagger API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API Documentation & Examples

### 1. Create Ticket
- **URL**: `POST /api/tickets`
- **Request Body**:
  ```json
  {
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "subject": "Login Issue",
    "description": "Unable to login to the system console."
  }
  ```
- **Response** (Status `201 Created`):
  ```json
  {
    "ticket_id": "TKT-001",
    "created_at": "2026-05-26T11:05:00Z"
  }
  ```

### 2. List Tickets
- **URL**: `GET /api/tickets`
- **Query Parameters**:
  - `status`: `Open` | `In Progress` | `Closed` (Optional)
  - `search`: string keyword (Optional)
  - `page`: integer (Default: `1`)
  - `limit`: integer (Default: `10`)
- **Response** (Status `200 OK`):
  ```json
  [
    {
      "ticket_id": "TKT-001",
      "customer_name": "John Doe",
      "subject": "Login Issue",
      "status": "Open",
      "created_at": "2026-05-26T11:05:00Z"
    }
  ]
  ```

---

### 3. Get Single Ticket Details
- **URL**: `GET /api/tickets/{ticket_id}`
- **Response** (Status `200 OK`):
  ```json
  {
    "ticket_id": "TKT-001",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "subject": "Login Issue",
    "description": "Unable to login to the system console.",
    "status": "Open",
    "notes": [
      {
        "note_text": "Investigating logs and user session records.",
        "created_at": "2026-05-26T11:15:00Z"
      }
    ]
  }
  ```

---

### 4. Update Ticket Status / Add Note
- **URL**: `PUT /api/tickets/{ticket_id}`
- **Request Body**:
  ```json
  {
    "status": "In Progress",
    "notes": "Issue reproduced in local sandbox environment."
  }
  ```
- **Response** (Status `200 OK`):
  ```json
  {
    "success": true,
    "updated_at": "2026-05-26T11:20:00Z"
  }
  ```