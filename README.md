# Task API

A simple CRUD REST API built using FastAPI.

## Features

- Create tasks
- Read all tasks
- Read a single task
- Update tasks
- Delete tasks
- Swagger UI

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/tharxn/task-api.git
```

### 2. Navigate to the project directory

```bash
cd task-api
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Run the application

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```
http://127.0.0.1:8000
```

---

## API Documentation

FastAPI automatically generates interactive API documentation.

**Swagger UI**

```
http://127.0.0.1:8000/docs
```

**ReDoc**

```
http://127.0.0.1:8000/redoc
```

---

## API Endpoints

| Method | Endpoint      | Description             |
| ------ | ------------- | ----------------------- |
| GET    | `/`           | API information         |
| GET    | `/health`     | Health check            |
| GET    | `/tasks`      | Retrieve all tasks      |
| GET    | `/tasks/{id}` | Retrieve a task by ID   |
| POST   | `/tasks`      | Create a new task       |
| PUT    | `/tasks/{id}` | Update an existing task |
| DELETE | `/tasks/{id}` | Delete a task           |

---

## Example Request

Create a new task:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
-H "Content-Type: application/json" \
-d "{\"title\":\"Buy Milk\"}"
```

### Example Response

```json
{
  "id": 4,
  "title": "Buy Milk",
  "done": false
}
```

---

## Technologies Used

- Python 3
- FastAPI
- Uvicorn
- Pydantic

---

## Project Structure

```text
task-api/
│
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── routes.py
│
├── .gitignore
├── README.md
└── requirements.txt
```

---

## Author

**Tharun Kumar**
