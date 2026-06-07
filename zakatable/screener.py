import os
import yaml
import yfinance as yf
import pandas as pd
import numpy as np
from zakatable.session import get_yf_ticker
from typing import Dict, Any, List, Optional
from zakatable import cache

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")

def load_yaml_config(filename: str) -> Dict[str, Any]:
    path = os.path.join(CONFIG_DIR, filename)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading config {filename}: {e}")
        return {}

def get_row_value(df: pd.DataFrame, possible_keys: List[str], default: float = 0.0) -> float:
    """
    Search for a financial line item in a DataFrame by checking several possible index labels.
    Returns the value from the most recent period (first column) or default.
    """
    if df is None or df.empty:
        return default
    
    # Lowercase and strip index for robust matching
    cleaned_index = {str(idx).strip().lower(): idx for idx in df.index}
    
    for key in possible_keys:
        cleaned_key = key.strip().lower()
        if cleaned_key in cleaned_index:
            real_key = cleaned_index[cleaned_key]
            val = df.loc[real_key]
            # If it's a Series (multiple dates), get the most recent date (usually the first column)
            if isinstance(val, pd.Series):
                # Check the first non-nan value
                for item in val:
                    if pd.notna(item):
                        return float(item)
                return default
            elif pd.notna(val):
                return float(val)
            
    return default

def calculate_trailing_market_cap(ticker_obj: yf.Ticker, current_shares: float, months: int = 12) -> float:
    """
    Fetches historical stock prices and computes the average market cap.
    """
    period_map = {12: "1y", 24: "2y", 36: "3y"}
    period = period_map.get(months, "1y")
    
    try:
        history = ticker_obj.history(period=period, interval="1mo")
        if history.empty:
            return 0.0
        avg_close = history["Close"].mean()
        if pd.isna(avg_close):
            return 0.0
        return avg_close * current_shares
    except Exception as e:
        print(f"Error calculating trailing average market cap: {e}")
        return 0.0

