# Smart Meter Data Processor

A Django application comparing **django-tasks** (async DatabaseBackend) with **Celery** for asynchronous processing of smart meter readings.

## Overview

This project processes simulated smart meter readings asynchronously and provides a side-by-side comparison of Django's Tasks framework (via `django-tasks` package with DatabaseBackend) versus Celery.

### Features

- **Django Tasks (Async)**: True async execution with `django-tasks` DatabaseBackend
- **Celery Integration**: Distributed task processing with Redis broker
- **Fair Comparison**: Both systems run tasks in separate worker processes
- **Interactive Dashboard**: Chart.js visualization comparing performance metrics
- **REST API**: Django REST Framework with Swagger documentation
- **Performance Metrics**: Real-time comparison of execution times
- **Japanese Localization**: Customer data formatted for Japanese market
- **PostgreSQL**: Optimized database with 35K+ readings

## Technology Stack

- Python 3.12+
- Django 6
- django-tasks 0.11.0 (DatabaseBackend for async execution)
- Django REST Framework
- PostgreSQL 14+
- Redis 7+ / Memurai (Windows) - for Celery
- Celery 5.6.2
- Flower 2.0.1 (Celery monitoring dashboard)

## Project Structure

```
DjangoWorkers/
├── config/                 # Django project configuration
├── meters/                 # Core application (models, tasks, API)
├── comparison/             # Performance comparison dashboard
├── utils/                  # Utilities (data generator)
├── requirements.txt        # Python dependencies
├── start.sh                # Starts all services in separate terminal windows
├── stop.sh                 # Stops all running services
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 7+ (or Memurai on Windows)

### Setup

```bash
# Create virtual environment
python -m venv myenv
myenv\Scripts\activate  # Windows
source myenv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure database (copy and edit .env)
cp .env.example .env

# Run migrations
python manage.py migrate

# Generate test data
python manage.py generate_data --months 6

# Create superuser (optional)
python manage.py createsuperuser
```

### Running the Application

#### Step 1: Start Required Services

Before running the application, ensure these services are running:

**PostgreSQL** (required for both Django Tasks and the application):
- Windows: Start via Services (`services.msc`) or pgAdmin
- Linux/Mac: `sudo service postgresql start` or `brew services start postgresql`

**Redis/Memurai** (required for Celery only):

Windows (Memurai):
```powershell
# Start Memurai (run PowerShell as Administrator)
Start-Service Memurai

# Or run directly if service won't start
& "C:\Program Files\Memurai\memurai.exe"
```

Linux/Mac (Redis):
```bash
redis-server
```

#### Step 2: Start the Application

The project includes scripts that handle everything automatically:

```bash
# Start all services
./start.sh

# Stop all services
./stop.sh
```

`start.sh` will:
- Verify the virtual environment exists
- Auto-install dependencies if missing
- Check PostgreSQL and Redis connectivity before starting
- Open each service in its own terminal window (Django server, Django Tasks worker, Celery worker, Flower)
- Clean up any stale processes from previous runs

> **Note:** If Redis/Memurai is not running, `start.sh` will still start Django and the Django Tasks worker — only Celery and Flower will be skipped.

#### Manual Start (alternative)

If you prefer to start services individually:

**Terminal 1 - Django Server:**
```bash
python manage.py runserver 8001
```

**Terminal 2 - Django Tasks Worker:**
```bash
python manage.py db_worker
```

**Terminal 3 - Celery Worker:**
```bash
celery -A config worker -l info --pool=solo
```

**Terminal 4 - Flower (Celery Monitoring):**
```bash
celery -A config flower --port=5555
```

### Access Points

| Service | URL |
|---------|-----|
| Comparison Dashboard | http://localhost:8001/api/comparison/dashboard/ |
| Flower (Celery Monitor) | http://localhost:5555/ |
| API Docs (Swagger) | http://localhost:8001/api/docs/ |
| API Docs (ReDoc) | http://localhost:8001/api/redoc/ |

## API Usage

### Trigger Tasks

```bash
# Django Task
curl -X POST http://localhost:8001/api/tasks/trigger/ \
  -H "Content-Type: application/json" \
  -d '{"task_type": "django", "task_name": "process_readings_batch", "reading_ids": [1,2,3,4,5]}'

# Celery Task
curl -X POST http://localhost:8001/api/tasks/trigger/ \
  -H "Content-Type: application/json" \
  -d '{"task_type": "celery", "task_name": "process_readings_batch", "reading_ids": [1,2,3,4,5]}'
```

### Generate Reports

```bash
# Generate customer report via Django
curl -X POST "http://localhost:8001/api/comparison/generate-report/?task_type=django&customer_id=<uuid>"

# Generate customer report via Celery
curl -X POST "http://localhost:8001/api/comparison/generate-report/?task_type=celery&customer_id=<uuid>"
```

### View Data

```bash
# List customers
curl http://localhost:8001/api/customers/

# List meters
curl http://localhost:8001/api/meters/

# View task metrics
curl http://localhost:8001/api/comparison/metrics/

# View performance comparison
curl http://localhost:8001/api/comparison/summary/
```

## Architecture Comparison

Both systems now run tasks **asynchronously** in separate worker processes:

| Aspect | Django Tasks (DatabaseBackend) | Celery |
|--------|-------------------------------|--------|
| **Execution** | Async (db_worker process) | Async (celery worker) |
| **Broker** | PostgreSQL (existing DB) | Redis |
| **Task Storage** | Database table | Redis |
| **Worker Command** | `python manage.py db_worker` | `celery -A config worker` |
| **Monitoring** | Django Admin / DB queries | Flower dashboard |
| **Extra Infrastructure** | None (uses existing DB) | Requires Redis |
| **Retry Support** | Manual | Built-in with `max_retries` |

### When to Use Each

**Django Tasks (django-tasks)**:
- Simple background jobs
- Django-centric workflows
- No additional infrastructure needed
- Lower operational overhead
- Atomic task enqueuing within DB transactions

**Celery**:
- Complex workflows (chains, groups, chords)
- Distributed systems across multiple servers
- Advanced scheduling (beat)
- Production-scale with many workers
- Built-in retry mechanisms

## License

MIT License
