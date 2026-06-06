import pytest
import pandas as pd
from zakatable import screener

def test_load_yaml_config():
    # Verify that rules config loads and default settings resolve
    config = screener.load_yaml_config("business_rules.yaml")
    assert "compliance_standards" in config
    assert "haram_sectors" in config
    assert config["default_standard"] == "aaoifi"

def test_get_row_value_fallbacks():
    # Construct a test DataFrame with varying column configurations
    df = pd.DataFrame(
        {"2025-12-31": [100.0, 200.0]},
        index=["Cash And Cash Equivalents", "Net Receivables"]
    )
    
    # Test match with exact casing
    val1 = screener.get_row_value(df, ["Cash And Cash Equivalents"])
    assert val1 == 100.0
    
    # Test match with lowercase/spaces variance
    val2 = screener.get_row_value(df, ["net receivables", "Receivables"])
    assert val2 == 200.0
    
    # Test fallback to default if not found
    val3 = screener.get_row_value(df, ["Non Existent Field"], default=-9.9)
    assert val3 == -9.9

def test_compliance_screening_banks(mock_financial_data):
    # Bank of America (BAC) has non-halal sector/industry
    bac_data = mock_financial_data["BAC"]
    comp = screener.perform_compliance_screening(bac_data, "aaoifi")
    
    assert comp["is_compliant"] is False
    assert comp["business_screen"]["is_halal"] is False
    assert "banking" in comp["business_screen"]["reason"].lower()

def test_compliance_screening_ratios(mock_financial_data):
    # Apple (AAPL) has manual override to halal business activity
    aapl_data = mock_financial_data["AAPL"]
    comp = screener.perform_compliance_screening(aapl_data, "aaoifi", denominator_override="market_cap")
    
    assert comp["business_screen"]["is_halal"] is True
    assert comp["financial_screens"]["passed_all"] is True
    assert comp["is_compliant"] is True
    
    # Verify ratio maths
    # Debt ratio = 90B debt / 4500B market cap = 0.02 (2.0%)
    assert comp["financial_screens"]["debt"]["ratio"] == 0.02
    assert comp["financial_screens"]["debt"]["passed"] is True

def test_zakat_metrics_positive_and_floored(mock_financial_data):
    # Test Apple (has liquid asset deficit: current assets 115B < current liab 145B)
    aapl_data = mock_financial_data["AAPL"]
    zakat_aapl = screener.calculate_zakat_metrics(aapl_data)
    
    # Net assets is negative (-30B)
    assert zakat_aapl["balance_sheet_method"]["net_zakatable_assets_total"] == -30000000000.0
    # Floored to 0.0
    assert zakat_aapl["balance_sheet_method"]["net_zakatable_assets_floored"] == 0.0
    assert zakat_aapl["balance_sheet_method"]["zakatable_asset_per_share"] == 0.0
    assert zakat_aapl["balance_sheet_method"]["zakat_due_per_share_lunar"] == 0.0
    
    # Proxy method calculates 30% of share price ($300 * 0.30 = $90 per share)
    assert zakat_aapl["proxy_method_30pct"]["zakatable_asset_per_share"] == 90.0
    # Zakat due (Lunar: 90 * 0.025 = 2.25)
    assert zakat_aapl["proxy_method_30pct"]["zakat_due_per_share_lunar"] == 2.25

def test_zakat_metrics_positive():
    # Construct a dummy company with positive net assets
    dummy_data = {
        "symbol": "DUMY",
        "company_name": "Dummy Corp",
        "price": 100.0,
        "shares_outstanding": 1000.0,
        "cash_equivalents": 20000.0,
        "short_term_investments": 10000.0,
        "accounts_receivable": 10000.0,
        "inventory": 10000.0,
        "total_current_liabilities": 20000.0,
    }
    
    # Zakatable assets = 20k + 10k + 10k + 10k = 50k
    # Net Zakatable assets = 50k - 20k current liabilities = 30k
    # Shares = 1000. Zakatable Asset per Share = 30k / 1000 = $30.00
    zakat_dumy = screener.calculate_zakat_metrics(dummy_data)
    bs = zakat_dumy["balance_sheet_method"]
    
    assert bs["net_zakatable_assets_total"] == 30000.0
    assert bs["zakatable_asset_per_share"] == 30.0
    
    # Lunar Zakat due = $30.00 * 2.5% = $0.75
    assert bs["zakat_due_per_share_lunar"] == 0.75
    # Solar Zakat due = $30.00 * 2.577% = $0.7731
    assert round(bs["zakat_due_per_share_solar"], 4) == 0.7731
