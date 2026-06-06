// --- State Management ---
let currentTicker = "AAPL";
let portfolioItems = [
    { type: "stocks", data: { ticker: "AAPL", shares: 100, intent: "holding" } },
    { type: "stocks", data: { ticker: "BAC", shares: 200, intent: "trading" } }
];
let useProxyForPortfolio = false;

// --- DOM Elements ---
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("ticker-search-input");
const dashboardSection = document.getElementById("dashboard-section");
const loader = document.getElementById("dashboard-loader");

// Settings Elements
const selectStandard = document.getElementById("select-compliance-standard");
const selectDenominator = document.getElementById("select-denominator");
const btnRecalculate = document.getElementById("btn-recalculate");

// Ticker Information DOM
const tickerBadge = document.getElementById("ticker-badge");
const companyTitle = document.getElementById("company-name-title");
const sectorIndustry = document.getElementById("company-sector-industry");
const complianceIndicator = document.getElementById("compliance-indicator");
const complianceIcon = document.getElementById("compliance-icon");
const complianceStatusText = document.getElementById("compliance-status-text");
const currentSharePrice = document.getElementById("current-share-price");
const businessSummaryText = document.getElementById("business-summary-text");
const businessActivityVerdict = document.getElementById("business-activity-verdict");

// Ratios DOM
const denominatorLabelDesc = document.getElementById("denominator-label-desc");
const ratioValDebt = document.getElementById("ratio-val-debt");
const ratioValCash = document.getElementById("ratio-val-cash");
const ratioValReceivables = document.getElementById("ratio-val-receivables");
const rawValDebt = document.getElementById("raw-val-debt");
const rawValCash = document.getElementById("raw-val-cash");
const rawValReceivables = document.getElementById("raw-val-receivables");
const progressBarDebt = document.getElementById("progress-bar-debt");
const progressBarCash = document.getElementById("progress-bar-cash");
const progressBarReceivables = document.getElementById("progress-bar-receivables");
const statusLblDebt = document.getElementById("status-lbl-debt");
const statusLblCash = document.getElementById("status-lbl-cash");
const statusLblReceivables = document.getElementById("status-lbl-receivables");

// Zakat DOM
const zakatTotalNetAssets = document.getElementById("zakat-total-net-assets");
const zakatAssetPerShare = document.getElementById("zakat-asset-per-share");
const zakatLunarPerShare = document.getElementById("zakat-lunar-per-share");
const zakatSolarPerShare = document.getElementById("zakat-solar-per-share");
const proxyAssetPerShare = document.getElementById("proxy-asset-per-share");
const proxyLunarPerShare = document.getElementById("proxy-lunar-per-share");
const proxySolarPerShare = document.getElementById("proxy-solar-per-share");

// Breakdown DOM
const breakdownCash = document.getElementById("val-breakdown-cash");
const breakdownInvestments = document.getElementById("val-breakdown-investments");
const breakdownReceivables = document.getElementById("val-breakdown-receivables");
const breakdownInventory = document.getElementById("val-breakdown-inventory");
const breakdownTotalRaw = document.getElementById("val-breakdown-total-raw");
const breakdownLiabilities = document.getElementById("val-breakdown-liabilities");

// Portfolio Summary DOM
const summaryGrossAssets = document.getElementById("summary-gross-assets");
const summaryAllowedLiabilities = document.getElementById("summary-allowed-liabilities");
const summaryNetWealth = document.getElementById("summary-net-wealth");
const summaryTotalZakatDue = document.getElementById("summary-total-zakat-due");
const summaryNisabValue = document.getElementById("summary-nisab-value");
const summaryZakatDueLabel = document.getElementById("summary-zakat-due-label");
const summaryNisabInfoLabel = document.getElementById("summary-nisab-info-label");
const portfolioComplianceAlert = document.getElementById("portfolio-compliance-alert");

// Portfolio Buttons
const btnToggleMethodBS = document.getElementById("btn-toggle-method-bs");
const btnToggleMethodProxy = document.getElementById("btn-toggle-method-proxy");
const btnClearPortfolio = document.getElementById("btn-clear-portfolio");
const portfolioTableBody = document.getElementById("portfolio-table-body");

