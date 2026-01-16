"""
Django 6.0 Tasks implementation for smart meter processing.

This module contains background tasks using Django's native Tasks framework.
These tasks are compared against Celery implementations.
"""

import time
from datetime import datetime, timedelta
from decimal import Decimal
from django.tasks import task
from django.db.models import Sum, Avg, Max, Min, Count
from django.utils import timezone
from meters.models import MeterReading, UsageAggregate, SmartMeter, Customer
from comparison.models import TaskMetric


@task
def process_readings_batch_django(reading_ids):
    """
    Process a batch of meter readings using Django Tasks.

    Args:
        reading_ids: List of MeterReading IDs to process

    Returns:
        dict: Processing results including count and statistics
    """
    start_time = time.time()
    task_name = 'process_readings_batch'

    try:
        # Fetch readings
        readings = MeterReading.objects.filter(id__in=reading_ids).select_related('meter')

        if not readings.exists():
            raise ValueError(f"No readings found for IDs: {reading_ids}")

        processed_count = 0
        total_kwh = Decimal('0.0')

        # Process each reading (validation, business logic, etc.)
        for reading in readings:
            # Validate reading value
            if reading.kwh < 0:
                raise ValueError(f"Negative reading value: {reading.kwh} for reading {reading.id}")

            # Accumulate statistics
            total_kwh += reading.kwh
            processed_count += 1

        # Calculate statistics
        avg_kwh = total_kwh / processed_count if processed_count > 0 else Decimal('0.0')

        duration = time.time() - start_time

        # Record metrics
        TaskMetric.objects.create(
            task_type='django',
            task_name=task_name,
            started_at=datetime.fromtimestamp(start_time, tz=timezone.get_current_timezone()),
            completed_at=timezone.now(),
            duration_seconds=Decimal(str(round(duration, 3))),
            records_processed=processed_count,
            success=True,
            metadata={
                'total_kwh': float(total_kwh),
                'avg_kwh': float(avg_kwh),
                'reading_ids_count': len(reading_ids)
            }
        )

        return {
            'success': True,
            'processed': processed_count,
            'total_kwh': float(total_kwh),
            'avg_kwh': float(avg_kwh),
            'duration': duration
        }

    except Exception as e:
        duration = time.time() - start_time

        # Record failure metrics
        TaskMetric.objects.create(
            task_type='django',
            task_name=task_name,
            started_at=datetime.fromtimestamp(start_time, tz=timezone.get_current_timezone()),
            completed_at=timezone.now(),
            duration_seconds=Decimal(str(round(duration, 3))),
            records_processed=0,
            success=False,
            error_message=str(e),
            metadata={'reading_ids_count': len(reading_ids)}
        )

        raise


@task
def calculate_daily_aggregate_django(meter_id, date_str):
    """
    Calculate daily usage aggregates for a meter using Django Tasks.

    Args:
        meter_id: UUID of the SmartMeter
        date_str: Date string in YYYY-MM-DD format

    Returns:
        dict: Aggregate statistics
    """
    start_time = time.time()
    task_name = 'calculate_daily_aggregate'

    try:
        from datetime import datetime as dt
        target_date = dt.strptime(date_str, '%Y-%m-%d').date()

        # Get meter
        meter = SmartMeter.objects.get(id=meter_id)

        # Calculate date range
        period_start = target_date
        period_end = target_date

        # Get all readings for the day
        readings = MeterReading.objects.filter(
            meter=meter,
            timestamp__date=target_date
        )

        if not readings.exists():
            raise ValueError(f"No readings found for meter {meter_id} on {date_str}")

        # Calculate aggregates
        stats = readings.aggregate(
            total=Sum('kwh'),
            avg=Avg('kwh'),
            peak=Max('kwh'),
            min_val=Min('kwh'),
            count=Count('id')
        )

        # Separate peak and off-peak (7am-10pm is peak for residential)
        peak_readings = readings.filter(
            timestamp__hour__gte=7,
            timestamp__hour__lt=22
        )
        off_peak_readings = readings.exclude(
            timestamp__hour__gte=7,
            timestamp__hour__lt=22
        )

        peak_kwh = peak_readings.aggregate(total=Sum('kwh'))['total'] or Decimal('0.0')
        off_peak_kwh = off_peak_readings.aggregate(total=Sum('kwh'))['total'] or Decimal('0.0')

        # Create or update aggregate record
        aggregate, created = UsageAggregate.objects.update_or_create(
            meter=meter,
            period_type='daily',
            period_start=period_start,
            defaults={
                'period_end': period_end,
                'total_kwh': stats['total'],
                'avg_kwh': stats['avg'],
                'peak_kwh': stats['peak'],
                'off_peak_kwh': off_peak_kwh,
            }
        )

        duration = time.time() - start_time

        # Record metrics
        TaskMetric.objects.create(
            task_type='django',
            task_name=task_name,
            started_at=datetime.fromtimestamp(start_time, tz=timezone.get_current_timezone()),
            completed_at=timezone.now(),
            duration_seconds=Decimal(str(round(duration, 3))),
            records_processed=stats['count'],
            success=True,
            metadata={
                'meter_id': str(meter_id),
                'date': date_str,
                'total_kwh': float(stats['total']),
                'created': created
            }
        )

        return {
            'success': True,
            'meter_id': str(meter_id),
            'date': date_str,
            'total_kwh': float(stats['total']),
            'avg_kwh': float(stats['avg']),
            'peak_kwh': float(stats['peak']),
            'readings_count': stats['count'],
            'created': created,
            'duration': duration
        }

    except Exception as e:
        duration = time.time() - start_time

        TaskMetric.objects.create(
            task_type='django',
            task_name=task_name,
            started_at=datetime.fromtimestamp(start_time, tz=timezone.get_current_timezone()),
            completed_at=timezone.now(),
            duration_seconds=Decimal(str(round(duration, 3))),
            records_processed=0,
            success=False,
            error_message=str(e),
            metadata={'meter_id': str(meter_id), 'date': date_str}
        )

        raise


