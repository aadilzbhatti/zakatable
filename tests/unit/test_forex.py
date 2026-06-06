import pytest
from decimal import Decimal
from zakatable.forex import get_exchange_rate

def test_get_exchange_rate_same():
    rate = get_exchange_rate("USD", "USD")
    assert rate == Decimal("1.0")
    
    rate = get_exchange_rate("EUR", "EUR")
    assert rate == Decimal("1.0")

def test_get_exchange_rate_direct(mock_yfinance):
    # EUR to USD direct
    rate = get_exchange_rate("EUR", "USD", force_refresh=True)
    assert rate == Decimal("1.08")
    
    # USD to EUR direct
    rate = get_exchange_rate("USD", "EUR", force_refresh=True)
    assert rate == Decimal("0.92")

def test_get_exchange_rate_routed(mock_yfinance):
    # GBP to EUR (routes GBP -> USD -> EUR)
    # GBP -> USD = 1.27
    # USD -> EUR = 0.92
    # GBP -> EUR = 1.27 * 0.92 = 1.1684
    rate = get_exchange_rate("GBP", "EUR", force_refresh=True)
    assert rate == Decimal("1.27") * Decimal("0.92")

def test_get_exchange_rate_invalid(mock_yfinance):
    # Try a completely invalid currency pair
    with pytest.raises(ValueError, match="Exchange rate from XYZ to USD is currently unavailable"):
        get_exchange_rate("XYZ", "ABC", force_refresh=True)
