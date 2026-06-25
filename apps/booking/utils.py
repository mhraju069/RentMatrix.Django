from apps.property.models import Property
from django.db.models import Avg
from django.utils import timezone
from decimal import Decimal
import datetime

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
            breakdown["other_charges"].append({"name": oc.name, "amount": float(charge), "percentage": float(oc.price)})
            breakdown["other_charges_total"] += float(charge)

    # 2. Add-ons prices (only added if the user selects them)
    if selected_addon_ids:
        # Convert all to strings for safe comparison
        selected_ids_str = [str(i) for i in selected_addon_ids]
        for addon in property_obj.add_ons_prices.all():
            if addon.price and str(addon.id) in selected_ids_str:
                charge = (Decimal(str(base_price)) * Decimal(str(addon.price)) / Decimal("100"))
                total_price += charge
                breakdown["add_ons"].append({"name": addon.service, "amount": float(charge), "percentage": float(addon.price)})
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
                
        current_date = start_date
        while current_date <= end_date:
            month_str = current_date.strftime("%b").upper()
            day_str = current_date.strftime("%a").upper()[0:3]
            
            if hasattr(property_obj, 'vacations') and property_obj.vacations and month_str in property_obj.vacations.month:
                has_vacation = True
            if hasattr(property_obj, 'weekend_dates') and property_obj.weekend_dates and day_str in property_obj.weekend_dates.weekend:
                has_weekend = True
                
            current_date += datetime.timedelta(days=1)
    else:
        current_date = timezone.now()
        month_str = current_date.strftime("%b").upper()
        day_str = current_date.strftime("%a").upper()[0:3]
        if hasattr(property_obj, 'vacations') and property_obj.vacations and month_str in property_obj.vacations.month:
            has_vacation = True
        if hasattr(property_obj, 'weekend_dates') and property_obj.weekend_dates and day_str in property_obj.weekend_dates.weekend:
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

    breakdown["total_before_discount"] = float(total_price)

    # 5. Finally apply discount
    discount = property_obj.discount or 0
    discount_amount = (Decimal(str(base_price)) * Decimal(str(discount)) / Decimal("100"))
    total_price -= discount_amount
    breakdown["discount_amount"] = float(discount_amount)

    # Ensure price doesn't go below 0
    if total_price < 0:
        total_price = Decimal("0.0")

    breakdown["final_unit_price"] = float(total_price)
    
    return breakdown
