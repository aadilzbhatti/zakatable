from decimal import Decimal
from zakatable import cache
from zakatable.forex import get_exchange_rate
from zakatable.session import get_yf_ticker

DEFAULT_COMMODITY_EXPIRY = 3600  # Cache spot prices for 1 hour
GRAMS_PER_TROY_ONCE = Decimal("31.1034768")

# Scholarly Nisab Threshold weights:
# Gold Nisab = 87.48 grams of pure gold (equivalent to 20 mithqals / 20 dinars)
# Hadith: Sunan Abu Dawud 1572 - https://sunnah.com/abudawud:1572
# Silver Nisab = 612.36 grams of pure silver (equivalent to 200 dirhams / 5 awquq)
# Hadith: Sahih al-Bukhari 1447 - https://sunnah.com/bukhari:1447
# Detailed guide: NZF Gold & Silver Guide: https://nzf.org.uk/knowledge/zakat-on-gold-and-silver/
NISAB_WEIGHTS = {
    "gold": Decimal("87.48"),
    "silver": Decimal("612.36")
}

def get_commodity_spot_price(metal: str, force_refresh: bool = False) -> Decimal:
    """
    Fetches the live commodity spot price per gram in USD.
    Supports metal="gold" (GC=F ticker) and metal="silver" (SI=F ticker).
    """
    metal = metal.strip().lower()
    if metal not in ("gold", "silver"):
        raise ValueError("Metal must be 'gold' or 'silver'")
        
    cache_key = f"COMMODITY_{metal}_USD"
    
    # Check cache first
    if not force_refresh:
        cached = cache.get_cached_data(cache_key, expiry_seconds=DEFAULT_COMMODITY_EXPIRY)
        if cached:
            return Decimal(str(cached["data"]["price_per_gram"]))
            
    ticker_name = "GC=F" if metal == "gold" else "SI=F"
    try:
        ticker = get_yf_ticker(ticker_name)
        info = ticker.info
        
        # Spot futures price per troy ounce
        price_per_ounce = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        
        if price_per_ounce is None or price_per_ounce <= 0:
            # Fallback historical check
            hist = ticker.history(period="1d")
            if not hist.empty:
                price_per_ounce = hist["Close"].iloc[-1]
                
        if price_per_ounce is None or price_per_ounce <= 0:
            raise ValueError(f"No pricing data found for ticker {ticker_name}")
            
        # Convert troy ounce to gram price
        price_per_gram = Decimal(str(price_per_ounce)) / GRAMS_PER_TROY_ONCE
        
        # Cache the result
        cache.set_cached_data(cache_key, {"price_per_gram": float(price_per_gram)})
        return price_per_gram
        
    except Exception as e:
        # Provide hardcoded fallback estimates if Yahoo is down (approximate spot prices in USD/gram)
        # Gold ~ $75/g, Silver ~ $0.95/g
        fallbacks = {"gold": Decimal("75.00"), "silver": Decimal("0.95")}
        print(f"Warning: Commodities oracle failed for {metal}: {e}. Using conservative fallback.")
        return fallbacks.get(metal, Decimal("0.0"))

def get_nisab_threshold(metal: str, currency: str = "USD", force_refresh: bool = False) -> Decimal:
    """
    Calculates the Nisab threshold in the user's base currency.
    Formula: weight (grams) * USD_price_per_gram * FX_rate(USD -> base_currency)
    """
    metal = metal.strip().lower()
    currency = currency.strip().upper()
    
    if metal not in NISAB_WEIGHTS:
        raise ValueError("Metal must be 'gold' or 'silver'")
        
    weight = NISAB_WEIGHTS[metal]
    price_per_gram_usd = get_commodity_spot_price(metal, force_refresh)
    
    # Convert USD price to base currency
    fx_rate = get_exchange_rate("USD", currency, force_refresh)
    price_per_gram_base = price_per_gram_usd * fx_rate
    
    return weight * price_per_gram_base
