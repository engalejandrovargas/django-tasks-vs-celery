"""
Serializers for task comparison and metrics.
"""

from rest_framework import serializers
from comparison.models import TaskMetric


class TaskMetricSerializer(serializers.ModelSerializer):
    """Serializer for TaskMetric model."""

    throughput = serializers.SerializerMethodField()

    class Meta:
        model = TaskMetric
        fields = [
            'id', 'task_type', 'task_name', 'task_id',
            'started_at', 'completed_at', 'duration_seconds',
            'records_processed', 'success', 'error_message',
            'metadata', 'throughput', 'created_at'
        ]
        read_only_fields = fields

    def get_throughput(self, obj):
        """Calculate records per second."""
        return float(obj.calculate_throughput()) if obj.calculate_throughput() else None


class ComparisonSummarySerializer(serializers.Serializer):
    """Serializer for comparison summary statistics."""

    task_name = serializers.CharField()
    django_stats = serializers.DictField()
    celery_stats = serializers.DictField()
    comparison = serializers.DictField()
