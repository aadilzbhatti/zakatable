import pytest
import os
import pandas as pd
from fastapi.testclient import TestClient
from zakatable import cache
from zakatable.api.main import app

# --- 1. Autouse Fixture to Isolate Cache ---
@pytest.fixture(autouse=True)
def isolate_cache(tmp_path):
    """
    Reroutes the caching directory to a temporary path for each test,
    ensuring testing operations are clean and don't write to developer runs.
    """
    old_cache_dir = cache.CACHE_DIR
    temp_dir = tmp_path / "zakatable_test_cache"
    temp_dir.mkdir(parents=True, exist_ok=True)
    cache.CACHE_DIR = str(temp_dir)
    yield
    cache.clear_cache()
    cache.CACHE_DIR = old_cache_dir

# --- 2. Test Client for FastAPI Endpoints ---
@pytest.fixture
def client():
    """
    Provides a Starlette TestClient pointing to the FastAPI server app.
    """
    return TestClient(app)

# --- 3. Mock Data Mocking Helpers ---
@pytest.fixture
def mock_financial_data():
    """
    Provides a standardized set of parsed metrics for AAPL, BAC, and DIS
    which can be injected into tests to verify calculations without hitting yfinance.
    """
    return {
        "AAPL": {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "price": 300.0,
            "shares_outstanding": 15000000000.0,
            "market_cap": 4500000000000.0,
            "cash_equivalents": 25000000000.0,
            "short_term_investments": 10000000000.0,
            "accounts_receivable": 75000000000.0,
            "inventory": 5000000000.0,
            "total_current_assets": 115000000000.0,
            "total_current_liabilities": 145000000000.0,
            "total_assets": 350000000000.0,
            "total_liabilities": 290000000000.0,
            "total_debt": 90000000000.0,
            "trailing_market_cap_12m": 4300000000000.0,
            "trailing_market_cap_36m": 4000000000000.0
        },
        "BAC": {
            "symbol": "BAC",
            "company_name": "Bank of America Corporation",
            "sector": "Financial Services",
            "industry": "Banks—Diversified",
            "price": 50.0,
            "shares_outstanding": 8000000000.0,
            "market_cap": 400000000000.0,
            "cash_equivalents": 150000000000.0,
            "short_term_investments": 50000000000.0,
            "accounts_receivable": 120000000000.0,
            "inventory": 0.0,
            "total_current_assets": 320000000000.0,
            "total_current_liabilities": 100000000000.0,
            "total_assets": 3200000000000.0,
            "total_liabilities": 2900000000000.0,
            "total_debt": 800000000000.0,
            "trailing_market_cap_12m": 390000000000.0,
            "trailing_market_cap_36m": 380000000000.0
        }
    }

class MockTicker:
    """
    Mock class replacing yfinance Ticker object.
    """
    def __init__(self, symbol, mock_dict):
        self.symbol = symbol
        self.mock_data = mock_dict.get(symbol, {})
        
        # Structure self.info
        if symbol == "GC=F":
            self.info = {
                "symbol": symbol,
                "currentPrice": 2332.76, # gold futures spot price per troy ounce (~ $75/g)
                "regularMarketPrice": 2332.76
            }
        elif symbol == "SI=F":
            self.info = {
                "symbol": symbol,
                "currentPrice": 29.55, # silver futures spot price per troy ounce (~ $0.95/g)
                "regularMarketPrice": 29.55
            }
        elif symbol.endswith("=X"):
            pair = symbol[:-2]
            src = pair[:3]
            tgt = pair[3:]
            rate = None
            if src == tgt:
                rate = 1.0
            elif src == "EUR" and tgt == "USD":
                rate = 1.08
            elif src == "USD" and tgt == "EUR":
                rate = 0.92
            elif src == "GBP" and tgt == "USD":
                rate = 1.27
            elif src == "USD" and tgt == "GBP":
                rate = 0.79
            self.info = {
                "symbol": symbol,
                "currentPrice": rate,
                "regularMarketPrice": rate
            }
        else:
            self.info = {
                "symbol": self.symbol,
                "shortName": self.mock_data.get("company_name", self.symbol),
                "longName": self.mock_data.get("company_name", self.symbol),
                "sector": self.mock_data.get("sector"),
                "industry": self.mock_data.get("industry"),
                "currentPrice": self.mock_data.get("price"),
                "sharesOutstanding": self.mock_data.get("shares_outstanding"),
                "marketCap": self.mock_data.get("market_cap"),
                "totalDebt": self.mock_data.get("total_debt"),
                "longBusinessSummary": "Mock summary for testing."
            }
        
        # Structure balance sheet DataFrame
        data = {
            "Cash And Cash Equivalents": [self.mock_data.get("cash_equivalents", 0.0)],
            "Short Term Investments": [self.mock_data.get("short_term_investments", 0.0)],
            "Net Receivables": [self.mock_data.get("accounts_receivable", 0.0)],
            "Inventory": [self.mock_data.get("inventory", 0.0)],
            "Total Current Assets": [self.mock_data.get("total_current_assets", 0.0)],
            "Total Current Liabilities": [self.mock_data.get("total_current_liabilities", 0.0)],
            "Total Assets": [self.mock_data.get("total_assets", 0.0)],
            "Total Liabilities Net Minority Interest": [self.mock_data.get("total_liabilities", 0.0)],
        }
        # Transposed structure
        self.balance_sheet = pd.DataFrame(data, index=["2025-12-31"]).T
        self.quarterly_balance_sheet = self.balance_sheet
        
    def history(self, period="1y", interval="1mo"):
        # Return mock series
        idx = pd.date_range(end="2026-06-01", periods=12, freq="ME")
        return pd.DataFrame({"Close": [self.mock_data.get("price", 100.0)] * 12}, index=idx)

@pytest.fixture
def mock_yfinance(monkeypatch, mock_financial_data):
    """
    Monkeypatches yfinance.Ticker to prevent outbound HTTP queries and return mock data.
    """
    def mock_ticker_init(symbol, *args, **kwargs):
        return MockTicker(symbol, mock_financial_data)
        
    monkeypatch.setattr("yfinance.Ticker", mock_ticker_init)
