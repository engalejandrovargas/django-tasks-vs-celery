"""
Data models for smart meter management and readings.

This module contains models for customers, smart meters, meter readings,
and usage aggregates for the Japanese energy market.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Customer(models.Model):
    """
    Customer model representing energy consumers in Japan.

    Stores customer information with Japanese address format.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='顧客ID'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='顧客名'
    )
    postal_code = models.CharField(
        max_length=8,
        help_text='Format: 123-4567',
        verbose_name='郵便番号'
    )
    prefecture = models.CharField(
        max_length=10,
        help_text='例: 東京都、大阪府',
        verbose_name='都道府県'
    )
    city = models.CharField(
        max_length=100,
        verbose_name='市区町村'
    )
    address = models.CharField(
        max_length=300,
        verbose_name='住所'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    class Meta:
        db_table = 'customers'
        verbose_name = '顧客'
        verbose_name_plural = '顧客'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['prefecture'], name='idx_customer_prefecture'),
            models.Index(fields=['created_at'], name='idx_customer_created'),
        ]

    def __str__(self):
        return f'{self.name} ({self.prefecture})'


class SmartMeter(models.Model):
    """
    Smart meter model representing physical meters installed at customer locations.
    """

    METER_TYPE_CHOICES = [
        ('residential', '住宅用'),
        ('commercial', '商業用'),
        ('industrial', '産業用'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='メーターID'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='meters',
        verbose_name='顧客'
    )
    meter_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='メーター番号'
    )
    installation_date = models.DateField(
        verbose_name='設置日'
    )
    meter_type = models.CharField(
        max_length=20,
        choices=METER_TYPE_CHOICES,
        default='residential',
        verbose_name='メータータイプ'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )

    class Meta:
        db_table = 'smart_meters'
        verbose_name = 'スマートメーター'
        verbose_name_plural = 'スマートメーター'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['meter_number'], name='idx_meter_number'),
            models.Index(fields=['customer', 'is_active'], name='idx_meter_customer_active'),
            models.Index(fields=['meter_type'], name='idx_meter_type'),
        ]

    def __str__(self):
        return f'{self.meter_number} - {self.customer.name}'


class MeterReading(models.Model):
    """
    Individual meter reading capturing energy consumption at a specific timestamp.

    Readings are typically captured every 30 minutes (48 readings per day).
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name='読取ID'
    )
    meter = models.ForeignKey(
        SmartMeter,
        on_delete=models.CASCADE,
        related_name='readings',
        verbose_name='メーター'
    )
    timestamp = models.DateTimeField(
        db_index=True,
        verbose_name='読取時刻'
    )
    kwh = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.000'))],
        help_text='Energy consumption in kWh',
        verbose_name='消費電力量 (kWh)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )

    class Meta:
        db_table = 'meter_readings'
        verbose_name = 'メーター読取値'
        verbose_name_plural = 'メーター読取値'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['meter', 'timestamp'], name='idx_reading_meter_time'),
            models.Index(fields=['timestamp'], name='idx_reading_timestamp'),
            models.Index(fields=['created_at'], name='idx_reading_created'),
        ]
        unique_together = [['meter', 'timestamp']]

    def __str__(self):
        return f'{self.meter.meter_number} - {self.timestamp} - {self.kwh}kWh'


class UsageAggregate(models.Model):
    """
    Aggregated usage statistics for a meter over a specific time period.

    Pre-calculated aggregates for daily and monthly reporting.
    """

    PERIOD_TYPE_CHOICES = [
        ('daily', '日次'),
        ('monthly', '月次'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='集計ID'
    )
    meter = models.ForeignKey(
        SmartMeter,
        on_delete=models.CASCADE,
        related_name='aggregates',
        verbose_name='メーター'
    )
    period_type = models.CharField(
        max_length=10,
        choices=PERIOD_TYPE_CHOICES,
        verbose_name='集計期間タイプ'
    )
    period_start = models.DateField(
        db_index=True,
        verbose_name='集計期間開始'
    )
    period_end = models.DateField(
        verbose_name='集計期間終了'
    )
    total_kwh = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name='合計消費電力量 (kWh)'
    )
    avg_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name='平均消費電力量 (kWh)'
    )
    peak_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name='ピーク消費電力量 (kWh)'
    )
    off_peak_kwh = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name='オフピーク消費電力量 (kWh)'
    )
    calculated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='計算日時'
    )

    class Meta:
        db_table = 'usage_aggregates'
        verbose_name = '使用量集計'
        verbose_name_plural = '使用量集計'
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['meter', 'period_type', 'period_start'], name='idx_agg_meter_period'),
            models.Index(fields=['period_start'], name='idx_agg_period_start'),
        ]
        unique_together = [['meter', 'period_type', 'period_start']]

    def __str__(self):
        return f'{self.meter.meter_number} - {self.period_type} - {self.period_start}'
