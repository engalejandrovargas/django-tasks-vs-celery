"""
Django REST Framework views for smart meter API.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from meters.models import Customer, SmartMeter, MeterReading, UsageAggregate
from meters.serializers import (
    CustomerSerializer, SmartMeterSerializer,
    MeterReadingSerializer, UsageAggregateSerializer,
    TaskTriggerSerializer
)
from meters.tasks_django import (
    process_readings_batch_django,
    calculate_daily_aggregate_django,
    bulk_process_readings_django,
    generate_customer_report_django
)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for all viewsets."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing customers.

    list: Get all customers
    retrieve: Get a specific customer
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter by prefecture if provided."""
        queryset = Customer.objects.all()
        prefecture = self.request.query_params.get('prefecture', None)
        if prefecture:
            queryset = queryset.filter(prefecture=prefecture)
        return queryset.order_by('-created_at')


class SmartMeterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing smart meters.

    list: Get all meters
    retrieve: Get a specific meter
    readings: Get readings for a specific meter
    """
    queryset = SmartMeter.objects.all()
    serializer_class = SmartMeterSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter by meter type or status."""
        queryset = SmartMeter.objects.select_related('customer').all()
        meter_type = self.request.query_params.get('meter_type', None)
        is_active = self.request.query_params.get('is_active', None)

        if meter_type:
            queryset = queryset.filter(meter_type=meter_type)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['get'])
    def readings(self, request, pk=None):
        """Get all readings for a specific meter."""
        meter = self.get_object()
        readings = MeterReading.objects.filter(meter=meter).order_by('-timestamp')

        # Apply pagination
        page = self.paginate_queryset(readings)
        if page is not None:
            serializer = MeterReadingSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MeterReadingSerializer(readings, many=True)
        return Response(serializer.data)


class MeterReadingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing meter readings.

    list: Get all readings
    retrieve: Get a specific reading
    """
    queryset = MeterReading.objects.all()
    serializer_class = MeterReadingSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter by meter, date range, etc."""
        queryset = MeterReading.objects.select_related('meter').all()

        # Filter by meter
        meter_id = self.request.query_params.get('meter_id', None)
        if meter_id:
            queryset = queryset.filter(meter__id=meter_id)

        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)

        return queryset.order_by('-timestamp')


class UsageAggregateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing usage aggregates.

    list: Get all aggregates
    retrieve: Get a specific aggregate
    """
    queryset = UsageAggregate.objects.all()
    serializer_class = UsageAggregateSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter by meter, period type, date range."""
        queryset = UsageAggregate.objects.select_related('meter').all()

        # Filter by meter
        meter_id = self.request.query_params.get('meter_id', None)
        if meter_id:
            queryset = queryset.filter(meter__id=meter_id)

        # Filter by period type
        period_type = self.request.query_params.get('period_type', None)
        if period_type:
            queryset = queryset.filter(period_type=period_type)

        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(period_start__gte=date_from)
        if date_to:
            queryset = queryset.filter(period_start__lte=date_to)

        return queryset.order_by('-period_start')


@api_view(['POST'])
def trigger_task(request):
    """
    Trigger a background task (Django or Celery).

    POST data:
    {
        "task_type": "django" or "celery",
        "task_name": "process_readings_batch" | "calculate_daily_aggregate" | "bulk_process_readings",
        "reading_ids": [1, 2, 3],  # For process_readings_batch
        "meter_id": "uuid",         # For calculate_daily_aggregate
        "date": "2026-01-14",      # For calculate_daily_aggregate
        "batch_size": 1000          # For bulk_process_readings
    }
    """
    serializer = TaskTriggerSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    task_type = data['task_type']
    task_name = data['task_name']

    try:
        # Route to appropriate task implementation
        if task_type == 'django':
            result = _trigger_django_task(task_name, data)
        elif task_type == 'celery':
            result = _trigger_celery_task(task_name, data)
        else:
            return Response(
                {'error': 'Invalid task_type'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(result, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _trigger_django_task(task_name, data):
    """Trigger a Django 6.0 Task."""
    if task_name == 'process_readings_batch':
        result = process_readings_batch_django.enqueue(
            reading_ids=data['reading_ids']
        )
        return {
            'task_type': 'django',
            'task_name': task_name,
            'task_id': str(result.id) if hasattr(result, 'id') else None,
            'status': 'Task enqueued (ImmediateBackend executes synchronously)',
            'result': result._return_value if hasattr(result, '_return_value') else None
        }

    elif task_name == 'calculate_daily_aggregate':
        result = calculate_daily_aggregate_django.enqueue(
            meter_id=str(data['meter_id']),
            date_str=data['date'].strftime('%Y-%m-%d')
        )
        return {
            'task_type': 'django',
            'task_name': task_name,
            'task_id': str(result.id) if hasattr(result, 'id') else None,
            'status': 'Task enqueued',
            'result': result._return_value if hasattr(result, '_return_value') else None
        }

    elif task_name == 'bulk_process_readings':
        result = bulk_process_readings_django.enqueue(
            batch_size=data.get('batch_size', 1000)
        )
        return {
            'task_type': 'django',
            'task_name': task_name,
            'task_id': str(result.id) if hasattr(result, 'id') else None,
            'status': 'Task enqueued',
            'result': result._return_value if hasattr(result, '_return_value') else None
        }

    elif task_name == 'generate_customer_report':
        result = generate_customer_report_django.enqueue(
            customer_id=str(data['customer_id']),
            days=data.get('days', 30)
        )
        return {
            'task_type': 'django',
            'task_name': task_name,
            'task_id': str(result.id) if hasattr(result, 'id') else None,
            'status': 'Task enqueued (ImmediateBackend executes synchronously)',
            'result': result._return_value if hasattr(result, '_return_value') else None
        }


def _trigger_celery_task(task_name, data):
    """Trigger a Celery task."""
    try:
        from meters.tasks_celery import (
            process_readings_batch_celery,
            calculate_daily_aggregate_celery,
            bulk_process_readings_celery,
            generate_customer_report_celery
        )

        if task_name == 'process_readings_batch':
            result = process_readings_batch_celery.apply_async(
                args=[data['reading_ids']]
            )
        elif task_name == 'calculate_daily_aggregate':
            result = calculate_daily_aggregate_celery.apply_async(
                args=[str(data['meter_id']), data['date'].strftime('%Y-%m-%d')]
            )
        elif task_name == 'bulk_process_readings':
            result = bulk_process_readings_celery.apply_async(
                args=[data.get('batch_size', 1000)]
            )
        elif task_name == 'generate_customer_report':
            result = generate_customer_report_celery.apply_async(
                args=[str(data['customer_id']), data.get('days', 30)]
            )

        return {
            'task_type': 'celery',
            'task_name': task_name,
            'task_id': result.id,
            'status': 'Task enqueued',
            'note': 'Task will be processed by Celery worker'
        }

    except Exception as e:
        # Celery requires Redis to be running
        return {
            'error': f'Celery unavailable: {str(e)}',
            'note': 'Make sure Redis is running and Celery worker is started'
        }
