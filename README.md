# Zakatable — Shariah Stock Screener & Zakat Calculator API

Zakatable is a high-precision, open-source financial screening service and REST API designed to calculate Shariah compliance and Zakat metrics for US equities and multi-asset portfolios. It retrieves real-time financial statements and market pricing data (utilizing public Yahoo Finance endpoints via `yfinance` in Python) and structures calculations in accordance with contemporary Islamic jurisprudential (Fiqh) standards.

---

## 1. Theological & Jurisprudential Foundations

To ensure absolute theological and mathematical integrity, the calculations, screening rules, and asset routing thresholds in this API are mapped directly to standards issued by leading Islamic finance bodies, primarily the [Accounting and Auditing Organization for Islamic Financial Institutions (AAOIFI) E-Standards Portal](https://aaoifi.com/e-standards/?lang=en).

### A. Shariah Stock Screening Standards (AAOIFI Standard No. 21)
According to **AAOIFI Shari'ah Standard No. 21 (Financial Papers and Shares)** (available directly via [AAOIFI Shariah Standard No. 21](https://aaoifi.com/ss-21-financial-paper-shares-and-bonds/?lang=en)), investing in common stocks is permissible provided the company's business activities and financial structures satisfy specific quantitative and qualitative thresholds.

1.  **Business Activity Screen (Qualitative):** 
    *   The primary business of the corporation must be permissible (*halal*). Sectors offering conventional financial services (interest-bearing banking, conventional insurance), tobacco, alcohol, gambling, weapons/defense, adult entertainment, or non-halal food processing are prohibited.
    *   **Tolerable Impurity Limit:** Any non-compliant (haram) revenue generated from secondary or accidental activities must not exceed **5%** of the company's total revenue:
        $$\frac{\text{Non-Compliant Revenue}}{\text{Total Revenue}} < 5\%$$
        *Note: Any earnings derived from non-compliant sources must be "purified" (donated to charity) and cannot be kept or reinvested. See [AAOIFI Standard 21, Section 3/4](https://aaoifi.com/ss-21-financial-paper-shares-and-bonds/?lang=en).*
2.  **Financial Ratios Screen (Quantitative):**
    Because modern public companies operate within conventional interest-based economies, AAOIFI allows investment in companies with minor debt or cash balances, subject to strict limits (historically set at a maximum of **33%**):
    *   **Debt-to-Asset/Market Cap Screen:** The company's total interest-bearing debt must not exceed 33% of its valuation:
        $$\frac{\text{Total Interest-Bearing Debt}}{\text{Denominator}} < 33\%$$
    *   **Cash-to-Asset/Market Cap Screen:** The company's cash and interest-bearing securities must not exceed 33% of its valuation:
        $$\frac{\text{Cash} + \text{Interest-Bearing Securities}}{\text{Denominator}} < 33\%$$
    *   **Receivables-to-Asset/Market Cap Screen:** Accounts receivable must not exceed 33% of its valuation:
        $$\frac{\text{Accounts Receivable}}{\text{Denominator}} < 33\%$$
        *(Note: Some standards, such as the Dow Jones Islamic Market index, permit receivables up to 33%, whereas others like MSCI permit up to 33.33% and utilize total assets rather than market capitalization as the denominator. See the [MSCI Islamic Index Methodology](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Islamic_Index_Methodology_Nov2019.pdf) and [S&P Dow Jones Shariah Indices Methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-shariah-indices.pdf)).*

### B. Asset-Class Specific Routing Rules (AAOIFI Standard No. 35)
Calculating Zakat is governed by **AAOIFI Shari'ah Standard No. 35 (Zakah)**, which can be searched on the [AAOIFI E-Standards Portal](https://aaoifi.com/e-standards/?lang=en). The calculations apply rules differently across asset classes to ensure compliance:

#### 1. Cash & Liquidity
*   **Fiqh Rule:** Cash is a liquid medium of exchange and is 100% subject to Zakat.
*   **References:** [AAOIFI Shari'ah Standard No. 35, Section 2](https://aaoifi.com/e-standards/?lang=en) (Zakat on Cash & Receivables) and [NZF Cash Zakat Guide](https://nzf.org.uk/knowledge/zakat-on-cash/).
*   **Formula:** $\text{Zakatable Value} = \text{Cash Amount} \times \text{FX Rate to Base Currency}$.

#### 2. Precious Metals (Gold & Silver)
*   **Fiqh Rule:** Zakat is due on the pure weight of gold or silver owned.
*   **Citations:** Quranic warning in [Surah At-Tawbah 9:34](https://quran.com/9/34) ("And those who hoard gold and silver...") and Hadith rules in [Sunan Abu Dawud 1572](https://sunnah.com/abudawud:1572) establishing Nisab weights. Detailed guidance is available in the [NZF Gold & Silver Zakat Guide](https://nzf.org.uk/knowledge/zakat-on-gold-and-silver/).
*   **Formula:**
    $$\text{Pure Weight} = \text{Raw Weight} \times \frac{\text{Karat Purity}}{24}$$
    $$\text{Value} = \text{Pure Weight (grams)} \times \text{Live USD Price per gram} \times \text{FX Rate}$$

#### 3. Stocks (Intent-Based Routing)
Under the **AAOIFI Shari'ah Standard No. 35 (Zakah)**, Zakat on stocks differs entirely based on the investor's intention:
*   **Active Trading (Capital Gains):** If the shares are held with the intent to resell (trading inventory), they are classified as **trade goods (*Urudh al-Tijarah*)** and taxed at 100% of the current market value (AAOIFI Standard No. 35, Section 4).
*   **Passive Holding (Dividend Income):** If the shares are held long-term for dividend yield, they are taxed only on the company's **Net Zakatable Assets** (Cash + Receivables + Inventory - Current Liabilities) according to AAOIFI Standard No. 35, item 4/2/4 (Pro-rata share of Net Zakatable Assets) and the [Assembly of Muslim Jurists of America (AMJA) Declaration on Stocks Zakat](https://www.amjaonline.org/declaration-articles/zakat-on-shares-and-investments/). If the balance sheet shows a liquid asset deficit, the Zakat due is floored to zero.
*   **The 30% Proxy Heuristic:** If balance sheet data fails to fetch or is unavailable, we apply the contemporary 30% Market Cap Proxy fallback established by the [UK National Zakat Foundation (NZF) Guide on Shares](https://nzf.org.uk/knowledge/zakat-on-shares/) and [Islamic Finance Guru (IFG) Definitive Guide to Zakat on Investments](https://www.islamicfinanceguru.com/articles/the-definitive-ifg-guide-to-zakat-on-investments) where 30% of the stock price represents the zakatable asset base.

#### 4. Real Estate
*   **Fiqh Rule:** The calculation varies strictly based on property usage:
    *   `primary` (Residence): Exempt from Zakat. Hadith: [Sahih al-Bukhari 1464](https://sunnah.com/bukhari:1464) and [Sahih Muslim 982](https://sunnah.com/muslim:982a) (No Zakat on personal-use houses or belongings). See also [NZF Property Zakat Guide](https://nzf.org.uk/knowledge/zakat-on-property/).
    *   `rental` (Investment): The asset value of the rental property is exempt from Zakat. Only accumulated net cash savings from rental income are subject to Zakat. See [AAOIFI Standard No. 35, Section 4](https://aaoifi.com/e-standards/?lang=en) and [NZF Property Zakat Guide](https://nzf.org.uk/knowledge/zakat-on-property/).
    *   `flip` (Trading property): Taxed at 100% of current market value as trade goods (*Urudh al-Tijarah*). Reference: [AAOIFI Standard No. 35, Section 4](https://aaoifi.com/e-standards/?lang=en).
*   **Formula:** Handled according to intent parameters in Zakat calculation engine.

#### 5. Business Inventory
*   **Fiqh Rule:** Business inventory held for sale is valued at its current wholesale market price on the Zakat anniversary date and is 100% subject to Zakat. Reference: [AAOIFI Standard No. 35, Section 4](https://aaoifi.com/e-standards/?lang=en) and [NZF Business Assets Zakat Guide](https://nzf.org.uk/knowledge/business-zakat-guide/).

### C. Deductible Liabilities & Nisab Checking
*   **Liabilities Deduction:** Immediate, short-term liabilities (outstanding debts payable within the current month or 30 days) are subtracted from the gross wealth base. Long-term debts (like the remaining principal on a mortgage) are excluded. Reference: [AAOIFI Standard No. 35, Section 7](https://aaoifi.com/e-standards/?lang=en) (Deductible Debts) and [NZF Debt Zakat Guide](https://nzf.org.uk/knowledge/zakat-on-debt/).
*   **Nisab Check:** Zakat is only due if the user's `Net Zakatable Wealth` exceeds the Nisab threshold in their base currency:
    *   **Gold Standard:** 87.48 grams of pure gold. Hadith: [Sunan Abu Dawud 1572](https://sunnah.com/abudawud:1572).
    *   **Silver Standard:** 612.36 grams of pure silver. Hadith: [Sahih al-Bukhari 1447](https://sunnah.com/bukhari:1447) (No Zakat is due on less than 5 *awquq* of silver).
*   **Calendar adjustments:**
    *   **Lunar calendar Zakat rate:** **2.50%**. Hadith: [Sunan Ibn Majah 1790](https://sunnah.com/ibnmajah:1790).
    *   **Solar calendar Zakat rate:** Adjusted to **2.577%** ($2.5\% \times \frac{365.25}{354}$) to account for the extra 11 days of asset accumulation under Gregorian years. Reference: [AAOIFI Standard No. 35, Section 5/2/2](https://aaoifi.com/e-standards/?lang=en).

---

## 2. Technical Implementation & API Architecture

The application is structured as a modular Python package with a FastAPI REST API and a premium, glowing glassmorphism frontend served statically.

### Code Directories
*   **[calculator.py](file:///Users/aadil/Documents/Workspace/zakatable/zakatable/calculator.py):** Main Zakat rules calculation engine. Enforces strict `Decimal` high-precision arithmetic for all assets, currency conversions, and Nisab thresholds.
*   **[forex.py](file:///Users/aadil/Documents/Workspace/zakatable/zakatable/forex.py):** Queries Yahoo Finance exchange rates (e.g. `EURUSD=X`) to normalize all assets to the base currency. Uses an in-memory 1-hour cache.
*   **[commodities.py](file:///Users/aadil/Documents/Workspace/zakatable/zakatable/commodities.py):** Fetches live spot commodity prices per troy ounce using `GC=F` (Gold Futures) and `SI=F` (Silver Futures), converting ounce rates to gram rates.
*   **[screener.py](file:///Users/aadil/Documents/Workspace/zakatable/zakatable/screener.py):** Retrieves stock balance sheets and info details, applying qualitative and quantitative Shariah compliance screens.
*   **[cache.py](file:///Users/aadil/Documents/Workspace/zakatable/zakatable/cache.py):** File-based cache engine ensuring high performance and rate limit avoidance.
*   **[main.py](file:///Users/aadil/Documents/Workspace/zakatable/zakatable/api/main.py):** Houses FastAPI routes, Pydantic schemas, and launches the server.
*   **[static/](file:///Users/aadil/Documents/Workspace/zakatable/zakatable/api/static/):** Dashboard UI (`index.html`, `js/app.js`, `css/styles.css`).

---

## 3. API Endpoint Reference

### A. screen stock ticker
*   **Endpoint:** `GET /api/v1/screen/{ticker}`
*   **cURL Example:**
    ```bash
    curl -X 'GET' 'http://localhost:8000/api/v1/screen/AAPL?standard=aaoifi&denominator=market_cap&refresh=false' -H 'accept: application/json'
    ```

### B. Calculate Portfolio Zakat (New Structured Payload)
*   **Endpoint:** `POST /api/v1/calculate-portfolio`
*   **cURL Example:**
    ```bash
    curl -X 'POST' \
      'http://localhost:8000/api/v1/calculate-portfolio' \
      -H 'Content-Type: application/json' \
      -d '{
      "settings": {
        "base_currency": "USD",
        "nisab_standard": "silver",
        "calendar_type": "gregorian"
      },
      "assets": {
        "cash": [
          { "amount": 10000.00, "currency": "USD" },
          { "amount": 5000.00, "currency": "EUR" }
        ],
        "precious_metals": [
          { "metal": "gold", "weight": 20.0, "purity": 22.0, "unit": "grams" }
        ],
        "stocks": [
          { "ticker": "AAPL", "shares": 100, "intent": "holding" }
        ],
        "business_inventory": [
          { "value": 5000.00, "currency": "USD" }
        ],
        "real_estate": [
          { "value": 500000.00, "currency": "USD", "type": "primary" },
          { "value": 150000.00, "currency": "USD", "type": "flip" }
        ]
      },
      "liabilities": {
        "short_term_debts": [
          { "amount": 2000.00, "currency": "USD", "type": "credit_card" }
        ]
      }
    }'
    ```
*   **Example Response:**
    ```json
    {
      "settings": {
        "base_currency": "USD",
        "nisab_standard": "silver",
        "calendar_type": "gregorian",
        "zakat_rate": 0.02577
      },
      "nisab_threshold_used": 612.36,
      "nisab_value_base": 581.74,
      "is_nisab_met": true,
      "gross_zakatable_assets": 182070.50,
      "allowed_liabilities": 2000.00,
      "net_zakatable_wealth": 180070.50,
      "total_zakat_due": 4640.42,
      "breakdown": [
        {
          "asset_class": "cash",
          "label": "Cash (USD)",
          "raw_value": 10000.0,
          "value_base": 10000.0,
          "zakatable_value": 10000.0,
          "zakat_due": 257.7,
          "rationale": "Cash holdings are 100% subject to Zakat (AAOIFI Standard No. 35, Sec. 2). 10,000.00 USD converted to base currency is $10,000.00, yielding $257.70 Zakat at a gregorian Zakat rate of 2.577%."
        },
        {
          "asset_class": "precious_metals",
          "label": "Gold (20.0 grams)",
          "raw_value": 20.0,
          "value_base": 1375.0,
          "zakatable_value": 1375.0,
          "zakat_due": 35.43,
          "rationale": "Precious metals are subject to Zakat on their net pure weight value (Quran 9:34). Resolved spot price is $75.00/gram in USD. Pure weight: 18.33g. Net value in base currency is $1,375.00, yielding $35.43 Zakat."
        },
        ...
      ]
    }
    ```

---

## 4. Current Limitations & Risk Assessment

While Zakatable provides a robust, high-precision calculation infrastructure, developers should account for the following limitations:
1.  **Dependency on Unofficial Web-Scraping:** Yahoo Finance (`yfinance`) may change its public API endpoints or balance sheet styling, causing calculations to return zero or default.
2.  **Liability Deduction Assumptions:** By default, Yahoo Finance data does not differentiate between interest-bearing and interest-free short-term debt. Consequently, our balance sheet stock screening subtracts `Total Current Liabilities` instead of isolating interest-free current liabilities (like accounts payable), which may slightly underestimate the zakatable stock base of highly leveraged firms.

---

## 5. Launching the Application

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Start the server:**
    ```bash
    zakatable-api
    ```
    *Note: The server script is exposed as a command-line script in `pyproject.toml`.*
3.  **View UI & Docs:**
    *   Dashboard Home: [http://localhost:8000/](http://localhost:8000/)
    *   Interactive Swagger API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
