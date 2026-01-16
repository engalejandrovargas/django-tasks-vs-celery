# Smart Meter Data Processor

A Django 6.0 application comparing native Django Tasks framework with Celery for asynchronous processing of smart meter readings.

## Overview

This project processes simulated smart meter readings asynchronously and provides a side-by-side comparison of Django 6.0's new Tasks framework versus Celery.

### Features

- **Django 6.0 Tasks**: Native background task framework
- **Celery Integration**: Distributed task processing with Redis broker
- **Interactive Dashboard**: Chart.js visualization comparing performance metrics
- **REST API**: Django REST Framework with Swagger documentation
- **Performance Metrics**: Real-time comparison (Django ~20% faster)
- **Japanese Localization**: Customer data formatted for Japanese market
- **PostgreSQL**: Optimized database with 35K+ readings

## Technology Stack

- Python 3.12+
- Django 6.0 (with native Tasks framework)
- Django REST Framework 3.16
- PostgreSQL 14+
- Redis 7+ / Memurai (Windows)
- Celery 5.6.2

## Project Structure

```
Octopus/
├── config/                 # Django project configuration
├── meters/                 # Core application (models, tasks, API)
├── comparison/             # Performance comparison dashboard
├── utils/                  # Utilities (data generator)
├── requirements.txt        # Python dependencies
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

**Terminal 1 - Django Server:**
```bash
python manage.py runserver 8001
```

**Terminal 2 - Celery Worker:**
```bash
celery -A config worker -l info --pool=solo  # --pool=solo for Windows
```

### Access Points

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:8001/api/comparison/dashboard/ |
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

## Performance Comparison

The dashboard provides real-time comparison between Django Tasks and Celery:

| Metric | Django 6.0 Tasks | Celery |
|--------|------------------|--------|
| Avg Duration | ~0.04s | ~0.05s |
| Throughput | ~230 rec/s | ~180 rec/s |
| Success Rate | 100% | 100% |

**Result**: Django Tasks is faster for simple synchronous-style tasks.

### When to Use Each

**Django Tasks**:
- Simple background jobs
- Django-centric workflows
- Development/prototyping
- Lower operational overhead

**Celery**:
- Complex workflows (chains, groups)
- Distributed systems
- Advanced scheduling
- Production-scale async processing

## License

MIT License
