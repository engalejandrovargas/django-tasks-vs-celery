"""
Celery tasks module for meters app.

This file is required for Celery's autodiscover_tasks() to find our tasks.
It imports all tasks from tasks_celery.py.
"""

from meters.tasks_celery import (
    process_readings_batch_celery,
    calculate_daily_aggregate_celery,
    bulk_process_readings_celery,
    generate_customer_report_celery,
)

__all__ = [
    'process_readings_batch_celery',
    'calculate_daily_aggregate_celery',
    'bulk_process_readings_celery',
    'generate_customer_report_celery',
]
