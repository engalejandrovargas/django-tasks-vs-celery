"""
Smart meter data generator for testing and demonstration.

Generates realistic meter readings with Japanese customer data,
including daily patterns, seasonal variations, and different customer types.
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal
from faker import Faker

# Initialize Faker with Japanese locale
fake = Faker('ja_JP')
Faker.seed(42)  # Reproducible data
random.seed(42)


# Japanese prefectures
PREFECTURES = [
    '東京都', '大阪府', '神奈川県', '愛知県', '埼玉県',
    '千葉県', '兵庫県', '北海道', '福岡県', '静岡県'
]


def generate_japanese_customer():
    """Generate a customer with Japanese address format."""
    prefecture = random.choice(PREFECTURES)

    return {
        'name': fake.name(),
        'postal_code': fake.postcode(),
        'prefecture': prefecture,
        'city': fake.city(),
        'address': fake.address().replace('\n', ' '),
    }


def generate_meter_number():
    """Generate a unique meter number."""
    prefix = random.choice(['TK', 'OS', 'FK'])  # Tokyo, Osaka, Fukuoka
    number = random.randint(100000, 999999)
    return f'{prefix}-{number}'


def calculate_reading(meter_type, timestamp, base_monthly_kwh):
    """
    Calculate realistic energy reading based on time and meter type.

    Args:
        meter_type: 'residential', 'commercial', or 'industrial'
        timestamp: datetime of the reading
        base_monthly_kwh: base monthly consumption in kWh

    Returns:
        Decimal: kWh consumption for this 30-minute period
    """
    hour = timestamp.hour
    month = timestamp.month
    is_weekend = timestamp.weekday() >= 5

    # Base usage per 30-minute interval (monthly / 48 readings/day / ~30 days)
    base_interval = base_monthly_kwh / (48 * 30)

    # Time of day factor
    if meter_type == 'residential':
        if 7 <= hour <= 9 or 18 <= hour <= 22:  # Morning and evening peaks
            time_factor = 2.5
        elif 10 <= hour <= 17:  # Day hours (lower for residential)
            time_factor = 0.8
        else:  # Night hours
            time_factor = 0.3

        # Weekend factor (higher at home)
        weekend_factor = 1.2 if is_weekend else 1.0

    elif meter_type == 'commercial':
        if 9 <= hour <= 18:  # Business hours
            time_factor = 2.0
        elif 7 <= hour <= 9 or 18 <= hour <= 20:  # Opening/closing
            time_factor = 1.2
        else:  # Closed hours
            time_factor = 0.2

        # Weekend factor (closed or reduced hours)
        weekend_factor = 0.3 if is_weekend else 1.0

    else:  # industrial
        if 8 <= hour <= 17:  # Production hours
            time_factor = 2.0
        elif 6 <= hour <= 8 or 17 <= hour <= 19:  # Shift changes
            time_factor = 1.5
        else:  # Night shift (reduced)
            time_factor = 0.7

        # Weekend factor (reduced production)
        weekend_factor = 0.5 if is_weekend else 1.0

    # Seasonal factor
    if month in [6, 7, 8]:  # Summer (air conditioning)
        seasonal_factor = 1.6
    elif month in [12, 1, 2]:  # Winter (heating)
        seasonal_factor = 1.5
    elif month in [3, 4, 5, 9, 10, 11]:  # Spring/Fall
        seasonal_factor = 1.0
    else:
        seasonal_factor = 1.0

    # Random noise for realism (±20%)
    noise = random.uniform(0.8, 1.2)

    # Calculate final kWh
    kwh = base_interval * time_factor * weekend_factor * seasonal_factor * noise

    # Ensure minimum consumption
    kwh = max(kwh, 0.01)

    return Decimal(str(round(kwh, 3)))


def generate_readings(meter, start_date, end_date, base_monthly_kwh):
    """
    Generate 30-minute interval readings for a meter.

    Args:
        meter: SmartMeter instance
        start_date: Start date for readings
        end_date: End date for readings
        base_monthly_kwh: Base monthly consumption

    Returns:
        list: List of reading dictionaries
    """
    readings = []
    current_time = datetime.combine(start_date, datetime.min.time())
    end_time = datetime.combine(end_date, datetime.max.time())

    # 30-minute intervals
    interval = timedelta(minutes=30)

    while current_time <= end_time:
        kwh = calculate_reading(
            meter.meter_type,
            current_time,
            base_monthly_kwh
        )

        readings.append({
            'meter': meter,
            'timestamp': current_time,
            'kwh': kwh
        })

        current_time += interval

    return readings


def get_customer_profiles():
    """
    Define customer profiles with typical consumption patterns.

    Returns:
        list: List of (profile_name, meter_type, base_monthly_kwh)
    """
    return [
        ('single_apartment_tokyo', 'residential', 200),     # Single person, small apartment
        ('family_house_osaka', 'residential', 450),         # Family of 4, house
        ('elderly_couple_fukuoka', 'residential', 180),     # Elderly couple, low usage
        ('large_family_tokyo', 'residential', 600),         # Large family, high usage
        ('small_office_tokyo', 'commercial', 800),          # Small office
        ('restaurant_osaka', 'commercial', 1200),           # Restaurant (high usage)
        ('retail_store_fukuoka', 'commercial', 900),        # Retail store
        ('small_factory_osaka', 'industrial', 3000),        # Small manufacturing
    ]


def print_summary(customers_count, meters_count, readings_count, start_date, end_date):
    """Print generation summary."""
    days = (end_date - start_date).days + 1
    print("\n" + "="*60)
    print("Data Generation Summary")
    print("="*60)
    print(f"Customers created:  {customers_count}")
    print(f"Meters installed:   {meters_count}")
    print(f"Readings generated: {readings_count:,}")
    print(f"Date range:         {start_date} to {end_date}")
    print(f"Duration:           {days} days")
    print(f"Readings per meter: {readings_count // meters_count:,}")
    print("="*60)
    print("\nCustomer types:")
    profiles = get_customer_profiles()
    for profile_name, meter_type, monthly_kwh in profiles:
        print(f"  - {profile_name}: {meter_type} ({monthly_kwh} kWh/month)")
    print("="*60)
