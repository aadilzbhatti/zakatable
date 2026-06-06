import pytest
from decimal import Decimal
from zakatable.commodities import (
    get_commodity_spot_price,
    get_nisab_threshold,
    NISAB_WEIGHTS,
    GRAMS_PER_TROY_ONCE
)

def test_get_commodity_spot_price_gold(mock_yfinance):
    # GC=F mock is 2332.76 per troy ounce
    price_gold = get_commodity_spot_price("gold", force_refresh=True)
    expected_gold_g = Decimal("2332.76") / GRAMS_PER_TROY_ONCE
    assert price_gold == expected_gold_g

def test_get_commodity_spot_price_silver(mock_yfinance):
    # SI=F mock is 29.55 per troy ounce
    price_silver = get_commodity_spot_price("silver", force_refresh=True)
    expected_silver_g = Decimal("29.55") / GRAMS_PER_TROY_ONCE
    assert price_silver == expected_silver_g

def test_get_commodity_spot_price_invalid():
    with pytest.raises(ValueError, match="Metal must be 'gold' or 'silver'"):
        get_commodity_spot_price("platinum")

def test_get_nisab_threshold_usd(mock_yfinance):
    # Gold weight is 87.48g
    gold_nisab = get_nisab_threshold("gold", "USD", force_refresh=True)
    gold_g = Decimal("2332.76") / GRAMS_PER_TROY_ONCE
    assert gold_nisab == Decimal("87.48") * gold_g

    # Silver weight is 612.36g
    silver_nisab = get_nisab_threshold("silver", "USD", force_refresh=True)
    silver_g = Decimal("29.55") / GRAMS_PER_TROY_ONCE
    assert silver_nisab == Decimal("612.36") * silver_g

def test_get_nisab_threshold_eur(mock_yfinance):
    # EURUSD=X rate in mock is 1.08. But we convert USD -> EUR using USDEUR=X which is 0.92
    # So gold spot price in EUR = gold_g_usd * 0.92
    gold_nisab_eur = get_nisab_threshold("gold", "EUR", force_refresh=True)
    gold_g_usd = Decimal("2332.76") / GRAMS_PER_TROY_ONCE
    gold_g_eur = gold_g_usd * Decimal("0.92")
    assert gold_nisab_eur == Decimal("87.48") * gold_g_eur
