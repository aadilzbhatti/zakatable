import pytest
from zakatable import ZakatCalculator

def test_calculator_balance_sheet_portfolio(mock_yfinance):
    calc = ZakatCalculator()
    
    # Define portfolio ( लचीला keys)
    holdings = [
        {"ticker": "AAPL", "shares": 100},           # AAPL (floored to 0 due on balance sheet)
        {"symbol": "BAC", "quantity": 200}           # BAC (has Zakat due on balance sheet)
    ]
    
    res = calc.calculate_portfolio(holdings, use_proxy=False)
    
    # Assert totals
    # AAPL value: 100 * $300 = $30k
    # BAC value: 200 * $50 = $10k
    # Total Market Value = $40k
    assert res["total_market_value"] == 40000.0
    
    # Zakat values
    # AAPL Zakat = 0.0
    # BAC Zakat: BAC shares outstanding is 8B. Net assets = 150B cash + 50B short_term + 120B receivables - 100B liabilities = 220B.
    # BAC Zakatable Asset per Share = 220B / 8B = $27.50.
    # For 200 shares, Zakatable value = 200 * $27.50 = $5,500.00.
    # Lunar Zakat (2.5%) = $5500 * 0.025 = $137.50
    assert res["total_zakatable_value"] == 5500.0
    assert res["total_zakat_due_lunar"] == 137.50
    assert res["method_used"] == "Balance Sheet Method"
    
    # Assert item details
    aapl_item = next(item for item in res["items"] if item["ticker"] == "AAPL")
    assert aapl_item["is_compliant"] is True
    assert aapl_item["zakatable_value"] == 0.0
    assert "liquid asset deficit" in aapl_item["rationale"]
    
    bac_item = next(item for item in res["items"] if item["ticker"] == "BAC")
    assert bac_item["is_compliant"] is False
    assert bac_item["zakatable_value"] == 5500.0
    assert bac_item["zakat_due_lunar"] == 137.50
    assert "Proportionate net liquid assets" in bac_item["rationale"]

def test_calculator_proxy_portfolio(mock_yfinance):
    calc = ZakatCalculator()
    holdings = [
        {"ticker": "AAPL", "shares": 100},
        {"symbol": "BAC", "quantity": 200}
    ]
    
    res = calc.calculate_portfolio(holdings, use_proxy=True)
    
    # Assert proxy totals
    # AAPL proxy zakatable asset = $300 * 0.3 = $90.0. Total for 100 shares = $9,000.0.
    # BAC proxy zakatable asset = $50 * 0.3 = $15.0. Total for 200 shares = $3,000.0.
    # Total Zakatable Value = 9k + 3k = 12k.
    # Lunar Zakat (2.5%) = 12k * 0.025 = $300.00.
    assert res["total_zakatable_value"] == 12000.0
    assert res["total_zakat_due_lunar"] == 300.00
    assert res["method_used"] == "30% Market Cap Proxy"
    
    aapl_item = next(item for item in res["items"] if item["ticker"] == "AAPL")
    assert aapl_item["zakatable_value"] == 9000.0
    assert aapl_item["zakat_due_lunar"] == 225.0
    assert "30% Market Cap Proxy" in aapl_item["rationale"]
