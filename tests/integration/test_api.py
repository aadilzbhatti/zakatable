import pytest

def test_api_config(client):
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert "overrides" in data
    assert data["rules"]["default_standard"] == "aaoifi"

def test_api_screening(client, mock_yfinance):
    response = client.get("/api/v1/screen/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["compliance"]["is_compliant"] is True
    assert data["compliance"]["business_screen"]["is_halal"] is True

def test_api_screening_bank(client, mock_yfinance):
    response = client.get("/api/v1/screen/BAC")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "BAC"
    assert data["compliance"]["is_compliant"] is False
    assert data["compliance"]["business_screen"]["is_halal"] is False

def test_api_batch_screening(client, mock_yfinance):
    payload = {"tickers": ["AAPL", "BAC"]}
    response = client.post("/api/v1/screen/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "AAPL" in data
    assert "BAC" in data
    assert data["AAPL"]["compliance"]["is_compliant"] is True
    assert data["BAC"]["compliance"]["is_compliant"] is False

def test_api_calculate_portfolio(client, mock_yfinance):
    payload = {
        "items": [
            {"ticker": "AAPL", "shares": 100},
            {"ticker": "BAC", "shares": 200}
        ],
        "standard": "aaoifi",
        "use_proxy": False
    }
    response = client.post("/api/v1/calculate-portfolio", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Assert structural fields
    assert "total_market_value" in data
    assert "total_zakatable_value" in data
    assert "total_zakat_due_lunar" in data
    assert "items" in data
    
    # Assert maths
    assert data["total_market_value"] == 40000.0
    assert data["total_zakatable_value"] == 5500.0
    assert data["total_zakat_due_lunar"] == 137.50
    assert len(data["items"]) == 2
    
    # Assert item breakdowns
    aapl_item = next(item for item in data["items"] if item["ticker"] == "AAPL")
    assert aapl_item["zakatable_value"] == 0.0
    assert "liquid asset deficit" in aapl_item["rationale"]
    
    bac_item = next(item for item in data["items"] if item["ticker"] == "BAC")
    assert bac_item["zakatable_value"] == 5500.0
    assert bac_item["zakat_due_lunar"] == 137.50
    assert "Proportionate net liquid assets" in bac_item["rationale"]

def test_api_cache_clear(client):
    response = client.post("/api/v1/cache/clear")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_api_calculate_portfolio_advanced(client, mock_yfinance):
    payload = {
        "settings": {
            "base_currency": "USD",
            "nisab_standard": "gold",
            "calendar_type": "gregorian"
        },
        "assets": {
            "cash": [
                { "amount": 10000.00, "currency": "USD" }
            ],
            "precious_metals": [
                { "metal": "gold", "weight": 20.0, "purity": 22.0, "unit": "grams" }
            ]
        },
        "liabilities": {
            "short_term_debts": [
                { "amount": 2000.00, "currency": "USD", "type": "credit_card" }
            ]
        }
    }
    response = client.post("/api/v1/calculate-portfolio", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Assert structural fields of the new schema
    assert "settings" in data
    assert data["settings"]["base_currency"] == "USD"
    assert data["settings"]["calendar_type"] == "gregorian"
    assert "zakat_rate" in data["settings"]
    assert "nisab_threshold_used" in data
    assert "nisab_value_base" in data
    assert "is_nisab_met" in data
    assert "gross_zakatable_assets" in data
    assert "allowed_liabilities" in data
    assert "net_zakatable_wealth" in data
    assert "total_zakat_due" in data
    assert "breakdown" in data
    
    # Assert maths
    assert data["gross_zakatable_assets"] == 11375.00
    assert data["allowed_liabilities"] == 2000.00
    assert data["net_zakatable_wealth"] == 9375.00
    assert data["is_nisab_met"] is True
    assert data["total_zakat_due"] == round(9375.00 * 0.02577, 2)
