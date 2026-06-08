import pytest
from decimal import Decimal
from zakatable import ZakatCalculator

def test_calculate_portfolio_advanced_balance_sheet(mock_yfinance):
    calc = ZakatCalculator()
    
    # Gold spot price: GC=F is 2332.76 USD/oz => 2332.76 / 31.1034768 = $75.0000/g
    # Silver spot price: SI=F is 29.55 USD/oz => 29.55 / 31.1034768 = $0.950055/g
    
    payload = {
        "settings": {
            "base_currency": "USD",
            "nisab_standard": "gold",
            "calendar_type": "gregorian"
        },
        "assets": {
            "cash": [
                { "amount": 10000.00, "currency": "USD" },
                { "amount": 5000.00, "currency": "EUR" } # 5000 * 1.08 = 5400 USD
            ],
            "precious_metals": [
                # 20g 22k Gold => 20 * (22/24) = 18.3333g pure gold. Value = 18.3333 * 75 = $1,375.00
                { "metal": "gold", "weight": 20.0, "purity": 22.0, "unit": "grams" },
                # 10oz 24k Silver => 10 * 31.1034768 = 311.034768g pure silver. Value = 311.034768 * 0.950055 = $295.50
                { "metal": "silver", "weight": 10.0, "purity": 24.0, "unit": "ounces" }
            ],
            "business_inventory": [
                { "value": 5000.00, "currency": "USD" }
            ],
            "real_estate": [
                { "value": 500000.00, "currency": "USD", "type": "primary" }, # Exempt
                { "value": 300000.00, "currency": "USD", "type": "rental" },  # Exempt
                { "value": 150000.00, "currency": "USD", "type": "flip" }     # 100% Taxed
            ],
            "stocks": [
                # AAPL holding => balance sheet deficit => floored to 0.0 under pure balance sheet
                { "ticker": "AAPL", "shares": 100.0, "intent": "holding" },
                # BAC trading => 100% market value
                # 200 shares * 50 = $10,000.00
                { "ticker": "BAC", "shares": 200.0, "intent": "trading" }
            ]
        },
        "liabilities": {
            "short_term_debts": [
                { "amount": 2000.00, "currency": "USD", "type": "credit_card" },
                { "amount": 500.00, "currency": "EUR", "type": "utility" } # 500 * 1.08 = 540 USD
            ]
        }
    }
    
    res = calc.calculate_portfolio(
        settings=payload["settings"],
        assets=payload["assets"],
        liabilities=payload["liabilities"],
        force_refresh=True
    )
    
    # Calculations:
    # Cash USD: 10000.00
    # Cash EUR: 5400.00
    # Gold: 1375.00
    # Silver: 295.50
    # Inventory: 5000.00
    # RE Flip: 150000.00
    # AAPL (floored BS): 0.00
    # BAC (trading): 10000.00
    # Total Gross = 10000 + 5400 + 1375 + 295.50 + 5000 + 150000 + 0 + 10000 = $182,070.50
    assert res["gross_zakatable_assets"] == 182070.50
    
    # Liabilities:
    # credit_card: 2000.00
    # utility: 540.00
    # Total = $2,540.00
    assert res["allowed_liabilities"] == 2540.00
    
    # Net: 182070.50 - 2540.00 = $179,530.50
    assert res["net_zakatable_wealth"] == 179530.50
    
    # Zakat due: 179530.50 * 0.02577 = 4626.50
    assert res["total_zakat_due"] == 4626.50

def test_calculate_portfolio_advanced_proxy(mock_yfinance):
    calc = ZakatCalculator()
    
    payload = {
        "settings": {
            "base_currency": "USD",
            "nisab_standard": "gold",
            "calendar_type": "gregorian",
            "use_proxy": True # Use 30% proxy
        },
        "assets": {
            "cash": [
                { "amount": 10000.00, "currency": "USD" }
            ],
            "stocks": [
                # AAPL holding => 30% proxy => 100 * 300 * 0.3 = $9,000.00
                { "ticker": "AAPL", "shares": 100.0, "intent": "holding" }
            ]
        }
    }
    
    res = calc.calculate_portfolio(
        settings=payload["settings"],
        assets=payload["assets"],
        force_refresh=True
    )
    
    # Cash: 10000.00
    # AAPL: 9000.00
    # Total Gross = $19,000.00
    assert res["gross_zakatable_assets"] == 19000.00
    assert res["net_zakatable_wealth"] == 19000.00
    assert res["total_zakat_due"] == round(19000.00 * 0.02577, 2)

