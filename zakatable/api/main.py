import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Import from our packaged zakatable library
from zakatable import screener, cache
from zakatable import ZakatCalculator

app = FastAPI(
    title="Islamic Finance & Zakat API",
    description="A comprehensive API for Shariah compliance stock screening and Zakat calculations.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas ---

class TickerResponse(BaseModel):
    ticker: str
    company_name: str
    sector: str
    industry: str
    price: float
    compliance: Dict[str, Any]
    zakat: Dict[str, Any]

class BatchRequest(BaseModel):
    tickers: List[str] = Field(..., example=["AAPL", "MSFT", "TSLA"])

class PortfolioItem(BaseModel):
    ticker: str = Field(..., example="AAPL")
    shares: float = Field(..., example=10.0)

class CalculationSettings(BaseModel):
    base_currency: str = Field("USD", example="USD")
    nisab_standard: str = Field("silver", example="silver")
    calendar_type: str = Field("gregorian", example="gregorian")
    standard: Optional[str] = Field(None, example="aaoifi")
    denominator: Optional[str] = Field(None, example="market_cap")

class CashAssetInput(BaseModel):
    amount: float = Field(..., example=15000.00)
    currency: str = Field("USD", example="USD")

class PreciousMetalAssetInput(BaseModel):
    metal: str = Field(..., example="gold")
    weight: float = Field(..., example=20.0)
    purity: Any = Field(24.0, example=22.0)
    unit: str = Field("grams", example="grams")

class StockAssetInput(BaseModel):
    ticker: str = Field(..., example="AAPL")
    shares: float = Field(..., example=100.0)
    intent: str = Field("holding", example="holding")

class BusinessInventoryAssetInput(BaseModel):
    value: float = Field(..., example=5000.00)
    currency: str = Field("USD", example="USD")

class RealEstateAssetInput(BaseModel):
    value: float = Field(..., example=450000.00)
    currency: str = Field("USD", example="USD")
    type: str = Field("primary", example="primary")  # primary, rental, flip

class ReceivableInput(BaseModel):
    amount: float = Field(..., example=3000.00)
    currency: str = Field("USD", example="USD")
    type: str = Field("good", example="good")  # good (performing), bad (non-performing/doubtful)

class RetirementAccountInput(BaseModel):
    balance: float = Field(..., example=50000.00)
    currency: str = Field("USD", example="USD")
    tax_rate: float = Field(0.20, example=0.20)      # Expected tax rate if withdrawn (default: 20%)
    penalty_rate: float = Field(0.10, example=0.10)  # Expected early withdrawal penalty (default: 10%)
    is_accessible: bool = Field(True, example=True)   # If False, locked (completely inaccessible, Zakat is 0 until accessible)

class AssetsInput(BaseModel):
    cash: Optional[List[CashAssetInput]] = None
    precious_metals: Optional[List[PreciousMetalAssetInput]] = None
    stocks: Optional[List[StockAssetInput]] = None
    business_inventory: Optional[List[BusinessInventoryAssetInput]] = None
    real_estate: Optional[List[RealEstateAssetInput]] = None
    receivables: Optional[List[ReceivableInput]] = None
    retirement_accounts: Optional[List[RetirementAccountInput]] = None

class ShortTermDebtInput(BaseModel):
    type: str = Field("debt", example="credit_card")
    amount: float = Field(..., example=2500.00)
    currency: str = Field("USD", example="USD")

class LiabilitiesInput(BaseModel):
    short_term_debts: Optional[List[ShortTermDebtInput]] = None

class PortfolioRequest(BaseModel):
    # New structured fields
    settings: Optional[CalculationSettings] = None
    assets: Optional[AssetsInput] = None
    liabilities: Optional[LiabilitiesInput] = None
    
    # Old fields for backward compatibility
    items: Optional[List[PortfolioItem]] = None
    standard: Optional[str] = "aaoifi"
    denominator: Optional[str] = None
    use_proxy: Optional[bool] = False

class CalculationSettingsResponse(BaseModel):
    base_currency: str
    nisab_standard: str
    calendar_type: str
    zakat_rate: float

class AssetBreakdownItem(BaseModel):
    asset_class: str
    label: str
    raw_value: float
    value_base: float
    zakatable_value: float
    zakat_due: float
    rationale: str

class PortfolioSummary(BaseModel):
    settings: CalculationSettingsResponse
    nisab_threshold_used: float
    nisab_value_base: float
    is_nisab_met: bool
    gross_zakatable_assets: float
    allowed_liabilities: float
    net_zakatable_wealth: float
    total_zakat_due: float
    breakdown: List[AssetBreakdownItem]
    
    # Old fields for backward compatibility, optional
    total_market_value: Optional[float] = None
    total_zakatable_value: Optional[float] = None
    total_zakat_due_lunar: Optional[float] = None
    total_zakat_due_solar: Optional[float] = None
    method_used: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None

# --- API Routes ---

@app.get("/api/v1/config", tags=["Configuration"])
def get_config():
    """
    Retrieve current screening configurations, business rules, and manual overrides.
    """
    try:
        rules = screener.load_yaml_config("business_rules.yaml")
        overrides = screener.load_yaml_config("overrides.yaml")
        return {
            "rules": rules,
            "overrides": overrides
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load configurations: {str(e)}")

@app.get("/api/v1/screen/{ticker}", response_model=TickerResponse, tags=["Screening"])
def screen_ticker(
    ticker: str,
    standard: str = Query("aaoifi", description="Screening standard (aaoifi, dow_jones, msci)"),
    denominator: Optional[str] = Query(
        None, 
        description="Override denominator (market_cap, total_assets, trailing_market_cap_12m, trailing_market_cap_36m)"
    ),
    refresh: bool = Query(False, description="Force refresh data from Yahoo Finance")
):
    """
    Analyze a US stock for Shariah compliance and compute Zakat details.
    """
    try:
        data = screener.screen_stock(
            ticker=ticker,
            standard_name=standard,
            denominator_override=denominator,
            force_refresh=refresh
        )
        return data
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/api/v1/screen/batch", response_model=Dict[str, TickerResponse], tags=["Screening"])
def batch_screen(
    request: BatchRequest,
    standard: str = Query("aaoifi", description="Screening standard (aaoifi, dow_jones, msci)"),
    denominator: Optional[str] = Query(
        None, 
        description="Override denominator (market_cap, total_assets, trailing_market_cap_12m, trailing_market_cap_36m)"
    ),
    refresh: bool = Query(False, description="Force refresh data from Yahoo Finance")
):
    """
    Analyze multiple stocks in a single request.
    """
    results = {}
    for ticker in request.tickers:
        try:
            results[ticker.upper()] = screener.screen_stock(
                ticker=ticker,
                standard_name=standard,
                denominator_override=denominator,
                force_refresh=refresh
            )
        except Exception as e:
            print(f"Failed to screen ticker {ticker} in batch: {e}")
            
    return results

@app.post("/api/v1/calculate-portfolio", response_model=PortfolioSummary, tags=["Zakat Calculator"])
def calculate_portfolio_zakat(request: PortfolioRequest):
    """
    Compute total Zakat due on a portfolio, using the local ZakatCalculator client library.
    """
    try:
        calc = ZakatCalculator()
        
        # If the request used the old simple structure (items list), convert it
        if request.items is not None and request.assets is None:
            holdings = [{"ticker": item.ticker, "shares": item.shares} for item in request.items]
            # Use the settings defaults or standard from request
            settings = {
                "base_currency": "USD",
                "nisab_standard": "silver",
                "calendar_type": "gregorian"
            }
            result = calc.calculate_portfolio(
                holdings=holdings,
                use_proxy=request.use_proxy or False,
                standard=request.standard,
                denominator=request.denominator,
                settings=settings
            )
            
            # Reconstruct old response keys for backward compatibility
            total_market_value = 0.0
            total_zakatable_value = 0.0
            old_items = []
            
            for b_item in result["breakdown"]:
                ticker_part = b_item["label"].split()[0]
                is_compliant = "Halal" in b_item["label"]
                raw_val = b_item["raw_value"]
                val_base = b_item["value_base"]
                price = val_base / raw_val if raw_val > 0 else 0.0
                
                total_market_value += val_base
                total_zakatable_value += b_item["zakatable_value"]
                
                z_lunar = b_item["zakatable_value"] * 0.025
                z_solar = b_item["zakatable_value"] * 0.02577
                
                old_items.append({
                    "ticker": ticker_part,
                    "company_name": ticker_part,
                    "shares": raw_val,
                    "price": price,
                    "market_value": val_base,
                    "is_compliant": is_compliant,
                    "status": "Compliant" if is_compliant else "Non-Compliant",
                    "zakatable_value": b_item["zakatable_value"],
                    "zakatable_asset_per_share": b_item["zakatable_value"] / raw_val if raw_val > 0 else 0.0,
                    "zakat_due_lunar": z_lunar,
                    "zakat_due_solar": z_solar,
                    "method_used": "30% Market Cap Proxy" if request.use_proxy else "Balance Sheet Method",
                    "rationale": b_item["rationale"]
                })
                
            result["total_market_value"] = total_market_value
            result["total_zakatable_value"] = total_zakatable_value
            result["total_zakat_due_lunar"] = total_zakatable_value * 0.025
            result["total_zakat_due_solar"] = total_zakatable_value * 0.02577
            result["method_used"] = "30% Market Cap Proxy" if request.use_proxy else "Balance Sheet Method"
            result["items"] = old_items
            
        else:
            # New structured request
            def dump_model(model):
                if model is None:
                    return {}
                return model.model_dump(exclude_none=True) if hasattr(model, "model_dump") else model.dict(exclude_none=True)
                
            settings_dict = dump_model(request.settings)
            assets_dict = dump_model(request.assets)
            liabilities_dict = dump_model(request.liabilities)
            
            result = calc.calculate_portfolio(
                settings=settings_dict,
                assets=assets_dict,
                liabilities=liabilities_dict
            )
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate portfolio: {str(e)}")

@app.post("/api/v1/cache/clear", tags=["System"])
def clear_api_cache(ticker: Optional[str] = Query(None, description="Clear cache for a specific ticker")):
    """
    Clears local file cache. If ticker is omitted, clears all cache.
    """
    try:
        cache.clear_cache(ticker)
        return {"status": "success", "message": "Cache cleared successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

# Mount static files for HTML UI (serves index.html at root "/")
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    print(f"Warning: Static directory {static_dir} not found. UI files will not be served.")

def start_server():
    """
    Launches the FastAPI Uvicorn server. Exposed as a CLI script.
    """
    import uvicorn
    uvicorn.run("zakatable.api.main:app", host="0.0.0.0", port=8000, reload=True)

