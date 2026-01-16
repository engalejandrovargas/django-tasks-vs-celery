"""
Views for task comparison and performance metrics.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.shortcuts import render
from django.db.models import Avg, Min, Max, Count, Q
from decimal import Decimal
from comparison.models import TaskMetric
from comparison.serializers import TaskMetricSerializer, ComparisonSummarySerializer


class TaskMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing task execution metrics.

    list: Get all metrics
    retrieve: Get a specific metric
    clear: Delete all customer report metrics
    """
    queryset = TaskMetric.objects.all()
    serializer_class = TaskMetricSerializer

    def get_queryset(self):
        """Filter by task type, task name, success status."""
        queryset = TaskMetric.objects.all()

        # Filter by task type
        task_type = self.request.query_params.get('task_type', None)
        if task_type:
            queryset = queryset.filter(task_type=task_type)

        # Filter by task name
        task_name = self.request.query_params.get('task_name', None)
        if task_name:
            queryset = queryset.filter(task_name=task_name)

        # Filter by success
        success = self.request.query_params.get('success', None)
        if success is not None:
            queryset = queryset.filter(success=success.lower() == 'true')

        return queryset.order_by('-started_at')

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Delete all customer report metrics."""
        deleted_count = TaskMetric.objects.filter(task_name='generate_customer_report').delete()[0]
        return Response({
            'status': 'success',
            'deleted_count': deleted_count,
            'message': f'Deleted {deleted_count} customer report metrics'
        })


@api_view(['GET'])
def comparison_summary(request):
    """
    Get summary statistics comparing Django Tasks vs Celery.

    Returns aggregated performance metrics for each task type.
    """
    # Get unique task names
    task_names = TaskMetric.objects.values_list('task_name', flat=True).distinct()

    summaries = []

    for task_name in task_names:
        # Django stats
        django_metrics = TaskMetric.objects.filter(
            task_type='django',
            task_name=task_name,
            success=True
        )

        # Celery stats
        celery_metrics = TaskMetric.objects.filter(
            task_type='celery',
            task_name=task_name,
            success=True
        )

        if not django_metrics.exists() and not celery_metrics.exists():
            continue

        # Calculate Django statistics
        django_stats = _calculate_stats(django_metrics)

        # Calculate Celery statistics
        celery_stats = _calculate_stats(celery_metrics)

        # Calculate comparison
        comparison = _calculate_comparison(django_stats, celery_stats)

        summaries.append({
            'task_name': task_name,
            'django_stats': django_stats,
            'celery_stats': celery_stats,
            'comparison': comparison
        })

    serializer = ComparisonSummarySerializer(summaries, many=True)
    return Response(serializer.data)


def _calculate_stats(queryset):
    """Calculate statistics for a queryset of metrics."""
    if not queryset.exists():
        return {
            'count': 0,
            'avg_duration': None,
            'min_duration': None,
            'max_duration': None,
            'total_records': 0,
            'avg_throughput': None,
            'success_rate': 0
        }

    stats = queryset.aggregate(
        count=Count('id'),
        avg_duration=Avg('duration_seconds'),
        min_duration=Min('duration_seconds'),
        max_duration=Max('duration_seconds'),
        total_records=Count('records_processed')
    )

    # Calculate average throughput
    total_duration = sum(float(m.duration_seconds) for m in queryset if m.duration_seconds)
    total_records = sum(m.records_processed for m in queryset)
    avg_throughput = total_records / total_duration if total_duration > 0 else 0

    # Success rate
    total_count = TaskMetric.objects.filter(
        task_type=queryset.first().task_type,
        task_name=queryset.first().task_name
    ).count()
    success_rate = (stats['count'] / total_count * 100) if total_count > 0 else 0

    return {
        'count': stats['count'],
        'avg_duration': float(stats['avg_duration']) if stats['avg_duration'] else None,
        'min_duration': float(stats['min_duration']) if stats['min_duration'] else None,
        'max_duration': float(stats['max_duration']) if stats['max_duration'] else None,
        'total_records': total_records,
        'avg_throughput': round(avg_throughput, 2),
        'success_rate': round(success_rate, 2)
    }


def _calculate_comparison(django_stats, celery_stats):
    """Calculate comparison metrics between Django and Celery."""
    comparison = {}

    # Speed comparison
    if django_stats['avg_duration'] and celery_stats['avg_duration']:
        if django_stats['avg_duration'] < celery_stats['avg_duration']:
            faster_percent = ((celery_stats['avg_duration'] - django_stats['avg_duration']) /
                            celery_stats['avg_duration'] * 100)
            comparison['speed'] = f"Django is {faster_percent:.1f}% faster"
            comparison['winner'] = 'django'
        else:
            faster_percent = ((django_stats['avg_duration'] - celery_stats['avg_duration']) /
                            django_stats['avg_duration'] * 100)
            comparison['speed'] = f"Celery is {faster_percent:.1f}% faster"
            comparison['winner'] = 'celery'
    else:
        comparison['speed'] = 'Insufficient data'
        comparison['winner'] = None

    # Throughput comparison
    if django_stats['avg_throughput'] and celery_stats['avg_throughput']:
        comparison['throughput_django'] = django_stats['avg_throughput']
        comparison['throughput_celery'] = celery_stats['avg_throughput']
    else:
        comparison['throughput_django'] = None
        comparison['throughput_celery'] = None

    # Reliability comparison
    comparison['reliability_django'] = django_stats['success_rate']
    comparison['reliability_celery'] = celery_stats['success_rate']

    return comparison


def dashboard(request):
    """
    Render the customer reports dashboard.

    Shows real-time report generation status for Django Tasks vs Celery.
    """
    return render(request, 'comparison/dashboard.html')


@api_view(['GET'])
def get_customers(request):
    """Get list of all customers for report generation."""
    from meters.models import Customer
    customers = Customer.objects.all()
    customer_list = [{'id': str(c.id), 'name': c.name} for c in customers]
    return Response(customer_list)


@api_view(['POST'])
def generate_report(request):
    """Generate a customer report using Django Tasks or Celery."""
    from meters.models import Customer
    from meters.tasks_django import generate_customer_report_django
    from meters.tasks_celery import generate_customer_report_celery

    customer_id = request.data.get('customer_id')
    report_type = request.data.get('type', 'django')

    if not customer_id:
        return Response({'success': False, 'error': 'customer_id is required'}, status=400)

    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        return Response({'success': False, 'error': 'Customer not found'}, status=404)

    if report_type == 'django':
        # Django task - use .enqueue() to execute immediately with ImmediateBackend
        task_result = generate_customer_report_django.enqueue(customer_id)
        result = {
            'success': task_result.status == 'SUCCESSFUL',
            'task_id': task_result.id,
            'status': task_result.status,
            'return_value': task_result.return_value if hasattr(task_result, 'return_value') else None
        }
    elif report_type == 'celery':
        # Celery task - use .delay() to queue asynchronously
        task = generate_customer_report_celery.delay(customer_id)
        result = {'success': True, 'task_id': task.id, 'status': 'queued'}
    else:
        return Response({'success': False, 'error': 'Invalid type'}, status=400)

    return Response(result)


@api_view(['GET'])
def get_reports(request, task_type):
    """Get reports for a specific task type (django or celery)."""
    if task_type not in ['django', 'celery']:
        return Response({'error': 'Invalid task type'}, status=400)

    reports = TaskMetric.objects.filter(
        task_type=task_type,
        task_name='generate_customer_report',
        success=True
    ).order_by('-created_at')[:50]

    formatted_reports = [{
        'id': str(r.id),
        'task_type': r.task_type,
        'task_name': r.task_name,
        'task_id': r.task_id,
        'started_at': r.started_at.isoformat(),
        'duration': float(r.duration_seconds),
        'metadata': r.metadata,
        'created_at': r.created_at.isoformat()
    } for r in reports]

    return Response(formatted_reports)


@api_view(['POST'])
def clear_reports(request):
    """Clear all customer reports."""
    deleted_count = TaskMetric.objects.filter(task_name='generate_customer_report').delete()[0]
    return Response({'success': True, 'deleted_count': deleted_count})
