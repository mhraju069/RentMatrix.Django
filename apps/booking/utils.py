from apps.property.models import Property
from django.db.models import Avg
from django.utils import timezone
from decimal import Decimal
import datetime

def _month_matches(current_date, vacation_months):
    """
    Checks if current_date's month matches any month in vacation_months list,
    handling formats like ['JUL', 'JULY', 'July', 'jul', 'july', 7, '07'].
    """
    if not vacation_months:
        return False
    if isinstance(vacation_months, str):
        vacation_months = [vacation_months]

    stored = {str(m).strip().upper() for m in vacation_months}

    short_name = current_date.strftime("%b").upper()   # "JUL"
    full_name = current_date.strftime("%B").upper()    # "JULY"
    month_num = str(current_date.month)                # "7"
    month_num_padded = f"{current_date.month:02d}"     # "07"

    month_variants = {short_name, full_name, month_num, month_num_padded}
    return bool(stored.intersection(month_variants))


def _weekend_matches(current_date, weekend_days):
    """
    Checks if current_date's weekday matches any day in weekend_days list,
    handling formats like ['SAT', 'SATURDAY', 'Saturday', 'sat', 'saturday'].
    """
    if not weekend_days:
        return False
    if isinstance(weekend_days, str):
        weekend_days = [weekend_days]

    stored = {str(d).strip().upper() for d in weekend_days}

    short_name = current_date.strftime("%a").upper()   # "SAT"
    full_name = current_date.strftime("%A").upper()    # "SATURDAY"

    day_variants = {short_name, full_name}
    return bool(stored.intersection(day_variants))


def parse_addon_ids(raw_value):
    """
    Safely parses selected_addon_ids from any format:
    - String with JSON array: "[79, 80]" or "['79', '80']"
    - Comma-separated string: "79, 80"
    - List/Tuple: [79, 80] or ['79', '80']
    - Single ID: 79 or "79"
    """
    if not raw_value:
        return []
    if isinstance(raw_value, (list, tuple)):
        result = []
        for item in raw_value:
            result.extend(parse_addon_ids(item))
        return list(dict.fromkeys(result))
    if isinstance(raw_value, str):
        cleaned = raw_value.strip().lstrip('[').rstrip(']')
        if not cleaned:
            return []
        parts = []
        for item in cleaned.split(','):
            item_clean = item.strip().strip('"').strip("'")
            if item_clean:
                parts.append(item_clean)
        return list(dict.fromkeys(parts))
    return [str(raw_value)]



def get_final_discount_price_for_booking(property_obj_or_id, price_type="monthly",selected_addon_ids=None,start_date=None,end_date=None):
    if isinstance(property_obj_or_id, Property):
        property_obj = property_obj_or_id
    else:
        property_obj = Property.objects.get(id=property_obj_or_id)

    if price_type=="monthly":
        base_price = property_obj.price_monthly or 0
    else:
        base_price = property_obj.price_daily or 0
    total_price = Decimal(str(base_price))

    breakdown = {
        "base_price": float(base_price),
        "other_charges": [],
        "other_charges_total": 0.0,
        "add_ons": [],
        "add_ons_total": 0.0,
        "vacation_surcharge": 0.0,
        "weekend_surcharge": 0.0,
        "discount_amount": 0.0,
        "total_before_discount": 0.0,
        "final_unit_price": 0.0
    }

    # 1. Other Charges
    for oc in property_obj.other_charges.all():
        if oc.price:
            charge = (Decimal(str(base_price)) * Decimal(str(oc.price)) / Decimal("100"))
            total_price += charge
            breakdown["other_charges"].append({"name": oc.name, "amount": float(charge)})
            breakdown["other_charges_total"] += float(charge)

    # 2. Add-ons prices (only added if the user selects them)
    if selected_addon_ids:
        selected_ids_str = parse_addon_ids(selected_addon_ids)
        for addon in property_obj.add_ons_prices.all():
            if addon.price and str(addon.id) in selected_ids_str:
                charge = (Decimal(str(base_price)) * Decimal(str(addon.price)) / Decimal("100"))
                total_price += charge
                breakdown["add_ons"].append({"name": addon.service, "amount": float(charge)})
                breakdown["add_ons_total"] += float(charge)

    # Check if dates overlap with vacations or weekends
    has_vacation = False
    has_weekend = False

    if start_date and end_date:
        if isinstance(start_date, str):
            try:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                start_date = timezone.now().date()
        if isinstance(end_date, str):
            try:
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                end_date = timezone.now().date()

        d1, d2 = min(start_date, end_date), max(start_date, end_date)
        current_date = d1
        while current_date <= d2:
            if hasattr(property_obj, 'vacations') and property_obj.vacations and property_obj.vacations.month:
                if _month_matches(current_date, property_obj.vacations.month):
                    has_vacation = True
            if hasattr(property_obj, 'weekend_dates') and property_obj.weekend_dates and property_obj.weekend_dates.weekend:
                if _weekend_matches(current_date, property_obj.weekend_dates.weekend):
                    has_weekend = True

            current_date += datetime.timedelta(days=1)
    else:
        current_date = timezone.now().date()
        if hasattr(property_obj, 'vacations') and property_obj.vacations and property_obj.vacations.month:
            if _month_matches(current_date, property_obj.vacations.month):
                has_vacation = True
        if hasattr(property_obj, 'weekend_dates') and property_obj.weekend_dates and property_obj.weekend_dates.weekend:
            if _weekend_matches(current_date, property_obj.weekend_dates.weekend):
                has_weekend = True

    # 3. Vacations prices
    if has_vacation and hasattr(property_obj, 'vacations') and property_obj.vacations and property_obj.vacations.price:
        charge = (Decimal(str(base_price)) * Decimal(str(property_obj.vacations.price)) / Decimal("100"))
        total_price += charge
        breakdown["vacation_surcharge"] = float(charge)

    # 4. Weekend prices
    if price_type == "daily" and has_weekend and hasattr(property_obj, 'weekend_dates') and property_obj.weekend_dates and property_obj.weekend_dates.price:
        charge = (Decimal(str(base_price)) * Decimal(str(property_obj.weekend_dates.price)) / Decimal("100"))
        total_price += charge
        breakdown["weekend_surcharge"] = float(charge)

    # 5. Rating surcharge — applied if avg rating >= owner-defined threshold
    rating_surcharge_amount = Decimal("0.0")
    if property_obj.rating_threshold and property_obj.rating_surcharge_percent:
        avg_rating_result = property_obj.reviews.aggregate(avg=Avg("rating"))
        avg_rating = avg_rating_result.get("avg") or 0
        if avg_rating and Decimal(str(avg_rating)) >= Decimal(str(property_obj.rating_threshold)):
            rating_surcharge_amount = (
                Decimal(str(base_price))
                * Decimal(str(property_obj.rating_surcharge_percent))
                / Decimal("100")
            )
            total_price += rating_surcharge_amount

    breakdown["rating_surcharge"] = float(rating_surcharge_amount)
    breakdown["total_before_discount"] = float(total_price)

    # 6. Finally apply discount
    discount = property_obj.discount or 0
    discount_amount = (Decimal(str(base_price)) * Decimal(str(discount)) / Decimal("100"))
    total_price -= discount_amount
    breakdown["discount_amount"] = float(discount_amount)

    # Ensure price doesn't go below 0
    if total_price < 0:
        total_price = Decimal("0.0")

    breakdown["final_unit_price"] = float(total_price)
    
    return breakdown