// Collapsible Receipt DOM
const receiptToggle = document.getElementById("receipt-toggle");
const receiptContent = document.getElementById("receipt-content");
const receiptChevron = document.getElementById("receipt-chevron");

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    // Audit AAPL on load
    auditStock(currentTicker);
    
    // Setup initial portfolio calculations
    calculatePortfolio();
    
    // Bind Event Listeners
    searchForm.addEventListener("submit", handleSearchSubmit);
    btnRecalculate.addEventListener("click", () => auditStock(currentTicker));
    btnClearPortfolio.addEventListener("click", resetPortfolio);
    
    btnToggleMethodBS.addEventListener("click", () => setPortfolioMethod(false));
    btnToggleMethodProxy.addEventListener("click", () => setPortfolioMethod(true));
    
    // Bind Quick Tag Buttons
    document.querySelectorAll(".quick-tag-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const ticker = btn.getAttribute("data-ticker");
            searchInput.value = ticker;
            auditStock(ticker);
        });
    });

    // Bind API Tabs
    document.querySelectorAll(".api-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".api-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
        });
    });

    // Bind Asset Form Switch Tabs
    document.querySelectorAll(".asset-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".asset-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            
            const assetName = tab.getAttribute("data-asset");
            document.querySelectorAll(".asset-panel").forEach(panel => {
                panel.classList.remove("active");
            });
            document.getElementById(`panel-input-${assetName}`).classList.add("active");
        });
    });

    // Bind forms for asset inputs
    document.getElementById("form-add-cash").addEventListener("submit", (e) => {
        e.preventDefault();
        const amount = parseFloat(document.getElementById("cash-amount").value);
        const currency = document.getElementById("cash-currency").value;
        if (amount > 0) {
            portfolioItems.push({ type: "cash", data: { amount, currency } });
            document.getElementById("cash-amount").value = "";
            calculatePortfolio();
        }
    });

    document.getElementById("form-add-metals").addEventListener("submit", (e) => {
        e.preventDefault();
        const metal = document.getElementById("metal-type").value;
        const weight = parseFloat(document.getElementById("metal-weight").value);
        const unit = document.getElementById("metal-unit").value;
        const purity = parseFloat(document.getElementById("metal-purity").value);
        if (weight > 0) {
            portfolioItems.push({ type: "metals", data: { metal, weight, purity, unit } });
            document.getElementById("metal-weight").value = "";
            calculatePortfolio();
        }
    });

    document.getElementById("form-add-stocks").addEventListener("submit", (e) => {
        e.preventDefault();
        const ticker = document.getElementById("stock-ticker").value.trim().toUpperCase();
        const shares = parseFloat(document.getElementById("stock-shares").value);
        const intent = document.getElementById("stock-intent").value;
        if (ticker && shares > 0) {
            portfolioItems.push({ type: "stocks", data: { ticker, shares, intent } });
            document.getElementById("stock-ticker").value = "";
            document.getElementById("stock-shares").value = "";
            calculatePortfolio();
        }
    });

    document.getElementById("form-add-inventory").addEventListener("submit", (e) => {
        e.preventDefault();
        const value = parseFloat(document.getElementById("inventory-value").value);
        const currency = document.getElementById("inventory-currency").value;
        if (value > 0) {
            portfolioItems.push({ type: "inventory", data: { value, currency } });
            document.getElementById("inventory-value").value = "";
            calculatePortfolio();
        }
    });

    document.getElementById("form-add-realestate").addEventListener("submit", (e) => {
        e.preventDefault();
        const value = parseFloat(document.getElementById("realestate-value").value);
        const currency = document.getElementById("realestate-currency").value;
        const type = document.getElementById("realestate-type").value;
        if (value > 0) {
            portfolioItems.push({ type: "realestate", data: { value, currency, type } });
            document.getElementById("realestate-value").value = "";
            calculatePortfolio();
        }
    });

    document.getElementById("form-add-liabilities").addEventListener("submit", (e) => {
        e.preventDefault();
        const amount = parseFloat(document.getElementById("liability-amount").value);
        const currency = document.getElementById("liability-currency").value;
        const type = document.getElementById("liability-type").value.trim();
        if (amount > 0 && type) {
            portfolioItems.push({ type: "liabilities", data: { amount, currency, type } });
            document.getElementById("liability-amount").value = "";
            document.getElementById("liability-type").value = "";
            calculatePortfolio();
        }
    });

    // Bind settings dropdown changes
    document.getElementById("summary-base-currency").addEventListener("change", calculatePortfolio);
    document.getElementById("summary-nisab-standard").addEventListener("change", calculatePortfolio);
    document.getElementById("summary-calendar-type").addEventListener("change", calculatePortfolio);

    // Collapsible Receipt Toggle
    receiptToggle.addEventListener("click", () => {
        receiptContent.classList.toggle("hidden");
        if (receiptContent.classList.contains("hidden")) {
            receiptChevron.style.transform = "rotate(0deg)";
        } else {
            receiptChevron.style.transform = "rotate(180deg)";
        }
    });
});