def fetch_and_process_ticker(ticker_symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetches raw stock details from Yahoo Finance (or cache) and parses the balance sheet
    and info dictionaries.
    """
    ticker_symbol = ticker_symbol.strip().upper()
    
    # 1. Try cache first
    if not force_refresh:
        cached = cache.get_cached_data(ticker_symbol)
        if cached:
            return cached["data"]
            
    # 2. Fetch live data
    try:
        ticker_obj = get_yf_ticker(ticker_symbol)
        info = ticker_obj.info
        
        if not info or "shortName" not in info:
            # Try to fetch history just to see if ticker exists
            hist = ticker_obj.history(period="1d")
            if hist.empty:
                raise ValueError(f"Ticker symbol '{ticker_symbol}' not found or invalid.")
        
        # Access annual balance sheet
        bs_annual = ticker_obj.balance_sheet
        
        # If annual balance sheet is empty, fall back to quarterly
        bs = bs_annual if (bs_annual is not None and not bs_annual.empty) else ticker_obj.quarterly_balance_sheet
        
        # Sort columns to ensure newest date is first
        if bs is not None and not bs.empty:
            # convert column labels to string/datetime and sort descending
            bs = bs.reindex(columns=sorted(bs.columns, reverse=True))
            
        # Parse out critical financial details
        cash_equiv_keys = ["Cash And Cash Equivalents", "CashAndCashEquivalents", "Cash Cash Equivalents & Short Term Investments", "Cash Financial"]
        receivables_keys = ["Net Receivables", "Receivables", "Accounts Receivable", "Gross Accounts Receivable", "AccountsReceivable"]
        inventory_keys = ["Inventory", "Inventories", "Net Inventory"]
        short_term_inv_keys = ["Other Cash Short Term Investments", "Short Term Investments", "OtherShortTermInvestments", "ShortTermInvestments"]
        current_assets_keys = ["Total Current Assets", "Current Assets", "TotalCurrentAssets"]
        current_liab_keys = ["Total Current Liabilities", "Current Liabilities", "TotalCurrentLiabilities"]
        total_assets_keys = ["Total Assets", "TotalAssets"]
        total_liab_keys = ["Total Liabilities Net Minority Interest", "Total Liabilities", "TotalLiabilities"]
        
        cash = get_row_value(bs, cash_equiv_keys, 0.0)
        receivables = get_row_value(bs, receivables_keys, 0.0)
        inventory = get_row_value(bs, inventory_keys, 0.0)
        short_term_investments = get_row_value(bs, short_term_inv_keys, 0.0)
        current_assets = get_row_value(bs, current_assets_keys, 0.0)
        current_liabilities = get_row_value(bs, current_liab_keys, 0.0)
        total_assets = get_row_value(bs, total_assets_keys, 0.0)
        total_liabilities = get_row_value(bs, total_liab_keys, 0.0)
        
        # Parse total debt
        # First check if yfinance provides 'Total Debt' in info or BS
        total_debt = info.get("totalDebt")
        if total_debt is None:
            total_debt = get_row_value(bs, ["Total Debt", "TotalDebt"], None)
            
        if total_debt is None:
            # Fallback to ShortTermDebt + LongTermDebt
            st_debt_keys = ["Short Long Term Debt", "ShortTermDebt", "Current Debt", "Current Debt And Capital Lease Obligation"]
            lt_debt_keys = ["Long Term Debt", "LongTermDebt", "Long Term Debt And Capital Lease Obligation"]
            st_debt = get_row_value(bs, st_debt_keys, 0.0)
            lt_debt = get_row_value(bs, lt_debt_keys, 0.0)
            total_debt = st_debt + lt_debt
            
        # Basic fields from info
        shares_outstanding = info.get("sharesOutstanding")
        if not shares_outstanding or shares_outstanding == 0:
            # Fallback from balance sheet share count if available
            shares_outstanding = get_row_value(bs, ["Share Factor", "Share Cap", "Ordinary Shares Number"], 1.0)
            if shares_outstanding == 1.0:
                shares_outstanding = info.get("impliedSharesOutstanding", 1.0)
                
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or 0.0
        market_cap = info.get("marketCap")
        if not market_cap and price and shares_outstanding:
            market_cap = price * shares_outstanding
            
        # Compile processed data dictionary
        processed_data = {
            "symbol": ticker_symbol,
            "company_name": info.get("longName") or info.get("shortName") or ticker_symbol,
            "sector": info.get("sector") or "N/A",
            "industry": info.get("industry") or "N/A",
            "business_summary": info.get("longBusinessSummary") or "N/A",
            "price": float(price),
            "shares_outstanding": float(shares_outstanding),
            "market_cap": float(market_cap) if market_cap else 0.0,
            
            # Balance Sheet Items
            "cash_equivalents": cash,
            "short_term_investments": short_term_investments,
            "accounts_receivable": receivables,
            "inventory": inventory,
            "total_current_assets": current_assets,
            "total_current_liabilities": current_liabilities,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_debt": float(total_debt) if total_debt else 0.0,
            
            # Fetch historical average prices to support trailing market caps
            "trailing_market_cap_12m": calculate_trailing_market_cap(ticker_obj, shares_outstanding, 12),
            "trailing_market_cap_36m": calculate_trailing_market_cap(ticker_obj, shares_outstanding, 36),
        }
        
        # Save to cache
        cache.set_cached_data(ticker_symbol, processed_data)
        return processed_data
        
    except Exception as e:
        print(f"Error fetching data for ticker {ticker_symbol}: {e}")
        raise ValueError(f"Failed to fetch stock data: {str(e)}")

def perform_compliance_screening(
    stock_data: Dict[str, Any],
    standard_name: str = "aaoifi",
    denominator_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates Shariah compliance based on business activity and financial ratios.
    Reference: AAOIFI Shari'ah Standard No. 21 (Financial Papers - Shares and Bonds)
    Standard catalog link: https://aaoifi.com/ss-21-financial-paper-shares-and-bonds/?lang=en
    Other index methodologies referenced for denominator/ratios:
    - S&P Dow Jones Shariah Indices: https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-shariah-indices.pdf
    - MSCI Islamic Index Methodology Portal: https://www.msci.com/index-methodology
      (Historical PDF: https://www.msci.com/eqb/methodology/meth_docs/MSCI_Islamic_Index_Methodology_Nov2019.pdf)
    """
    # Load rules and overrides
    rules = load_yaml_config("business_rules.yaml")
    overrides = load_yaml_config("overrides.yaml")
    
    # 1. Resolve compliance standard configuration
    standards = rules.get("compliance_standards", {})
    standard = standards.get(standard_name, standards.get("aaoifi", {}))
    
    debt_threshold = standard.get("debt_threshold", 0.33)
    cash_threshold = standard.get("cash_threshold", 0.33)
    receivables_threshold = standard.get("receivables_threshold", 0.33)
    max_non_halal_rev = standard.get("max_non_halal_revenue", 0.05)
    
    # 2. Resolve Denominator
    denom_type = denominator_override or rules.get("default_denominator", "market_cap")
    
    if denom_type == "total_assets":
        denominator = stock_data["total_assets"]
        denom_label = "Total Assets"
    elif denom_type == "trailing_market_cap_12m" or denom_type == "trailing_12m":
        denominator = stock_data["trailing_market_cap_12m"]
        denom_label = "12-Month Average Market Cap"
    elif denom_type == "trailing_market_cap_36m" or denom_type == "trailing_36m":
        denominator = stock_data["trailing_market_cap_36m"]
        denom_label = "36-Month Average Market Cap"
    else: # default "market_cap"
        denominator = stock_data["market_cap"]
        denom_label = "Current Market Cap"
        
    # If denominator resolves to zero, fallback to total assets or market cap to avoid DivisionByZero
    if not denominator or denominator == 0.0:
        denominator = stock_data.get("market_cap") or stock_data.get("total_assets") or 1.0
        denom_label = "Current Market Cap (Fallback)"
        
    # 3. Business Activity Screen
    symbol = stock_data["symbol"]
    override = overrides.get(symbol, {})
    
    business_halal = True
    business_reason = ""
    non_compliant_rev_pct = 0.0
    
    # Sector/industry check
    sector_is_haram = stock_data["sector"] in rules.get("haram_sectors", [])
    industry_is_haram = stock_data["industry"] in rules.get("haram_industries", [])
    
    if sector_is_haram:
        business_halal = False
        business_reason = f"Sector is classified as non-compliant: {stock_data['sector']}"
        non_compliant_rev_pct = 1.0
    elif industry_is_haram:
        business_halal = False
        business_reason = f"Industry is classified as non-compliant: {stock_data['industry']}"
        non_compliant_rev_pct = 1.0
        
    # Apply override if present
    if override:
        status = override.get("status")
        if status == "halal":
            business_halal = True
            business_reason = "Manual override: Certified compliant"
            non_compliant_rev_pct = override.get("non_compliant_revenue_pct", 0.0)
        elif status == "haram":
            business_halal = False
            business_reason = override.get("reason", "Manual override: Non-compliant")
            non_compliant_rev_pct = override.get("non_compliant_revenue_pct", 1.0)
            
    # 4. Financial Ratio Screen
    debt_value = stock_data["total_debt"]
    # Cash screen includes Cash & Equivalents + Short Term Investments
    cash_value = stock_data["cash_equivalents"] + stock_data["short_term_investments"]
    receivables_value = stock_data["accounts_receivable"]
    
    debt_ratio = debt_value / denominator
    cash_ratio = cash_value / denominator
    receivables_ratio = receivables_value / denominator
    
    debt_passed = debt_ratio < debt_threshold
    cash_passed = cash_ratio < cash_threshold
    receivables_passed = receivables_ratio < receivables_threshold
    
    financials_available = stock_data.get("financials_available", True)
    financials_passed = debt_passed and cash_passed and receivables_passed
    
    # 5. Overall Compliance Status
    if not financials_available:
        is_compliant = False
        business_reason = "Financial compliance is uncertain: Balance sheet data is unavailable due to Yahoo Finance API rate limits."
    else:
        is_compliant = business_halal and financials_passed
    
    return {
        "ticker": symbol,
        "company_name": stock_data["company_name"],
        "compliance_standard": standard_name.upper(),
        "is_compliant": is_compliant,
        "denominator_used": denom_label,
        "denominator_value": float(denominator),
        "financials_available": financials_available,
        
        "business_screen": {
            "is_halal": business_halal,
            "non_compliant_revenue_percentage": float(non_compliant_rev_pct),
            "reason": business_reason or "Primary business activity is Shariah-compliant",
            "sector": stock_data["sector"],
            "industry": stock_data["industry"]
        },
        
        "financial_screens": {
            "passed_all": financials_passed,
            "debt": {
                "ratio": float(debt_ratio),
                "threshold": float(debt_threshold),
                "passed": bool(debt_passed),
                "raw_debt": float(debt_value)
            },
            "cash_and_investments": {
                "ratio": float(cash_ratio),
                "threshold": float(cash_threshold),
                "passed": bool(cash_passed),
                "raw_cash": float(cash_value)
            },
            "receivables": {
                "ratio": float(receivables_ratio),
                "threshold": float(receivables_threshold),
                "passed": bool(receivables_passed),
                "raw_receivables": float(receivables_value)
            }
        }
    }

def calculate_zakat_metrics(stock_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes Zakat due on a single stock using the balance sheet method.
    References:
    - AAOIFI Shari'ah Standard No. 35 (Zakah), item 4/2/4 (Pro-rata share of Net Zakatable Assets)
      Portal link: https://aaoifi.com/e-standards/?lang=en
    - AMJA Declaration on Zakat of Shares:
      Link: https://www.amjaonline.org/declaration-articles/zakat-on-shares-and-investments/
    
    Formula:
    Zakatable Assets = Cash & Cash Equivalents + Short Term Investments + Net Receivables + Inventory
    Net Zakatable Assets = Zakatable Assets - Current Liabilities
    Zakatable Asset per share = Net Zakatable Assets / Shares Outstanding
    Zakat Due per share (Lunar) = Zakatable Asset per share * 2.5% (0.025) (Sunan Ibn Majah 1790: https://sunnah.com/ibnmajah:1790)
    Zakat Due per share (Solar) = Zakatable Asset per share * 2.577% (0.02577) (AAOIFI SS 35 Sec. 5/2/2 solar calendar rate)
    """
    cash = stock_data["cash_equivalents"]
    short_term_inv = stock_data["short_term_investments"]
    receivables = stock_data["accounts_receivable"]
    inventory = stock_data["inventory"]
    current_liabilities = stock_data["total_current_liabilities"]
    shares = stock_data["shares_outstanding"]
    
    # 1. Total raw zakatable assets
    zakatable_assets_raw = cash + short_term_inv + receivables + inventory
    
    # 2. Subtract current liabilities
    net_zakatable_assets = zakatable_assets_raw - current_liabilities
    
    # Under Shariah principles, if net zakatable assets is negative, no Zakat is due (it is floored to 0.0)
    if net_zakatable_assets < 0.0:
        net_zakatable_assets_clean = 0.0
    else:
        net_zakatable_assets_clean = net_zakatable_assets
        
    # 3. Compute per-share values
    if shares > 0:
        zakatable_asset_per_share = net_zakatable_assets_clean / shares
    else:
        zakatable_asset_per_share = 0.0
        
    zakat_per_share_lunar = zakatable_asset_per_share * 0.025
    zakat_per_share_solar = zakatable_asset_per_share * 0.02577
    
    # 4. Market cap comparison (for 30% proxy method reference)
    price = stock_data["price"]
    proxy_zakatable_asset_per_share = price * 0.30
    proxy_zakat_per_share_lunar = proxy_zakatable_asset_per_share * 0.025
    proxy_zakat_per_share_solar = proxy_zakatable_asset_per_share * 0.02577
    
    return {
        "shares_outstanding": float(shares),
        "current_price": float(price),
        
        # Raw items
        "breakdown": {
            "cash_equivalents": float(cash),
            "short_term_investments": float(short_term_inv),
            "accounts_receivable": float(receivables),
            "inventory": float(inventory),
            "total_zakatable_assets_raw": float(zakatable_assets_raw),
            "total_current_liabilities": float(current_liabilities)
        },
        
        # Balance Sheet Method
        "balance_sheet_method": {
            "net_zakatable_assets_total": float(net_zakatable_assets), # can be negative
            "net_zakatable_assets_floored": float(net_zakatable_assets_clean), # >= 0
            "zakatable_asset_per_share": float(zakatable_asset_per_share),
            "zakat_due_per_share_lunar": float(zakat_per_share_lunar),
            "zakat_due_per_share_solar": float(zakat_per_share_solar)
        },
        
        # 30% Proxy Method (Alternate reference)
        "proxy_method_30pct": {
            "zakatable_asset_per_share": float(proxy_zakatable_asset_per_share),
            "zakat_due_per_share_lunar": float(proxy_zakat_per_share_lunar),
            "zakat_due_per_share_solar": float(proxy_zakat_per_share_solar)
        }
    }

def screen_stock(
    ticker: str,
    standard_name: str = "aaoifi",
    denominator_override: Optional[str] = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    High-level entry point to retrieve stock data, check Shariah compliance,
    and calculate Zakat.
    """
    raw_data = fetch_and_process_ticker(ticker, force_refresh)
    compliance = perform_compliance_screening(raw_data, standard_name, denominator_override)
    zakat = calculate_zakat_metrics(raw_data)
    
    return {
        "ticker": raw_data["symbol"],
        "company_name": raw_data["company_name"],
        "sector": raw_data["sector"],
        "industry": raw_data["industry"],
        "price": raw_data["price"],
        "compliance": compliance,
        "zakat": zakat
    }