def test_nisab_not_met(mock_yfinance):
    calc = ZakatCalculator()
    
    payload = {
        "settings": {
            "base_currency": "USD",
            "nisab_standard": "gold",
            "calendar_type": "gregorian"
        },
        "assets": {
            "cash": [
                { "amount": 500.00, "currency": "USD" }
            ],
            "stocks": [
                { "ticker": "AAPL", "shares": 1.0, "intent": "holding" }
            ]
        }
    }
    
    res = calc.calculate_portfolio(
        settings=payload["settings"],
        assets=payload["assets"],
        force_refresh=True
    )
    
    assert res["is_nisab_met"] is False
    assert res["total_zakat_due"] == 0.0
    for item in res["breakdown"]:
        assert item["zakat_due"] == 0.0

def test_nisab_not_met_backward_compatibility(mock_yfinance):
    calc = ZakatCalculator()
    
    # Simple stocks holdings below Nisab (gold Nisab value is $6561.00 USD)
    holdings = [
        {"ticker": "AAPL", "shares": 1} # 1 share AAPL = $300.00, below gold Nisab
    ]
    
    res = calc.calculate_portfolio(
        holdings=holdings,
        use_proxy=True,
        settings={
            "base_currency": "USD",
            "nisab_standard": "gold",
            "calendar_type": "gregorian"
        },
        force_refresh=True
    )
    
    assert res["is_nisab_met"] is False
    assert res["total_zakat_due"] == 0.0
    assert res["total_zakat_due_lunar"] == 0.0
    assert res["total_zakat_due_solar"] == 0.0
    for item in res["items"]:
        assert item["zakat_due_lunar"] == 0.0
        assert item["zakat_due_solar"] == 0.0

def test_receivables_and_retirement_accounts(mock_yfinance):
    calc = ZakatCalculator()
    
    payload = {
        "settings": {
            "base_currency": "USD",
            "nisab_standard": "silver",
            "calendar_type": "gregorian"
        },
        "assets": {
            "cash": [
                { "amount": 10000.00, "currency": "USD" }
            ],
            "receivables": [
                { "amount": 3000.00, "currency": "USD", "type": "good" },
                { "amount": 5000.00, "currency": "USD", "type": "bad" }
            ],
            "retirement_accounts": [
                { "balance": 50000.00, "currency": "USD", "is_accessible": True, "tax_rate": 0.20, "penalty_rate": 0.10 },
                { "balance": 100000.00, "currency": "USD", "is_accessible": False }
            ]
        }
    }
    
    res = calc.calculate_portfolio(
        settings=payload["settings"],
        assets=payload["assets"],
        force_refresh=True
    )
    
    # Assertions:
    # Cash: 10000.00
    # Good receivable: 3000.00
    # Bad receivable: 0.00
    # Accessible retirement: 50000.00 * (1 - 0.20 - 0.10) = 35000.00
    # Locked retirement: 0.00
    # Total Gross assets = 10000 + 3000 + 35000 = $48,000.00
    assert res["gross_zakatable_assets"] == 48000.00
    assert res["allowed_liabilities"] == 0.0
    assert res["net_zakatable_wealth"] == 48000.00
    assert res["is_nisab_met"] is True
    
    # 48000.00 * 0.02577 = 1236.96
    assert res["total_zakat_due"] == 1236.96
    
    # Check breakdown items
    rec_good = next(item for item in res["breakdown"] if "Good" in item["label"])
    assert rec_good["zakatable_value"] == 3000.00
    
    rec_bad = next(item for item in res["breakdown"] if "Bad" in item["label"])
    assert rec_bad["zakatable_value"] == 0.0
    
    ret_acc = next(item for item in res["breakdown"] if item["asset_class"] == "retirement_accounts" and item["zakatable_value"] > 0)
    assert ret_acc["zakatable_value"] == 35000.00
    
    ret_locked = next(item for item in res["breakdown"] if item["asset_class"] == "retirement_accounts" and item["zakatable_value"] == 0)
    assert ret_locked["zakatable_value"] == 0.0

