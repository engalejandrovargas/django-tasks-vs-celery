"""
Models for tracking and comparing task execution metrics.

This module contains models for storing performance data from both
Django 6.0 Tasks and Celery task executions.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class TaskMetric(models.Model):
    """
    Stores performance metrics for task executions.

    Tracks execution time, success rate, and other performance indicators
    for both Django Tasks and Celery implementations.
    """

    TASK_TYPE_CHOICES = [
        ('django', 'Django 6.0 Tasks'),
        ('celery', 'Celery'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='メトリックID'
    )
    task_type = models.CharField(
        max_length=10,
        choices=TASK_TYPE_CHOICES,
        db_index=True,
        verbose_name='タスクタイプ'
    )
    task_name = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='タスク名'
    )
    task_id = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text='Original task ID from Django Tasks or Celery',
        verbose_name='タスクID'
    )
    started_at = models.DateTimeField(
        db_index=True,
        verbose_name='開始時刻'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完了時刻'
    )
    duration_seconds = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.000'))],
        null=True,
        blank=True,
        verbose_name='実行時間 (秒)'
    )
    records_processed = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='処理レコード数'
    )
    success = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='成功'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name='エラーメッセージ'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional metadata about the task execution',
        verbose_name='メタデータ'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )

    class Meta:
        db_table = 'task_metrics'
        verbose_name = 'タスクメトリック'
        verbose_name_plural = 'タスクメトリック'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['task_type', 'task_name'], name='idx_metric_type_name'),
            models.Index(fields=['started_at'], name='idx_metric_started'),
            models.Index(fields=['success'], name='idx_metric_success'),
            models.Index(fields=['task_type', 'success'], name='idx_metric_type_success'),
        ]

    def __str__(self):
        status = '成功' if self.success else '失敗'
        return f'{self.task_type} - {self.task_name} - {status} ({self.duration_seconds}s)'

    def calculate_throughput(self):
        """
        Calculate records processed per second.

        Returns:
            Decimal: Records per second, or None if duration is zero
        """
        if self.duration_seconds and self.duration_seconds > 0:
            return Decimal(self.records_processed) / self.duration_seconds
        return None

    @classmethod
    def get_average_duration(cls, task_type=None, task_name=None, success_only=True):
        """
        Get average task duration for specified filters.

        Args:
            task_type: Filter by task type ('django' or 'celery')
            task_name: Filter by specific task name
            success_only: Only include successful tasks

        Returns:
            Decimal: Average duration in seconds
        """
        from django.db.models import Avg

        queryset = cls.objects.all()
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        if task_name:
            queryset = queryset.filter(task_name=task_name)
        if success_only:
            queryset = queryset.filter(success=True)

        result = queryset.aggregate(avg_duration=Avg('duration_seconds'))
        return result['avg_duration']

    @classmethod
    def get_success_rate(cls, task_type=None, task_name=None):
        """
        Calculate success rate for specified filters.

        Args:
            task_type: Filter by task type ('django' or 'celery')
            task_name: Filter by specific task name

        Returns:
            float: Success rate as percentage (0-100)
        """
        queryset = cls.objects.all()
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        if task_name:
            queryset = queryset.filter(task_name=task_name)

        total = queryset.count()
        if total == 0:
            return 0.0

        successful = queryset.filter(success=True).count()
        return (successful / total) * 100
