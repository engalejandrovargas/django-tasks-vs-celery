"""
Django REST Framework serializers for smart meter data.
"""

from rest_framework import serializers
from meters.models import Customer, SmartMeter, MeterReading, UsageAggregate


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model."""

    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'postal_code', 'prefecture',
            'city', 'address', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SmartMeterSerializer(serializers.ModelSerializer):
    """Serializer for SmartMeter model."""

    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_prefecture = serializers.CharField(source='customer.prefecture', read_only=True)

    class Meta:
        model = SmartMeter
        fields = [
            'id', 'customer', 'customer_name', 'customer_prefecture',
            'meter_number', 'installation_date', 'meter_type',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MeterReadingSerializer(serializers.ModelSerializer):
    """Serializer for MeterReading model."""

    meter_number = serializers.CharField(source='meter.meter_number', read_only=True)

    class Meta:
        model = MeterReading
        fields = [
            'id', 'meter', 'meter_number', 'timestamp',
            'kwh', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UsageAggregateSerializer(serializers.ModelSerializer):
    """Serializer for UsageAggregate model."""

    meter_number = serializers.CharField(source='meter.meter_number', read_only=True)

    class Meta:
        model = UsageAggregate
        fields = [
            'id', 'meter', 'meter_number', 'period_type',
            'period_start', 'period_end', 'total_kwh',
            'avg_kwh', 'peak_kwh', 'off_peak_kwh',
            'calculated_at'
        ]
        read_only_fields = ['id', 'calculated_at']


class TaskTriggerSerializer(serializers.Serializer):
    """Serializer for triggering tasks."""

    task_type = serializers.ChoiceField(choices=['django', 'celery'])
    task_name = serializers.ChoiceField(
        choices=[
            'process_readings_batch',
            'calculate_daily_aggregate',
            'bulk_process_readings',
            'generate_customer_report'
        ]
    )
    reading_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='Required for process_readings_batch'
    )
    meter_id = serializers.UUIDField(
        required=False,
        help_text='Required for calculate_daily_aggregate'
    )
    date = serializers.DateField(
        required=False,
        help_text='Required for calculate_daily_aggregate (YYYY-MM-DD)'
    )
    batch_size = serializers.IntegerField(
        required=False,
        default=1000,
        help_text='For bulk_process_readings'
    )
    customer_id = serializers.UUIDField(
        required=False,
        help_text='Required for generate_customer_report'
    )
    days = serializers.IntegerField(
        required=False,
        default=30,
        help_text='Number of days to analyze for generate_customer_report (default: 30)'
    )

    def validate(self, data):
        """Validate required fields based on task_name."""
        task_name = data.get('task_name')

        if task_name == 'process_readings_batch':
            if not data.get('reading_ids'):
                raise serializers.ValidationError({
                    'reading_ids': 'This field is required for process_readings_batch'
                })

        elif task_name == 'calculate_daily_aggregate':
            if not data.get('meter_id'):
                raise serializers.ValidationError({
                    'meter_id': 'This field is required for calculate_daily_aggregate'
                })
            if not data.get('date'):
                raise serializers.ValidationError({
                    'date': 'This field is required for calculate_daily_aggregate'
                })

        elif task_name == 'generate_customer_report':
            if not data.get('customer_id'):
                raise serializers.ValidationError({
                    'customer_id': 'This field is required for generate_customer_report'
                })

        return data
