import os
import yfinance as yf
from decimal import Decimal
from typing import Optional
from zakatable import cache

DEFAULT_FX_EXPIRY = 3600  # Cache exchange rates for 1 hour

def get_exchange_rate(source: str, target: str, force_refresh: bool = False) -> Decimal:
    """
    Fetches the currency exchange rate from source currency to target currency.
    E.g. source="EUR", target="USD" returns the rate to convert EUR to USD.
    Uses yfinance currency tickers (e.g., EURUSD=X) and caches rates for 1 hour.
    
    If direct conversion fails, it attempts to route the conversion through USD.
    
    Compliance Reference: Normalizing foreign currency balances using prevailing spot exchange rates
    aligns with the recommendations of AAOIFI Shari'ah Standard No. 35 (Zakah) Section 2/2.
    See E-Standards Portal: https://aaoifi.com/e-standards/?lang=en
    """
    source = source.strip().upper()
    target = target.strip().upper()
    
    if source == target:
        return Decimal("1.0")
        
    cache_key = f"FX_{source}_{target}"
    
    # Check cache first
    if not force_refresh:
        cached = cache.get_cached_data(cache_key, expiry_seconds=DEFAULT_FX_EXPIRY)
        if cached:
            return Decimal(str(cached["data"]["rate"]))
            
    # Try direct conversion ticker (e.g. EURUSD=X)
    ticker_name = f"{source}{target}=X"
    try:
        ticker = yf.Ticker(ticker_name)
        # Fetch current price
        info = ticker.info
        rate = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        
        if rate is not None and rate > 0:
            rate_decimal = Decimal(str(rate))
            # Cache the rate
            cache.set_cached_data(cache_key, {"rate": float(rate_decimal)})
            return rate_decimal
    except Exception as e:
        print(f"Direct FX conversion for {ticker_name} failed: {e}. Attempting USD routing...")
        
    # If direct fails, attempt routing through USD: (source -> USD -> target)
    if source != "USD" and target != "USD":
        try:
            rate_to_usd = get_exchange_rate(source, "USD", force_refresh)
            rate_from_usd = get_exchange_rate("USD", target, force_refresh)
            rate_decimal = rate_to_usd * rate_from_usd
            # Cache the routed rate
            cache.set_cached_data(cache_key, {"rate": float(rate_decimal)})
            return rate_decimal
        except Exception as e:
            raise ValueError(f"Failed to resolve exchange rate from {source} to {target} via USD: {e}")
            
    # Fallbacks if yfinance lacks USD pairs
    # In case USD -> source direct fails, try invert
    if target == "USD":
        try:
            invert_ticker = f"USD{source}=X"
            ticker = yf.Ticker(invert_ticker)
            rate = ticker.info.get("currentPrice") or ticker.info.get("regularMarketPrice")
            if rate is not None and rate > 0:
                rate_decimal = Decimal("1.0") / Decimal(str(rate))
                cache.set_cached_data(cache_key, {"rate": float(rate_decimal)})
                return rate_decimal
        except Exception as e:
            pass
            
    if source == "USD":
        try:
            invert_ticker = f"{target}USD=X"
            ticker = yf.Ticker(invert_ticker)
            rate = ticker.info.get("currentPrice") or ticker.info.get("regularMarketPrice")
            if rate is not None and rate > 0:
                rate_decimal = Decimal("1.0") / Decimal(str(rate))
                cache.set_cached_data(cache_key, {"rate": float(rate_decimal)})
                return rate_decimal
        except Exception as e:
            pass
            
    raise ValueError(f"Exchange rate from {source} to {target} is currently unavailable.")