@task
def bulk_process_readings_django(batch_size=1000):
    """
    Process unprocessed readings in bulk using Django Tasks.

    Args:
        batch_size: Number of readings to process per batch

    Returns:
        dict: Processing summary
    """
    start_time = time.time()
    task_name = 'bulk_process_readings'

    try:
        # Get recent readings (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        readings = MeterReading.objects.filter(
            timestamp__gte=seven_days_ago
        ).order_by('-timestamp')[:batch_size]

        reading_ids = list(readings.values_list('id', flat=True))

        if not reading_ids:
            return {
                'success': True,
                'processed': 0,
                'message': 'No readings to process'
            }

        # Process the batch
        result = process_readings_batch_django.enqueue(reading_ids=reading_ids)

        duration = time.time() - start_time

        # Record metrics
        TaskMetric.objects.create(
            task_type='django',
            task_name=task_name,
            started_at=datetime.fromtimestamp(start_time, tz=timezone.get_current_timezone()),
            completed_at=timezone.now(),
            duration_seconds=Decimal(str(round(duration, 3))),
            records_processed=len(reading_ids),
            success=True,
            metadata={
                'batch_size': batch_size,
                'readings_found': len(reading_ids),
                'subtask_id': str(result.id) if hasattr(result, 'id') else None
            }
        )

        return {
            'success': True,
            'processed': len(reading_ids),
            'task_id': str(result.id) if hasattr(result, 'id') else None,
            'duration': duration
        }

    except Exception as e:
        duration = time.time() - start_time

        TaskMetric.objects.create(
            task_type='django',
            task_name=task_name,
            started_at=datetime.fromtimestamp(start_time, tz=timezone.get_current_timezone()),
            completed_at=timezone.now(),
            duration_seconds=Decimal(str(round(duration, 3))),
            records_processed=0,
            success=False,
            error_message=str(e),
            metadata={'batch_size': batch_size}
        )

        raise


