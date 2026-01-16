"""
Django management command to generate test smart meter data.

Usage:
    python manage.py generate_data --months 6 --meters 5
"""

import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from meters.models import Customer, SmartMeter, MeterReading
from utils.data_generator import (
    generate_japanese_customer,
    generate_meter_number,
    generate_readings,
    get_customer_profiles,
    print_summary
)


class Command(BaseCommand):
    help = 'Generate test smart meter data with Japanese customers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            default=6,
            help='Number of months of data to generate (default: 6)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before generating new data'
        )

    def handle(self, *args, **options):
        months = options['months']
        clear_existing = options['clear']

        self.stdout.write(
            self.style.SUCCESS(f'\nGenerating {months} months of smart meter data...\n')
        )

        # Clear existing data if requested
        if clear_existing:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            MeterReading.objects.all().delete()
            SmartMeter.objects.all().delete()
            Customer.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('[OK] Existing data cleared\n'))

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)

        # Get customer profiles
        profiles = get_customer_profiles()

        customers_created = 0
        meters_created = 0
        readings_created = 0

        try:
            with transaction.atomic():
                # Generate data for each profile
                for profile_name, meter_type, base_monthly_kwh in profiles:
                    self.stdout.write(f'Creating {profile_name}...')

                    # Create customer
                    customer_data = generate_japanese_customer()
                    customer = Customer.objects.create(**customer_data)
                    customers_created += 1

                    # Create smart meter
                    installation_date = start_date - timedelta(days=random.randint(30, 365))
                    meter = SmartMeter.objects.create(
                        customer=customer,
                        meter_number=generate_meter_number(),
                        installation_date=installation_date,
                        meter_type=meter_type,
                        is_active=True
                    )
                    meters_created += 1

                    self.stdout.write(f'  > Customer ID: {customer.id}')
                    self.stdout.write(f'  > Meter: {meter.meter_number}')

                    # Generate readings
                    self.stdout.write('  > Generating readings...')
                    readings_data = generate_readings(
                        meter,
                        start_date,
                        end_date,
                        base_monthly_kwh
                    )

                    # Bulk create readings in batches
                    batch_size = 1000
                    reading_objects = []

                    for reading_dict in readings_data:
                        reading_objects.append(
                            MeterReading(**reading_dict)
                        )

                        if len(reading_objects) >= batch_size:
                            MeterReading.objects.bulk_create(reading_objects)
                            readings_created += len(reading_objects)
                            reading_objects = []
                            self.stdout.write(
                                f'    ... {readings_created:,} readings created',
                                ending='\r'
                            )

                    # Create remaining readings
                    if reading_objects:
                        MeterReading.objects.bulk_create(reading_objects)
                        readings_created += len(reading_objects)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  [OK] Created {len(readings_data):,} readings for {meter.meter_number}'
                        )
                    )

            # Print summary
            print_summary(
                customers_created,
                meters_created,
                readings_created,
                start_date,
                end_date
            )

            self.stdout.write(
                self.style.SUCCESS('\n[OK] Data generation completed successfully!\n')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n[ERROR] Error during data generation: {e}\n')
            )
            raise


