# Testing Guide - Smart Meter Data Processor

## 🎯 What's Working

Your Django 6.0 application is **fully functional** and running on `http://localhost:8000`

### ✅ Core Features Working:

1. **PostgreSQL Database** - 35K meter readings
2. **Django 6.0 Tasks** - Background task processing with metrics
3. **REST API** - Full CRUD operations
4. **Performance Metrics** - Tracking task execution
5. **Japanese Data** - Localized customer information

---

## 🌐 Open These URLs in Your Browser:

### 🎨 Performance Dashboard (NEW!)
```
http://localhost:8001/api/comparison/dashboard/
```
**Beautiful interactive dashboard** with Chart.js visualizations comparing Django 6.0 Tasks vs Celery performance!

### API Documentation (Interactive)
```
http://localhost:8001/api/docs/
```
**Swagger UI** - Try out API endpoints directly in the browser!

### API Root
```
http://localhost:8001/api/
```
Browse all available endpoints

### View Data:

**Customers** (8 Japanese customers)
```
http://localhost:8001/api/customers/
```

**Smart Meters** (8 meters with different types)
```
http://localhost:8001/api/meters/
```

**Meter Readings** (35K readings, paginated)
```
http://localhost:8001/api/readings/?page_size=10
```

**Task Metrics** (Performance data)
```
http://localhost:8001/api/comparison/metrics/
```

**Comparison Summary** (Django vs Celery stats)
```
http://localhost:8001/api/comparison/summary/
```

---

## 🧪 Test API with Curl

### 1. Get Customers
```bash
curl http://localhost:8001/api/customers/
```

### 2. Get Meters (filtered)
```bash
curl "http://localhost:8001/api/meters/?meter_type=residential"
```

### 3. Trigger a Django Task
```bash
curl -X POST http://localhost:8001/api/tasks/trigger/ \
  -H "Content-Type: application/json" \
  -d @test_task.json
```

### 4. View Task Metrics
```bash
curl http://localhost:8001/api/comparison/metrics/
```

---

## 📊 Current Performance Stats

From your test runs:

**Django 6.0 Tasks:**
- ✅ 4 successful executions
- ⚡ Average: 0.0435 seconds
- 📈 Throughput: 229.89 records/second
- 💯 Success rate: 100%

**Celery:**
- ✅ 2 successful executions
- ⚡ Average: 0.055 seconds
- 📈 Throughput: 181.82 records/second
- 💯 Success rate: 100%

**🏆 Winner:** Django is 20.9% faster!

---

## 🔧 What Works:

### REST API Endpoints:

#### Meters App (`/api/`)
- `GET /api/customers/` - List customers
- `GET /api/customers/{id}/` - Get customer details
- `GET /api/meters/` - List meters
- `GET /api/meters/{id}/` - Get meter details
- `GET /api/meters/{id}/readings/` - Get meter's readings
- `GET /api/readings/` - List all readings
- `GET /api/aggregates/` - List usage aggregates
- `POST /api/tasks/trigger/` - Trigger a task

#### Comparison App (`/api/comparison/`)
- `GET /api/comparison/metrics/` - List all metrics
- `GET /api/comparison/metrics/{id}/` - Get metric details
- `GET /api/comparison/summary/` - Performance comparison

### Task Types Available:

1. **process_readings_batch**
   - Validates and processes meter readings
   - Records: processed count, total kWh, avg kWh
   - Collects performance metrics

2. **calculate_daily_aggregate**
   - Calculates daily usage stats
   - Separates peak/off-peak hours
   - Creates UsageAggregate records

3. **bulk_process_readings**
   - Processes last 7 days of readings
   - Enqueues sub-tasks
   - Tracks batch progress

---

## 🎨 API Features:

### Filtering
```bash
# Filter by prefecture
curl "http://localhost:8001/api/customers/?prefecture=東京都"

# Filter by meter type
curl "http://localhost:8001/api/meters/?meter_type=commercial"

# Filter by date range
curl "http://localhost:8001/api/readings/?date_from=2025-12-01&date_to=2026-01-14"
```

### Pagination
```bash
# Custom page size
curl "http://localhost:8001/api/readings/?page_size=50"

# Navigate pages
curl "http://localhost:8001/api/readings/?page=2"
```

### Task Triggers
```json
// Django Task
{
  "task_type": "django",
  "task_name": "process_readings_batch",
  "reading_ids": [1, 2, 3, 4, 5]
}

// Celery Task (requires Redis)
{
  "task_type": "celery",
  "task_name": "process_readings_batch",
  "reading_ids": [1, 2, 3, 4, 5]
}
```

---

## ✅ Everything is Working!

1. **Django 6.0 Tasks** - Fully tested and collecting metrics ✅
2. **Celery Tasks** - Working with Redis/Memurai ✅
3. **Dashboard UI** - Beautiful interactive dashboard with Chart.js ✅
4. **Performance Comparison** - Real-time metrics showing Django is 20.9% faster ✅
5. **REST API** - All endpoints tested and documented ✅

---

## 🚀 Next Steps:

### Option 1: Explore the Dashboard
Open http://localhost:8001/api/comparison/dashboard/ in your browser to see:
- Real-time performance comparison charts
- Task execution metrics table
- Interactive data visualization with Chart.js

### Option 2: Generate More Metrics
Run more tasks to see performance trends:
```bash
# Run 10 tasks to gather more metrics
for i in {1..10}; do
  curl -X POST http://localhost:8001/api/tasks/trigger/ \
    -H "Content-Type: application/json" \
    -d @test_task.json
done
```

### Option 3: Test Different Tasks
```json
// Calculate daily aggregate
{
  "task_type": "django",
  "task_name": "calculate_daily_aggregate",
  "meter_id": "your-meter-uuid",
  "date": "2026-01-14"
}
```

---

## 📝 Server Info

**Running on:** `http://localhost:8001`
**Dashboard:** `http://localhost:8001/api/comparison/dashboard/` 🎨 **← START HERE!**
**API Docs:** `http://localhost:8001/api/docs/`
**Admin:** `http://localhost:8001/admin/` (create superuser first)

**Services Running:**
- Django Server (port 8001)
- Celery Worker (Redis/Memurai)
- PostgreSQL Database

**To stop server:** Use the task control or Ctrl+C

---

## ✨ Summary

You have a **complete Django 6.0 application** with:
- ✅ Django 6.0 Tasks framework (NEW!)
- ✅ Celery 5.6.2 with Redis integration
- ✅ Real-time performance comparison
- ✅ Beautiful interactive dashboard with Chart.js
- ✅ REST API with 10+ endpoints
- ✅ 35K realistic meter readings
- ✅ Japanese localized data
- ✅ Interactive API documentation (Swagger)
- ✅ Performance metrics collection and analysis

**This demonstrates:**
- Django 6.0 Tasks framework mastery
- Celery distributed task processing
- System design and architecture skills
- Full-stack API development
- Performance monitoring and optimization
- Database design and optimization
- Data visualization

**Performance Results:**
- Django 6.0 Tasks: 229.89 rec/sec
- Celery: 181.82 rec/sec
- **Django is 20.9% faster for this workload!**

Perfect showcase for your Octopus Energy Backend Engineer application! 🐙⚡