// --- Search & Fetch Logic ---
function handleSearchSubmit(e) {
    e.preventDefault();
    const query = searchInput.value.trim().toUpperCase();
    if (query) {
        auditStock(query);
    }
}

async function auditStock(tickerSymbol) {
    currentTicker = tickerSymbol.toUpperCase();
    showLoader(true);
    
    const standard = selectStandard.value;
    const denominator = selectDenominator.value;
    
    try {
        const url = `/api/v1/screen/${currentTicker}?standard=${standard}&denominator=${denominator}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Stock symbol not found or data unavailable.");
        }
        
        const data = await response.json();
        renderAuditDashboard(data);
        showLoader(false);
    } catch (error) {
        showLoader(false);
        alert(`Error: ${error.message}`);
    }
}

function showLoader(show) {
    if (show) {
        loader.classList.remove("hidden");
        dashboardSection.classList.add("hidden");
    } else {
        loader.classList.add("hidden");
        dashboardSection.classList.remove("hidden");
    }
}

// --- Render Dashboard UI ---
function renderAuditDashboard(data) {
    // 1. Profile Information
    tickerBadge.textContent = data.ticker;
    companyTitle.textContent = data.company_name;
    sectorIndustry.textContent = `${data.sector} | ${data.industry}`;
    currentSharePrice.textContent = formatCurrency(data.price);
    businessSummaryText.textContent = data.compliance.business_screen.sector === "N/A" 
        ? "No corporate summary available." 
        : data.compliance.business_screen.reason;
        
    // Business Screen verdict box
    const bizScreen = data.compliance.business_screen;
    businessActivityVerdict.textContent = bizScreen.is_halal ? "Compliant" : "Non-Compliant";
    if (bizScreen.is_halal) {
        businessActivityVerdict.className = "rule-desc text-gradient";
    } else {
        businessActivityVerdict.className = "rule-desc text-danger";
        businessActivityVerdict.style.color = "var(--status-haram)";
    }

    // Overall Compliance Badge
    if (data.compliance.is_compliant) {
        complianceIndicator.className = "status-indicator halal";
        complianceIcon.className = "fa-solid fa-circle-check";
        complianceStatusText.textContent = "SHARIAH COMPLIANT";
    } else {
        complianceIndicator.className = "status-indicator haram";
        complianceIcon.className = "fa-solid fa-triangle-exclamation";
        complianceStatusText.textContent = "NON-COMPLIANT (HARAM)";
    }

    // 2. Financial Ratios Audit
    const denomUsed = data.compliance.denominator_used;
    denominatorLabelDesc.textContent = `Calculated against: ${denomUsed}`;
    
    const screens = data.compliance.financial_screens;
    
    // Debt
    renderRatioBar(
        progressBarDebt, 
        ratioValDebt, 
        rawValDebt, 
        statusLblDebt, 
        screens.debt.ratio, 
        screens.debt.threshold, 
        screens.debt.raw_debt, 
        screens.debt.passed
    );
    
    // Cash
    renderRatioBar(
        progressBarCash, 
        ratioValCash, 
        rawValCash, 
        statusLblCash, 
        screens.cash_and_investments.ratio, 
        screens.cash_and_investments.threshold, 
        screens.cash_and_investments.raw_cash, 
        screens.cash_and_investments.passed
    );
    
    // Receivables
    renderRatioBar(
        progressBarReceivables, 
        ratioValReceivables, 
        rawValReceivables, 
        statusLblReceivables, 
        screens.receivables.ratio, 
        screens.receivables.threshold, 
        screens.receivables.raw_receivables, 
        screens.receivables.passed
    );

    // 3. Zakat Valuation Methods
    const bsMethod = data.zakat.balance_sheet_method;
    zakatTotalNetAssets.textContent = formatCurrencyLarge(bsMethod.net_zakatable_assets_total);
    zakatAssetPerShare.textContent = formatCurrency(bsMethod.zakatable_asset_per_share, 4);
    zakatLunarPerShare.textContent = `$${bsMethod.zakat_due_per_share_lunar.toFixed(6)}`;
    zakatSolarPerShare.textContent = `$${bsMethod.zakat_due_per_share_solar.toFixed(6)}`;
    
    const proxyMethod = data.zakat.proxy_method_30pct;
    proxyAssetPerShare.textContent = formatCurrency(proxyMethod.zakatable_asset_per_share, 4);
    proxyLunarPerShare.textContent = `$${proxyMethod.zakat_due_per_share_lunar.toFixed(6)}`;
    proxySolarPerShare.textContent = `$${proxyMethod.zakat_due_per_share_solar.toFixed(6)}`;

    // 4. Liquid Breakdown Table
    const breakdown = data.zakat.breakdown;
    breakdownCash.textContent = formatCurrencyLarge(breakdown.cash_equivalents);
    breakdownInvestments.textContent = formatCurrencyLarge(breakdown.short_term_investments);
    breakdownReceivables.textContent = formatCurrencyLarge(breakdown.accounts_receivable);
    breakdownInventory.textContent = formatCurrencyLarge(breakdown.inventory);
    breakdownTotalRaw.textContent = formatCurrencyLarge(breakdown.total_zakatable_assets_raw);
    breakdownLiabilities.textContent = `-${formatCurrencyLarge(breakdown.total_current_liabilities)}`;
}

function renderRatioBar(barElem, valTextElem, rawValText, statusText, ratio, threshold, rawValue, passed) {
    const percentage = ratio * 100;
    valTextElem.textContent = `${percentage.toFixed(2)}%`;
    rawValText.textContent = `Value: ${formatCurrencyLarge(rawValue)}`;
    
    // Cap visual width at 100%
    const visualWidth = Math.min(percentage, 100);
    barElem.style.width = `${visualWidth}%`;
    
    if (passed) {
        barElem.className = "progress-bar passed";
        statusText.textContent = "Passed";
        statusText.className = "status-lbl passed";
    } else {
        barElem.className = "progress-bar failed";
        statusText.textContent = "Failed";
        statusText.className = "status-lbl failed";
    }
}

// --- Portfolio Planner Logic ---
function getPayloadFromItems() {
    const baseCurrency = document.getElementById("summary-base-currency").value;
    const nisabStandard = document.getElementById("summary-nisab-standard").value;
    const calendarType = document.getElementById("summary-calendar-type").value;
    
    const payload = {
        settings: {
            base_currency: baseCurrency,
            nisab_standard: nisabStandard,
            calendar_type: calendarType,
            use_proxy: useProxyForPortfolio
        },
        assets: {
            cash: [],
            precious_metals: [],
            stocks: [],
            business_inventory: [],
            real_estate: []
        },
        liabilities: {
            short_term_debts: []
        }
    };
    
    portfolioItems.forEach(item => {
        if (item.type === "cash") {
            payload.assets.cash.push(item.data);
        } else if (item.type === "metals") {
            payload.assets.precious_metals.push(item.data);
        } else if (item.type === "stocks") {
            payload.assets.stocks.push(item.data);
        } else if (item.type === "inventory") {
            payload.assets.business_inventory.push(item.data);
        } else if (item.type === "realestate") {
            payload.assets.real_estate.push(item.data);
        } else if (item.type === "liabilities") {
            payload.liabilities.short_term_debts.push(item.data);
        }
    });
    
    return payload;
}

async function calculatePortfolio() {
    if (portfolioItems.length === 0) {
        renderEmptyPortfolio();
        return;
    }
    
    const payload = getPayloadFromItems();
    
    try {
        const response = await fetch("/api/v1/calculate-portfolio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error("Failed to calculate portfolio metrics.");
        }
        
        const result = await response.json();
        
        // Render portfolio table rows paired with calculated values
        renderPortfolioTable(result);
        
        // Render Summary Stats
        const baseCurrency = payload.settings.base_currency;
        summaryGrossAssets.textContent = formatCurrency(result.gross_zakatable_assets, 2, baseCurrency);
        summaryAllowedLiabilities.textContent = `-${formatCurrency(result.allowed_liabilities, 2, baseCurrency)}`;
        summaryNetWealth.textContent = formatCurrency(result.net_zakatable_wealth, 2, baseCurrency);
        summaryTotalZakatDue.textContent = formatCurrency(result.total_zakat_due, 2, baseCurrency);
        
        const calendarLabel = payload.settings.calendar_type === "gregorian" ? "Solar (2.577%)" : "Lunar (2.5%)";
        summaryZakatDueLabel.textContent = `Total Zakat Due (${calendarLabel})`;
        
        const nisabMetalLabel = payload.settings.nisab_standard.charAt(0).toUpperCase() + payload.settings.nisab_standard.slice(1);
        summaryNisabInfoLabel.textContent = `Nisab Threshold (${nisabMetalLabel} Standard)`;
        summaryNisabValue.textContent = `${formatCurrency(result.nisab_value_base, 2, baseCurrency)} (based on ${result.nisab_threshold_used}g)`;
        
        // Render compliance alerts and collapsible receipt
        portfolioComplianceAlert.classList.remove("hidden");
        if (result.is_nisab_met) {
            portfolioComplianceAlert.className = "portfolio-compliance-alert alert-success";
            portfolioComplianceAlert.innerHTML = `<i class="fa-solid fa-circle-check"></i>
                <span>Nisab Met. Zakat of ${formatCurrency(result.total_zakat_due, 2, baseCurrency)} is due on net wealth.</span>`;
        } else {
            portfolioComplianceAlert.className = "portfolio-compliance-alert alert-warning";
            portfolioComplianceAlert.innerHTML = `<i class="fa-solid fa-circle-info"></i>
                <span>Nisab Not Met. Net wealth of ${formatCurrency(result.net_zakatable_wealth, 2, baseCurrency)} is below the threshold. No Zakat is due.</span>`;
        }
        
        renderReceipt(result.breakdown);
        
    } catch (error) {
        console.error("Portfolio error:", error);
    }
}

function renderPortfolioTable(summary) {
    portfolioTableBody.innerHTML = "";
    
    if (portfolioItems.length === 0) {
        renderEmptyPortfolio();
        return;
    }
    
    const baseCurrency = document.getElementById("summary-base-currency").value;
    const classIndices = {
        cash: 0,
        metals: 0,
        stocks: 0,
        inventory: 0,
        realestate: 0,
        liabilities: 0
    };
    
    portfolioItems.forEach((item, index) => {
        let matchClass = item.type;
        if (item.type === "metals") matchClass = "precious_metals";
        if (item.type === "inventory") matchClass = "business_inventory";
        if (item.type === "realestate") matchClass = "real_estate";
        if (item.type === "liabilities") matchClass = "liability";
        
        const classItems = summary.breakdown.filter(b => b.asset_class === matchClass);
        const bItem = classItems[classIndices[item.type]];
        classIndices[item.type]++;
        
        if (!bItem) return;
        
        const row = document.createElement("tr");
        
        let label = bItem.label;
        let classLabel = item.type.toUpperCase();
        let originalValueLabel = "";
        
        if (item.type === "cash") {
            originalValueLabel = `${item.data.amount.toLocaleString(undefined, {minimumFractionDigits: 2})} ${item.data.currency}`;
            classLabel = "CASH";
        } else if (item.type === "metals") {
            originalValueLabel = `${item.data.weight} ${item.data.unit} (${item.data.purity}K)`;
            classLabel = "METAL";
        } else if (item.type === "stocks") {
            originalValueLabel = `${item.data.shares.toLocaleString()} Shares`;
            classLabel = "STOCK";
        } else if (item.type === "inventory") {
            originalValueLabel = `${item.data.value.toLocaleString(undefined, {minimumFractionDigits: 2})} ${item.data.currency}`;
            classLabel = "INVENTORY";
        } else if (item.type === "realestate") {
            originalValueLabel = `${item.data.value.toLocaleString(undefined, {minimumFractionDigits: 2})} ${item.data.currency}`;
            classLabel = `REAL ESTATE (${item.data.type.toUpperCase()})`;
        } else if (item.type === "liabilities") {
            originalValueLabel = `${item.data.amount.toLocaleString(undefined, {minimumFractionDigits: 2})} ${item.data.currency}`;
            classLabel = "DEBT";
        }
        
        row.innerHTML = `
            <td><strong>${label}</strong></td>
            <td><span class="badge" style="background: rgba(255,255,255,0.05); border: 1px solid var(--glass-border); color: var(--text-secondary); box-shadow: none;">${classLabel}</span></td>
            <td>${originalValueLabel}</td>
            <td>${formatCurrency(bItem.value_base, 2, baseCurrency)}</td>
            <td style="color: ${bItem.zakatable_value < 0 ? 'var(--status-haram)' : 'var(--text-primary)'}">${formatCurrency(bItem.zakatable_value, 2, baseCurrency)}</td>
            <td><strong>${formatCurrency(bItem.zakat_due, 2, baseCurrency)}</strong></td>
            <td>
                <button class="btn-delete-item" onclick="removePortfolioItem(${index})" title="Remove Item">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </td>
        `;
        portfolioTableBody.appendChild(row);
    });
}

function renderReceipt(breakdown) {
    receiptContent.innerHTML = "";
    
    if (!breakdown || breakdown.length === 0) {
        receiptContent.innerHTML = "<p style='color: var(--text-muted); font-size: 0.8rem;'>No items to show.</p>";
        return;
    }
    
    const baseCurrency = document.getElementById("summary-base-currency").value;
    
    breakdown.forEach(item => {
        const itemDiv = document.createElement("div");
        itemDiv.className = "receipt-item";
        
        const dueLabel = item.zakat_due > 0 ? formatCurrency(item.zakat_due, 2, baseCurrency) : "$0.00";
        
        itemDiv.innerHTML = `
            <div class="receipt-item-title">
                <span>${item.label}</span>
                <span>Due: ${dueLabel}</span>
            </div>
            <div class="receipt-item-desc">${item.rationale}</div>
        `;
        receiptContent.appendChild(itemDiv);
    });
}

function renderEmptyPortfolio() {
    portfolioTableBody.innerHTML = `
        <tr class="empty-state">
            <td colspan="7">No items in calculator. Add assets or debts above to calculate Zakat.</td>
        </tr>
    `;
    summaryGrossAssets.textContent = "$0.00";
    summaryAllowedLiabilities.textContent = "-$0.00";
    summaryNetWealth.textContent = "$0.00";
    summaryTotalZakatDue.textContent = "$0.00";
    summaryNisabValue.textContent = "$0.00";
    portfolioComplianceAlert.classList.add("hidden");
    receiptContent.innerHTML = "<p style='color: var(--text-muted); font-size: 0.8rem;'>No items to show.</p>";
}

// Global scope binds for row click deletion
window.removePortfolioItem = function(index) {
    portfolioItems.splice(index, 1);
    calculatePortfolio();
};

function resetPortfolio() {
    portfolioItems = [];
    renderEmptyPortfolio();
}

function setPortfolioMethod(useProxy) {
    useProxyForPortfolio = useProxy;
    if (useProxy) {
        btnToggleMethodProxy.classList.add("active");
        btnToggleMethodBS.classList.remove("active");
    } else {
        btnToggleMethodBS.classList.add("active");
        btnToggleMethodProxy.classList.remove("active");
    }
    calculatePortfolio();
}

// --- Format Utilities ---
function formatCurrency(val, decimals = 2, currencyCode = 'USD') {
    if (val === undefined || val === null || isNaN(val)) return "$0.00";
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currencyCode,
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(val);
}

function formatCurrencyLarge(val) {
    if (val === undefined || val === null || isNaN(val)) return "$0.00";
    if (Math.abs(val) >= 1e9) {
        return `$${(val / 1e9).toFixed(2)}B`;
    } else if (Math.abs(val) >= 1e6) {
        return `$${(val / 1e6).toFixed(2)}M`;
    }
    return formatCurrency(val, 2);
}
