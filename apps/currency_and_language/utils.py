import urllib.request
import json
from decimal import Decimal
from apps.currency_and_language.models import Currency, UserPreference

def get_user_currency_and_rate(request):
    if request and request.user and request.user.is_authenticated:
        try:
            pref = UserPreference.objects.select_related('currency').get(user=request.user)
            if pref.currency:
                return pref.currency.code, pref.currency.symbol, float(pref.currency.exchange_rate)
        except Exception:
            pass
            
    # Fallback to checking Accept-Language / region / headers if needed, or default USD
    # Let's keep it simple: if not authenticated or no preference, default to USD.
    return "USD", "$", 1.0

def update_exchange_rates():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data and data.get("result") == "success":
                rates = data.get("rates", {})
                # Update all currencies in database with their fetched rate
                for code, rate in rates.items():
                    Currency.objects.filter(code=code.upper()).update(
                        exchange_rate=Decimal(str(rate))
                    )
                return True
    except Exception as e:
        print("Failed to update exchange rates:", str(e))
    return False