@task
def generate_customer_report_django(customer_id, days=30):
    """
    Generate a comprehensive energy usage report for a customer.

    This is a realistic task for Octopus Energy that:
    - Analyzes all meter readings for a period
    - Calculates peak vs off-peak usage
    - Calculates billing costs
    - Provides usage insights

    Args:
        customer_id: UUID of the customer
        days: Number of days to analyze (default 30)

    Returns:
        dict: Complete energy report with usage and cost breakdown
    """
    start_time = time.time()
    task_name = 'generate_customer_report'

    try:
        # Get customer
        customer = Customer.objects.get(id=customer_id)

        # Get customer's meter
        meter = SmartMeter.objects.filter(customer=customer).first()
        if not meter:
            raise ValueError(f"No meter found for customer {customer_id}")

        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Fetch all readings for the period
        readings = MeterReading.objects.filter(
            meter=meter,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')

        total_readings = readings.count()

        if total_readings == 0:
            raise ValueError(f"No readings found for customer {customer_id} in last {days} days")

        # Calculate usage statistics
        total_kwh = Decimal('0')
        peak_kwh = Decimal('0')  # 7am-11pm
        offpeak_kwh = Decimal('0')  # 11pm-7am

        daily_usage = {}
        daily_peak = {}
        daily_offpeak = {}

        for reading in readings:
            kwh = reading.kwh
            total_kwh += kwh

            # Determine if peak or off-peak
            hour = reading.timestamp.hour
            date_key = reading.timestamp.date()

            if 7 <= hour < 23:  # Peak hours
                peak_kwh += kwh
                if date_key not in daily_peak:
                    daily_peak[date_key] = Decimal('0')
                daily_peak[date_key] += kwh
            else:  # Off-peak hours
                offpeak_kwh += kwh
                if date_key not in daily_offpeak:
                    daily_offpeak[date_key] = Decimal('0')
                daily_offpeak[date_key] += kwh

            # Track daily usage
            if date_key not in daily_usage:
                daily_usage[date_key] = Decimal('0')
            daily_usage[date_key] += kwh

        # Calculate costs (UK rates)
        PEAK_RATE = Decimal('0.25')  # £0.25 per kWh
        OFFPEAK_RATE = Decimal('0.15')  # £0.15 per kWh

        peak_cost = peak_kwh * PEAK_RATE
        offpeak_cost = offpeak_kwh * OFFPEAK_RATE
        total_cost = peak_cost + offpeak_cost

        # Calculate averages
        avg_daily_kwh = total_kwh / Decimal(str(days))

        # Find highest usage day
        if daily_usage:
            highest_day = max(daily_usage.items(), key=lambda x: x[1])
            highest_day_date = highest_day[0].strftime('%Y-%m-%d')
            highest_day_kwh = float(highest_day[1])
        else:
            highest_day_date = None
            highest_day_kwh = 0

        # Simple anomaly detection
        anomaly_threshold = avg_daily_kwh * Decimal('1.5')
        anomalies = sum(1 for usage in daily_usage.values() if usage > anomaly_threshold)

        # Calculate potential savings
        shiftable_kwh = peak_kwh * Decimal('0.20')
        potential_savings = shiftable_kwh * (PEAK_RATE - OFFPEAK_RATE)

        # Prepare daily usage data for charts (sorted by date)
        all_dates = sorted(set(list(daily_usage.keys()) + list(daily_peak.keys()) + list(daily_offpeak.keys())))
        daily_usage_data = [
            {
                'date': date.strftime('%Y-%m-%d'),
                'kwh': round(float(daily_usage.get(date, 0)), 2),
                'peak_kwh': round(float(daily_peak.get(date, 0)), 2),
                'offpeak_kwh': round(float(daily_offpeak.get(date, 0)), 2)
            }
            for date in all_dates
        ]

        duration = time.time() - start_time

        report_data = {
            'customer_id': str(customer_id),
            'customer_name': customer.name,
            'postal_code': customer.postal_code,
            'prefecture': customer.prefecture,
            'city': customer.city,
            'address': customer.address,
            'meter_id': str(meter.id),
            'period_days': days,
            'total_readings': total_readings,
            'total_kwh': round(float(total_kwh), 2),
            'peak_kwh': round(float(peak_kwh), 2),
            'offpeak_kwh': round(float(offpeak_kwh), 2),
            'total_cost_gbp': round(float(total_cost), 2),
            'peak_cost_gbp': round(float(peak_cost), 2),
            'offpeak_cost_gbp': round(float(offpeak_cost), 2),
            'avg_daily_kwh': round(float(avg_daily_kwh), 2),
            'highest_usage_day': highest_day_date,
            'highest_usage_kwh': round(highest_day_kwh, 2),
            'anomaly_days': anomalies,
            'potential_monthly_savings_gbp': round(float(potential_savings), 2),
            'daily_usage': daily_usage_data
        }

        TaskMetric.objects.create(
            task_type='django',
            task_name=task_name,
            started_at=datetime.fromtimestamp(start_time, tz=timezone.get_current_timezone()),
            completed_at=timezone.now(),
            duration_seconds=Decimal(str(round(duration, 3))),
            records_processed=total_readings,
            success=True,
            metadata=report_data
        )

        return {
            'success': True,
            'report': report_data,
            'duration': duration
        }

    except Exception as e:
        duration = time.time() - start_time
        TaskMetric.objects.create(
            task_type='django',
            task_name=task_name,
            started_at=datetime.fromtimestamp(start_time, tz=timezone.get_current_timezone()),
            completed_at=timezone.now(),
            duration_seconds=Decimal(str(round(duration, 3))),
            records_processed=0,
            success=False,
            error_message=str(e)
        )
        raise
