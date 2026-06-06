import os
from decimal import Decimal, getcontext, ROUND_HALF_UP
from typing import List, Dict, Any, Optional

from zakatable import screener
from zakatable import cache
from zakatable.forex import get_exchange_rate
from zakatable.commodities import get_nisab_threshold, get_commodity_spot_price

# Set decimal precision context for high-precision financial operations
getcontext().prec = 28

# Core rates and parameters
LUNAR_RATE = Decimal("0.025")       # 2.50% based on Lunar calendar
SOLAR_RATE = Decimal("0.02577")    # 2.577% adjusted for Solar calendar

class ZakatCalculator:
    """
    State-of-the-art Zakat Calculation Engine. Calculates compliance and Zakat liability
    across multiple asset classes (cash, stocks, precious metals, business inventory, real estate)
    with short-term debt deductions and dynamic gold/silver Nisab checking.
    
    The engine runs entirely in-memory and enforces strict Decimal arithmetic to avoid
    floating-point rounding errors.
    """
    
    def __init__(self, default_standard: str = "aaoifi", default_denominator: str = "market_cap"):
        self.default_standard = default_standard
        self.default_denominator = default_denominator
        
    def calculate_portfolio(
        self,
        holdings: List[Dict[str, Any]] = None,  # Kept for backward compatibility
        use_proxy: bool = False,                # Kept for backward compatibility
        standard: Optional[str] = None,
        denominator: Optional[str] = None,
        force_refresh: bool = False,
        
        # New Structured parameters matching REST API specification
        settings: Optional[Dict[str, Any]] = None,
        assets: Optional[Dict[str, Any]] = None,
        liabilities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculates Zakat obligations, allowed liabilities, and Nisab compliance.
        Supports both simple stock lists and complex, multi-asset portfolios.
        """
        # Resolve settings
        settings = settings or {}
        base_currency = settings.get("base_currency", "USD").strip().upper()
        nisab_standard = settings.get("nisab_standard", "silver").strip().lower()
        calendar_type = settings.get("calendar_type", "gregorian").strip().lower()
        resolved_std = standard or settings.get("standard") or self.default_standard
        resolved_denom = denominator or settings.get("denominator") or self.default_denominator
        
        # Determine Zakat rate
        # Reference: AAOIFI Shari'ah Standard No. 35 (Zakah) Section 5/2/2 (Solar year adjustment)
        # See E-Standards: https://aaoifi.com/e-standards/?lang=en
        # Hadith: Sunan Ibn Majah 1790 - establishing the lunar Zakat rate of 2.5% (one-fortieth):
        # https://sunnah.com/ibnmajah:1790
        # Solar adjustment: 2.5% * (365.25 / 354) = 2.577% (reflecting extra 11 days of asset accumulation)
        zakat_rate = SOLAR_RATE if calendar_type == "gregorian" else LUNAR_RATE
        
        # Backwards compatibility wrapper for simple stock portfolios
        if holdings is not None and assets is None:
            assets = {"stocks": []}
            for h in holdings:
                ticker = (h.get("ticker") or h.get("symbol") or "").strip().upper()
                shares = float(h.get("shares") or h.get("quantity") or 0.0)
                intent = "holding"
                assets["stocks"].append({"ticker": ticker, "shares": shares, "intent": intent})
                
        assets = assets or {}
        liabilities = liabilities or {}
        
        gross_zakatable_assets = Decimal("0.0")
        total_zakat_due = Decimal("0.0")
        breakdown = []
        
        # --- 1. PROCESS CASH ASSETS ---
        # Fiqh Reference: AAOIFI Shari'ah Standard No. 35 (Zakah), Section 2 (Zakat on Cash & Receivables)
        # See E-Standards: https://aaoifi.com/e-standards/?lang=en
        # Cash is a liquid medium of exchange and is 100% subject to Zakat.
        # See also NZF Cash Guide: https://nzf.org.uk/knowledge/zakat-on-cash/
        for cash_item in assets.get("cash", []):
            amount = Decimal(str(cash_item.get("amount", 0.0)))
            curr = cash_item.get("currency", base_currency).strip().upper()
            
            rate = get_exchange_rate(curr, base_currency, force_refresh)
            val_base = amount * rate
            zakat_due = val_base * zakat_rate
            
            gross_zakatable_assets += val_base
            
            breakdown.append({
                "asset_class": "cash",
                "label": f"Cash ({curr})",
                "raw_value": float(amount),
                "value_base": float(val_base),
                "zakatable_value": float(val_base),
                "zakat_due": float(zakat_due),
                "rationale": (
                    f"Cash holdings are 100% subject to Zakat (AAOIFI Standard No. 35, Sec. 2). "
                    f"{amount:,.2f} {curr} converted to base currency is ${val_base:,.2f}, "
                    f"yielding ${zakat_due:,.2f} Zakat at a {calendar_type} Zakat rate of {float(zakat_rate)*100:.3f}%."
                )
            })
            
        # --- 2. PROCESS PRECIOUS METALS ---
        # Quranic Reference: Surah At-Tawbah 9:34 - "And those who hoard gold and silver and spend it not..."
        # Link: https://quran.com/9/34
        # Hadith Reference: Sunan Abu Dawud 1572 - establishing the gold/silver Zakat thresholds and Nisab:
        # Link: https://sunnah.com/abudawud:1572
        # Detailed guide: NZF Gold & Silver Guide: https://nzf.org.uk/knowledge/zakat-on-gold-and-silver/
        for metal_item in assets.get("precious_metals", []):
            metal = metal_item.get("metal", "gold").strip().lower()
            weight = Decimal(str(metal_item.get("weight", 0.0)))
            unit = metal_item.get("unit", "grams").strip().lower()
            purity = metal_item.get("purity", 24.0)
            
            # Karat to decimal purity mapping
            if purity in (24, 24.0, "24k"):
                purity_decimal = Decimal("1.0")
            elif purity in (22, 22.0, "22k"):
                purity_decimal = Decimal("22") / Decimal("24")
            elif purity in (21, 21.0, "21k"):
                purity_decimal = Decimal("21") / Decimal("24")
            elif purity in (18, 18.0, "18k"):
                purity_decimal = Decimal("18") / Decimal("24")
            else:
                purity_decimal = Decimal(str(purity))
                if purity_decimal > Decimal("1.0"): # if written as 0-100 percentage
                    purity_decimal = purity_decimal / Decimal("100.0")
            
            # Unit conversions (troy ounces to grams)
            weight_grams = weight
            if unit == "ounces" or unit == "oz":
                weight_grams = weight * Decimal("31.1034768")
                
            pure_weight = weight_grams * purity_decimal
            spot_price_usd = get_commodity_spot_price(metal, force_refresh)
            
            # Convert to base currency
            fx_rate = get_exchange_rate("USD", base_currency, force_refresh)
            spot_price_base = spot_price_usd * fx_rate
            val_base = pure_weight * spot_price_base
            zakat_due = val_base * zakat_rate
            
            gross_zakatable_assets += val_base
            
            breakdown.append({
                "asset_class": "precious_metals",
                "label": f"{metal.capitalize()} ({weight} {unit})",
                "raw_value": float(weight),
                "value_base": float(val_base),
                "zakatable_value": float(val_base),
                "zakat_due": float(zakat_due),
                "rationale": (
                    f"Precious metals are subject to Zakat on their net pure weight value (Quran 9:34). "
                    f"Resolved spot price is ${spot_price_usd:.2f}/gram in USD. "
                    f"Pure weight: {pure_weight:,.2f}g. Net value in base currency is ${val_base:,.2f}, "
                    f"yielding ${zakat_due:,.2f} Zakat."
                )
            })
            
        # --- 3. PROCESS BUSINESS INVENTORY ---
        # Fiqh Reference: AAOIFI Shari'ah Standard No. 35 (Zakah), Section 4 (Zakat on Trade Goods / Urudh al-Tijarah)
        # See E-Standards Portal: https://aaoifi.com/e-standards/?lang=en
        # Inventory held for sale is valued at its wholesale market price on the Zakat anniversary.
        # See also NZF Business Assets Guide: https://nzf.org.uk/knowledge/business-zakat-guide/
        for inv_item in assets.get("business_inventory", []):
            value = Decimal(str(inv_item.get("value", 0.0)))
            curr = inv_item.get("currency", base_currency).strip().upper()
            
            rate = get_exchange_rate(curr, base_currency, force_refresh)
            val_base = value * rate
            zakat_due = val_base * zakat_rate
            
            gross_zakatable_assets += val_base
            
            breakdown.append({
                "asset_class": "business_inventory",
                "label": f"Business Inventory ({curr})",
                "raw_value": float(value),
                "value_base": float(val_base),
                "zakatable_value": float(val_base),
                "zakat_due": float(zakat_due),
                "rationale": (
                    f"Business inventory represents trade goods ('Urudh al-Tijarah) and is valued at market price "
                    f"(AAOIFI Standard No. 35, Sec. 4). Converted inventory value is ${val_base:,.2f}, "
                    f"yielding ${zakat_due:,.2f} Zakat."
                )
            })
            
        # --- 4. PROCESS REAL ESTATE ---
        # Hadith Reference: Sahih al-Bukhari 1464 - Personal use items (residences/slaves) are exempt from Zakat.
        # Link: https://sunnah.com/bukhari:1464
        # Fiqh Reference: AAOIFI Shari'ah Standard No. 35 (Zakah) Section 4 (Zakat on Real Estate)
        # See E-Standards: https://aaoifi.com/e-standards/?lang=en
        # Zakat is due on the asset value if held with intent to resell/flip (treated as trade goods),
        # but the property asset itself is exempt if held as a rental; only accumulated rental cash is subject to Zakat.
        # See also NZF Property Guide: https://nzf.org.uk/knowledge/zakat-on-property/
        for re_item in assets.get("real_estate", []):
            value = Decimal(str(re_item.get("value", 0.0)))
            curr = re_item.get("currency", base_currency).strip().upper()
            re_type = re_item.get("type", "primary").strip().lower()
            
            rate = get_exchange_rate(curr, base_currency, force_refresh)
            val_base = value * rate
            
            if re_type == "primary":
                zakatable_val = Decimal("0.0")
                zakat_due = Decimal("0.0")
                rationale = (
                    f"Primary residence is exempt from Zakat under personal use rules (Hadith Bukhari 1464). "
                    f"Value of ${val_base:,.2f} is excluded."
                )
            elif re_type == "rental":
                zakatable_val = Decimal("0.0")
                zakat_due = Decimal("0.0")
                rationale = (
                    f"Rental property asset value is exempt. Zakat is only due on accumulated rental revenues "
                    f"(entered under cash savings). Value of ${val_base:,.2f} is excluded."
                )
            elif re_type == "flip":
                zakatable_val = val_base
                zakat_due = val_base * zakat_rate
                gross_zakatable_assets += val_base
                rationale = (
                    f"Real estate held for flipping (capital gains) is classified as trade goods and is taxed on its full "
                    f"market value (AAOIFI Standard No. 35, Sec. 4). Converted value is ${val_base:,.2f}, yielding ${zakat_due:,.2f} Zakat."
                )
            else:
                zakatable_val = Decimal("0.0")
                zakat_due = Decimal("0.0")
                rationale = f"Unknown property type '{re_type}' is excluded by default."
                
            breakdown.append({
                "asset_class": "real_estate",
                "label": f"Property ({re_type.capitalize()})",
                "raw_value": float(value),
                "value_base": float(val_base),
                "zakatable_value": float(zakatable_val),
                "zakat_due": float(zakat_due),
                "rationale": rationale
            })
            
        # --- 5. PROCESS STOCKS ---
        # Fiqh Reference: AAOIFI Shari'ah Standard No. 35 (Zakah) (Zakat on Corporate Shares & Securities)
        # See E-Standards: https://aaoifi.com/e-standards/?lang=en
        # Zakat on equities varies entirely based on investor intent:
        # 1. Active Trading: Treated as trade goods (Urudh al-Tijarah) - Zakat is due on 100% of the current market value.
        #    See AAOIFI Standard No. 35, Section 4 (Zakah on Trade Goods).
        # 2. Passive Holding: Taxed only on the investor's share of Net Zakatable Assets (liquid assets minus liabilities).
        #    See AAOIFI Standard No. 35, item 4/2/4 (Pro-rata share of Net Zakatable Assets) and AMJA Declaration:
        #    https://www.amjaonline.org/declaration-articles/zakat-on-shares-and-investments/
        for stock_item in assets.get("stocks", []):
            ticker = stock_item.get("ticker", "").strip().upper()
            shares = Decimal(str(stock_item.get("shares", 0.0)))
            intent = stock_item.get("intent", "holding").strip().lower()
            
            try:
                # Call screener service
                stock_result = screener.screen_stock(
                    ticker=ticker,
                    standard_name=resolved_std,
                    denominator_override=resolved_denom,
                    force_refresh=force_refresh
                )
                
                price = Decimal(str(stock_result["price"]))
                market_value = price * shares
                
                # Fetch FX rate (most stocks from Yahoo are USD, check base)
                # Currently yfinance USD stock prices, convert USD -> base_currency
                fx_rate = get_exchange_rate("USD", base_currency, force_refresh)
                val_base = market_value * fx_rate
                
                zakat_info = stock_result["zakat"]
                comp = stock_result["compliance"]
                
                if intent == "trading":
                    zakatable_val = val_base
                    zakat_due = val_base * zakat_rate
                    gross_zakatable_assets += val_base
                    rationale = (
                        f"Active Trading Shares ({ticker}): Shares held with the intent to resell (trading inventory) "
                        f"are subject to Zakat on 100% of their current market value (AAOIFI Standard No. 35, Sec. 4). "
                        f"Market value in base currency is ${val_base:,.2f}, yielding ${zakat_due:,.2f} Zakat."
                    )
                else:
                    # Passive Holding: taxed on balance sheet liquid items
                    # Let's check if the user explicitly requested the 30% proxy method,
                    # or if the balance sheet data is empty (failed to load/fetch)
                    net_assets_total = Decimal(str(zakat_info["balance_sheet_method"]["net_zakatable_assets_total"]))
                    zakatable_asset_per_share = Decimal(str(zakat_info["balance_sheet_method"]["zakatable_asset_per_share"]))
                    
                    # We define "failed to load" if all liquid assets and current liabilities are zero
                    bs_breakdown = zakat_info.get("breakdown", {})
                    bs_missing = (
                        Decimal(str(bs_breakdown.get("cash_equivalents", 0))) == 0 and
                        Decimal(str(bs_breakdown.get("short_term_investments", 0))) == 0 and
                        Decimal(str(bs_breakdown.get("accounts_receivable", 0))) == 0 and
                        Decimal(str(bs_breakdown.get("inventory", 0))) == 0 and
                        Decimal(str(bs_breakdown.get("total_current_liabilities", 0))) == 0
                    )
                    
                    is_proxy_requested = use_proxy or settings.get("use_proxy") or False
                    
                    if is_proxy_requested or bs_missing:
                        # Use 30% Market Cap Proxy (Contemporary estimation endorsed by NZF and IFG)
                        # NZF Shares: https://nzf.org.uk/knowledge/zakat-on-shares/
                        # IFG Guide: https://www.islamicfinanceguru.com/articles/the-definitive-ifg-guide-to-zakat-on-investments
                        proxy_asset_per_share = Decimal(str(zakat_info["proxy_method_30pct"]["zakatable_asset_per_share"]))
                        zakatable_val_usd = proxy_asset_per_share * shares
                        zakatable_val = zakatable_val_usd * fx_rate
                        zakat_due = zakatable_val * zakat_rate
                        gross_zakatable_assets += zakatable_val
                        
                        if bs_missing:
                            rationale = (
                                f"Passive Holding Shares ({ticker}): Balance sheet data was unavailable or empty. "
                                f"Fell back to the contemporary 30% Market Cap Proxy (NZF/IFG guidelines). "
                                f"30% of price (${price:.2f}) is ${proxy_asset_per_share:.2f}/share. "
                                f"Zakatable value: ${zakatable_val:,.2f}, yielding ${zakat_due:,.2f} Zakat."
                            )
                        else:
                            rationale = (
                                f"Passive Holding Shares ({ticker}): Taxed using the requested 30% Market Cap Proxy method "
                                f"(NZF/IFG guidelines). 30% of price (${price:.2f}) is ${proxy_asset_per_share:.2f}/share. "
                                f"Zakatable value: ${zakatable_val:,.2f}, yielding ${zakat_due:,.2f} Zakat."
                            )
                    else:
                        # Use Balance Sheet Method (Pro-rata share of Net Zakatable Assets)
                        # AAOIFI Standard No. 35, item 4/2/4 - See E-Standards: https://aaoifi.com/e-standards/?lang=en
                        zakatable_val_usd = zakatable_asset_per_share * shares
                        zakatable_val = zakatable_val_usd * fx_rate
                        zakat_due = zakatable_val * zakat_rate
                        gross_zakatable_assets += zakatable_val
                        
                        if net_assets_total <= 0:
                            rationale = (
                                f"Passive Holding Shares ({ticker}): Taxed only on company's Net Zakatable Assets "
                                f"(AAOIFI Standard No. 35, item 4/2/4). Balance sheet shows a liquid asset deficit of "
                                f"${net_assets_total/Decimal('1e9'):,.2f}B (Current Liabilities exceed current assets), "
                                f"so the zakatable value is floored to $0.00."
                            )
                        else:
                            rationale = (
                                f"Passive Holding Shares ({ticker}): Taxed only on company's Net Zakatable Assets "
                                f"(Cash + Inventory + Receivables - Current Liabilities) (AAOIFI Standard No. 35, item 4/2/4). "
                                f"Proportionate net liquid assets portion is ${zakatable_asset_per_share:.4f} per share. "
                                f"Zakatable value: ${zakatable_val:,.2f}, yielding ${zakat_due:,.2f} Zakat."
                            )
                
                # Check Shariah compliance label for breakdown
                is_compliant = comp["is_compliant"]
                compliance_label = "Halal" if is_compliant else "Haram"
                
                breakdown.append({
                    "asset_class": "stocks",
                    "label": f"{ticker} ({compliance_label} - {intent.capitalize()})",
                    "raw_value": float(shares),
                    "value_base": float(val_base),
                    "zakatable_value": float(zakatable_val),
                    "zakat_due": float(zakat_due),
                    "rationale": rationale
                })
                
            except Exception as e:
                print(f"Failed to process stock {ticker} in portfolio calculator: {e}")
                # Inject error item
                breakdown.append({
                    "asset_class": "stocks",
                    "label": f"{ticker} (Error)",
                    "raw_value": float(shares),
                    "value_base": 0.0,
                    "zakatable_value": 0.0,
                    "zakat_due": 0.0,
                    "rationale": f"Skipped: Failed to fetch stock parameters ({str(e)})"
                })
                
        # --- 6. PROCESS LIABILITIES (DEDUCTIONS) ---
        # Fiqh Reference: AAOIFI Shari'ah Standard No. 35 (Zakah), Section 7 (Deductible Debts)
        # See E-Standards: https://aaoifi.com/e-standards/?lang=en
        # Immediate short-term debts (payable within 30 days or the current month, like trade payables or credit cards)
        # can be deducted from gross wealth. Long-term mortgage principals or future interest-bearing liabilities are excluded.
        # See also NZF Debt Guide: https://nzf.org.uk/knowledge/zakat-on-debt/
        allowed_liabilities = Decimal("0.0")
        for debt_item in liabilities.get("short_term_debts", []):
            amount = Decimal(str(debt_item.get("amount", 0.0)))
            curr = debt_item.get("currency", base_currency).strip().upper()
            debt_type = debt_item.get("type", "debt").strip()
            
            rate = get_exchange_rate(curr, base_currency, force_refresh)
            val_base = amount * rate
            allowed_liabilities += val_base
            
            breakdown.append({
                "asset_class": "liability",
                "label": f"{debt_type.capitalize()} ({curr})",
                "raw_value": float(amount),
                "value_base": float(val_base),
                "zakatable_value": float(-val_base),
                "zakat_due": 0.0,
                "rationale": (
                    f"Short-term liability deduction (AAOIFI Standard No. 35, Sec. 7). "
                    f"Deducted ${val_base:,.2f} in base currency from total Zakat wealth base."
                )
            })
            
        # --- 7. NISAB CHECK & FINALIZE ---
        # Hadith Reference (Silver Nisab): Sahih al-Bukhari 1447 - Silver Nisab threshold is 5 awquq (612.36g).
        # Link: https://sunnah.com/bukhari:1447
        # Hadith Reference (Gold Nisab): Sunan Abu Dawud 1572 - Gold Nisab is 20 dinars (87.48g).
        # Link: https://sunnah.com/abudawud:1572
        # Nisab guides: NZF Gold & Silver Guide: https://nzf.org.uk/knowledge/zakat-on-gold-and-silver/
        nisab_value_base = get_nisab_threshold(nisab_standard, base_currency, force_refresh)
        
        net_zakatable_wealth = gross_zakatable_assets - allowed_liabilities
        if net_zakatable_wealth < Decimal("0.0"):
            net_zakatable_wealth = Decimal("0.0")
            
        # Zakat due is only calculated if net wealth exceeds Nisab
        if net_zakatable_wealth >= nisab_value_base:
            is_nisab_met = True
            total_zakat_due = net_zakatable_wealth * zakat_rate
        else:
            is_nisab_met = False
            total_zakat_due = Decimal("0.0")
            
        # Round values for presentation
        gross_zakatable_assets = gross_zakatable_assets.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        allowed_liabilities = allowed_liabilities.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        net_zakatable_wealth = net_zakatable_wealth.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_zakat_due = total_zakat_due.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        nisab_value_base = nisab_value_base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Build new return dictionary
        result = {
            "settings": {
                "base_currency": base_currency,
                "nisab_standard": nisab_standard,
                "calendar_type": calendar_type,
                "zakat_rate": float(zakat_rate)
            },
            "nisab_threshold_used": float(Decimal("87.48") if nisab_standard == "gold" else Decimal("612.36")),
            "nisab_value_base": float(nisab_value_base),
            "is_nisab_met": is_nisab_met,
            "gross_zakatable_assets": float(gross_zakatable_assets),
            "allowed_liabilities": float(allowed_liabilities),
            "net_zakatable_wealth": float(net_zakatable_wealth),
            "total_zakat_due": float(total_zakat_due),
            "breakdown": breakdown
        }
        
        # Reconstruct old return keys for backward compatibility if holdings parameter was used
        if holdings is not None:
            total_market_value = Decimal("0.0")
            total_zakatable_value = Decimal("0.0")
            old_items = []
            for b_item in breakdown:
                if b_item["asset_class"] == "stocks":
                    total_market_value += Decimal(str(b_item["value_base"]))
                    total_zakatable_value += Decimal(str(b_item["zakatable_value"]))
                    
                    is_compliant = "Halal" in b_item["label"]
                    shares = Decimal(str(b_item["raw_value"]))
                    price = Decimal(str(b_item["value_base"])) / shares if shares > 0 else Decimal("0.0")
                    
                    old_items.append({
                        "ticker": b_item["label"].split()[0],
                        "company_name": b_item["label"].split()[0],
                        "shares": float(shares),
                        "price": float(price),
                        "market_value": float(b_item["value_base"]),
                        "is_compliant": is_compliant,
                        "status": "Compliant" if is_compliant else "Non-Compliant",
                        "zakatable_value": float(b_item["zakatable_value"]),
                        "zakatable_asset_per_share": float(Decimal(str(b_item["zakatable_value"])) / shares) if shares > 0 else 0.0,
                        "zakat_due_lunar": float(Decimal(str(b_item["zakatable_value"])) * LUNAR_RATE),
                        "zakat_due_solar": float(Decimal(str(b_item["zakatable_value"])) * SOLAR_RATE),
                        "method_used": "30% Market Cap Proxy" if use_proxy else "Balance Sheet Method",
                        "rationale": b_item["rationale"]
                    })
            
            result["total_market_value"] = float(total_market_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            result["total_zakatable_value"] = float(total_zakatable_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            result["total_zakat_due_lunar"] = float((total_zakatable_value * LUNAR_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            result["total_zakat_due_solar"] = float((total_zakatable_value * SOLAR_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            result["method_used"] = "30% Market Cap Proxy" if use_proxy else "Balance Sheet Method"
            result["items"] = old_items
            
        return result
