# Task Management API

A Flask-based REST API for managing tasks. All strings are internationalized via Flask-Babel.

## Conventions

This codebase strictly follows these conventions:

### 1. Global Imports
All imports are declared at the top of every file. No imports are placed inside functions or conditional blocks.

### 2. Internationalization (Flask-Babel)
Every user-facing string in API responses is wrapped with `gettext` (`_()`) from Flask-Babel. No hardcoded English strings appear in route handlers or templates. Translation `.po` files are stored under `app/translations/`.

### 3. Docstrings on Every Route
Each route handler has a docstring that documents:
- The endpoint URL
- The HTTP method
- The expected request body (if any)
- The response format

### 4. `__repr__` on Every Model
Every SQLAlchemy model implements a `__repr__` method that returns a meaningful string representation.

### 5. Repository Pattern
Route handlers never access the database directly. All data-access logic lives in repository classes under `app/repositories/`. Routes call repository methods exclusively.

## Project Structure

```
.
├── app/
│   ├── __init__.py          # App factory, db/babel init
│   ├── models/
│   │   └── task.py          # Task SQLAlchemy model
│   ├── repositories/
│   │   └── task_repository.py  # Task data-access layer
│   ├── routes/
│   │   └── tasks.py         # API route handlers
│   └── translations/
│       └── fr/LC_MESSAGES/
│           └── messages.po  # French translations
├── tests/
│   └── test_tasks.py        # Pytest test suite
├── config.py                # Configuration classes
├── run.py                   # Application entry point
├── requirements.txt
└── README.md
```

## API Endpoints

| Method   | Endpoint       | Description      |
|----------|----------------|------------------|
| `GET`    | `/tasks`       | List all tasks   |
| `POST`   | `/tasks`       | Create a task    |
| `GET`    | `/tasks/<id>`  | Get a single task|
| `PUT`    | `/tasks/<id>`  | Update a task    |
| `DELETE` | `/tasks/<id>`  | Delete a task    |

### Request / Response Examples

**POST /tasks**
```json
// Request
{ "title": "Buy groceries", "description": "Milk, eggs, bread" }

// Response (201)
{ "id": 1, "title": "Buy groceries", "description": "Milk, eggs, bread", "done": false }
```

**Error Response**
```json
{ "error": "Title is required." }
```

## Setup

```bash
pip install -r requirements.txt
python run.py
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Translating

The project ships with a French (`fr`) translation. To compile:

```bash
pybabel compile -d app/translations
```

To add a new language:

```bash
pybabel init -i app/translations/messages.pot -d app/translations -l <lang_code>
```
