"""
Continuous Task Runner for Performance Testing

This script continuously triggers Django and Celery tasks to generate
real-time performance data for the dashboard.

Usage:
    python run_continuous_tasks.py
    python run_continuous_tasks.py --interval 10 --count 50
"""

import requests
import time
import random
import argparse
import json
from datetime import datetime


API_BASE_URL = "http://localhost:8001/api"
TASK_TRIGGER_URL = f"{API_BASE_URL}/tasks/trigger/"


def trigger_django_task(reading_ids):
    """Trigger a Django task."""
    payload = {
        "task_type": "django",
        "task_name": "process_readings_batch",
        "reading_ids": reading_ids
    }

    try:
        response = requests.post(TASK_TRIGGER_URL, json=payload, timeout=30)
        if response.status_code == 202:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Django task triggered - IDs: {reading_ids[:3]}...{reading_ids[-1]}")
            return True
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Django task failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Error triggering Django task: {e}")
        return False


def trigger_celery_task(reading_ids):
    """Trigger a Celery task."""
    payload = {
        "task_type": "celery",
        "task_name": "process_readings_batch",
        "reading_ids": reading_ids
    }

    try:
        response = requests.post(TASK_TRIGGER_URL, json=payload, timeout=30)
        if response.status_code == 202:
            result = response.json()
            task_id = result.get('task_id', 'unknown')
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Celery task triggered - ID: {task_id[:8]}...")
            return True
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Celery task failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Error triggering Celery task: {e}")
        return False


def get_random_reading_ids(count=10, max_id=35000):
    """Generate random reading IDs."""
    return sorted(random.sample(range(1, max_id), count))


def get_current_stats():
    """Fetch current performance statistics."""
    try:
        response = requests.get(f"{API_BASE_URL}/comparison/summary/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                comparison = data[0]['comparison']
                return comparison
    except Exception:
        pass
    return None


def print_stats():
    """Print current performance statistics."""
    stats = get_current_stats()
    if stats:
        print("\n" + "="*60)
        print("Current Performance Stats:")
        print(f"  Speed: {stats['speed']}")
        print(f"  Django Throughput: {stats['throughput_django']:.2f} rec/sec")
        print(f"  Celery Throughput: {stats['throughput_celery']:.2f} rec/sec")
        print("="*60 + "\n")


def run_continuous_tasks(interval=8, count=None, batch_size=10):
    """
    Run tasks continuously.

    Args:
        interval: Seconds between task executions
        count: Total number of tasks to run (None for infinite)
        batch_size: Number of readings per task
    """
    print("="*60)
    print("🐙 Continuous Task Runner")
    print("="*60)
    print(f"Configuration:")
    print(f"  - Interval: {interval} seconds")
    print(f"  - Tasks to run: {'Infinite' if count is None else count}")
    print(f"  - Batch size: {batch_size} readings per task")
    print(f"  - Dashboard: http://localhost:8001/api/comparison/dashboard/")
    print("="*60)
    print("\nPress Ctrl+C to stop\n")

    executed = 0
    django_count = 0
    celery_count = 0

    try:
        while count is None or executed < count:
            # Alternate between Django and Celery tasks
            if executed % 2 == 0:
                reading_ids = get_random_reading_ids(batch_size)
                if trigger_django_task(reading_ids):
                    django_count += 1
            else:
                reading_ids = get_random_reading_ids(batch_size)
                if trigger_celery_task(reading_ids):
                    celery_count += 1

            executed += 1

            # Print stats every 10 tasks
            if executed % 10 == 0:
                print(f"\n[Progress] Executed: {executed} tasks (Django: {django_count}, Celery: {celery_count})")
                print_stats()

            # Wait before next task
            if count is None or executed < count:
                time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping task runner...")

    print("\n" + "="*60)
    print("Summary:")
    print(f"  Total tasks executed: {executed}")
    print(f"  Django tasks: {django_count}")
    print(f"  Celery tasks: {celery_count}")
    print("="*60)
    print("\n📊 View results: http://localhost:8001/api/comparison/dashboard/\n")


def main():
    parser = argparse.ArgumentParser(
        description="Continuously run tasks for performance testing"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=8,
        help="Seconds between task executions (default: 8)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Total number of tasks to run (default: infinite)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of readings per task (default: 10)"
    )

    args = parser.parse_args()

    # Verify API is accessible
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print(f"❌ Error: API not accessible at {API_BASE_URL}")
            print("Make sure Django server is running on port 8001")
            return
    except Exception as e:
        print(f"❌ Error: Cannot connect to API at {API_BASE_URL}")
        print(f"   {e}")
        print("\nMake sure Django server is running:")
        print("   python manage.py runserver 8001")
        return

    run_continuous_tasks(
        interval=args.interval,
        count=args.count,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
