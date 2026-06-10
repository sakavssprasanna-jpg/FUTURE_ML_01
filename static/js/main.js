// Executive Sales Forecasting Dashboard - Frontend Application Logic

// Global State
let dashboardData = null;
let forecastData = null;
let insightsData = null;
let activeTab = 'overview';
let activeHorizon = 90; // Default future forecast horizon

// Chart instances for dynamic resizing & updates
let charts = {};

// Theme styling helper
function getThemeColors() {
    const isLight = document.body.classList.contains('light-theme');
    return {
        text: isLight ? '#475569' : '#94a3b8',
        grid: isLight ? 'rgba(15, 23, 42, 0.05)' : 'rgba(255, 255, 255, 0.05)',
        accent: '#0d9488',
        sales: isLight ? '#2563eb' : '#3b82f6',
        profit: isLight ? '#059669' : '#10b981',
        forecast: isLight ? '#7c3aed' : '#8b5cf6',
        bound: isLight ? 'rgba(13, 148, 136, 0.1)' : 'rgba(13, 148, 136, 0.15)',
        tooltipBg: isLight ? 'rgba(255, 255, 255, 0.9)' : 'rgba(18, 25, 41, 0.9)',
        tooltipBorder: isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.08)',
        tooltipText: isLight ? '#0f172a' : '#f8fafc'
    };
}

// ------------------ ON APPLICATION INITIALIZATION ------------------
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    setupEventListeners();
    showLoading(true);
    
    try {
        // 1. Fetch EDA Dashboard Data & Insights in parallel
        const [dashRes, insightsRes] = await Promise.all([
            fetch('/api/dashboard-data'),
            fetch('/api/insights')
        ]);
        
        dashboardData = await dashRes.json();
        insightsData = await insightsRes.json();
        
        // Populate static components from EDA & Insights first
        populateEDADOM();
        populateInsightsDOM();
        
        // 2. Fetch Forecasting Model details (may take 1-2s as models compile)
        const forecastRes = await fetch('/api/forecast');
        forecastData = await forecastRes.json();
        
        // Populate Forecast-dependent widgets
        populateForecastDOM();
        
        // Render all initial charts
        renderAllCharts();
        
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        alert('Error loading dashboard data. Please check if the Flask server is running.');
    } finally {
        showLoading(false);
    }
}

// ------------------ EVENT LISTENERS & NAVIGATION ------------------
function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = item.getAttribute('data-tab');
            switchTab(tabId);
        });
    });

    // Theme toggle
    const themeBtn = document.getElementById('theme-toggle');
    themeBtn.addEventListener('click', toggleTheme);

    // Horizon toggle (30 vs 90 days)
    document.querySelectorAll('.toggle-chart-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.toggle-chart-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeHorizon = parseInt(btn.getAttribute('data-horizon'));
            updateFutureForecastChart();
        });
    });
}

function switchTab(tabId) {
    activeTab = tabId;
    
    // Update navigation items active class
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('data-tab') === tabId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Show selected tab content, hide others
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tabId}`).classList.add('active');

    // Update Header labels
    const titleEl = document.getElementById('page-title');
    const subtitleEl = document.getElementById('page-subtitle');
    
    const titles = {
        'overview': { title: 'Executive Summary', sub: 'Historical performance and projected sales growth' },
        'eda': { title: 'Historical Exploratory Data Analysis', sub: 'Deep-dive insights from retail transactions log' },
        'forecasting': { title: 'Machine Learning Forecasting', sub: 'Model comparison matrix and statistical validation' },
        'insights': { title: 'Strategic Business Insights', sub: 'Inventory allocations and revenue growth opportunities' },
        'exports': { title: 'Executive Export Center', sub: 'Download reporting metrics in corporate file formats' }
    };
    
    titleEl.textContent = titles[tabId].title;
    subtitleEl.textContent = titles[tabId].sub;

    // Redraw charts to prevent layout bugs
    setTimeout(() => {
        Object.values(charts).forEach(chart => chart.resize());
    }, 50);
}

function toggleTheme() {
    const body = document.body;
    const themeText = document.getElementById('theme-text');
    const themeIcon = document.querySelector('#theme-toggle i');
    
    if (body.classList.contains('light-theme')) {
        body.classList.remove('light-theme');
        themeText.textContent = 'Light Mode';
        themeIcon.className = 'fa-solid fa-sun';
    } else {
        body.classList.add('light-theme');
        themeText.textContent = 'Dark Mode';
        themeIcon.className = 'fa-solid fa-moon';
    }
    
    // Dynamically update charts themes
    updateChartsThemes();
}

function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (show) {
        overlay.classList.add('active');
    } else {
        overlay.classList.remove('active');
    }
}

// ------------------ POPULATE DOM DATA ------------------

function populateEDADOM() {
    // KPI metrics
    document.getElementById('metric-total-sales').textContent = formatCurrency(dashboardData.total_sales);
    document.getElementById('metric-total-profit').textContent = formatCurrency(dashboardData.total_profit);
    
    const profitMargin = (dashboardData.total_profit / dashboardData.total_sales) * 100;
    document.getElementById('metric-profit-margin').textContent = `Margin: ${profitMargin.toFixed(1)}%`;
    
    // Top Products Table
    const tableBody = document.querySelector('#top-products-table tbody');
    tableBody.innerHTML = '';
    
    dashboardData.top_products.forEach((prod, index) => {
        const margin = (prod.Profit / prod.Sales) * 100;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>#${index + 1}</strong></td>
            <td title="${prod['Product Name']}">${truncateText(prod['Product Name'], 48)}</td>
            <td>${formatCurrency(prod.Sales)}</td>
            <td>${prod.Quantity} units</td>
            <td>${formatCurrency(prod.Profit)}</td>
            <td><span class="badge ${margin >= 15 ? 'badge-success' : 'badge-neutral'}">${margin.toFixed(1)}%</span></td>
        `;
        tableBody.appendChild(row);
    });
}

function populateInsightsDOM() {
    // Market analysis cards on Insights page
    const ins = insightsData;
    document.getElementById('insight-category-best').textContent = ins.best_category.name;
    document.getElementById('insight-category-sales').textContent = formatCurrency(ins.best_category.sales);
    document.getElementById('insight-category-profit').textContent = formatCurrency(ins.best_category.profit);
    document.getElementById('insight-category-margin').textContent = `${(ins.best_category.margin * 100).toFixed(1)}%`;
    
    document.getElementById('insight-region-best').textContent = ins.best_region.name;
    document.getElementById('insight-region-sales').textContent = formatCurrency(ins.best_region.sales);
    
    document.getElementById('insight-season-peak').textContent = ins.seasonality.peak_month;
    document.getElementById('insight-season-desc').textContent = ins.seasonality.description;
    
    // Populate recommendations list
    const recList = document.getElementById('recommendations-list');
    recList.innerHTML = '';
    
    const icons = [
        'fa-solid fa-boxes-stacked',       // Inventory
        'fa-solid fa-map-location-dot',    // Regional Marketing
        'fa-solid fa-percent',             // Margin Optimization
        'fa-solid fa-hand-holding-dollar'  // Revenue Projections
    ];
    
    ins.recommendations.forEach((rec, idx) => {
        const parts = rec.split(':');
        const title = parts[0];
        const text = parts[1];
        
        const item = document.createElement('div');
        item.className = 'rec-item';
        item.innerHTML = `
            <div class="rec-icon">
                <i class="${icons[idx] || 'fa-solid fa-circle-chevron-right'}"></i>
            </div>
            <div class="rec-text">
                <h5>${title}</h5>
                <p>${text}</p>
            </div>
        `;
        recList.appendChild(item);
    });
    
    // Overview tab recommendation highlight
    document.getElementById('exec-top-rec').textContent = ins.recommendations[0];
}

function populateForecastDOM() {
    const fc = forecastData;
    const bestModel = fc.best_model;
    const bestModelMetrics = fc.metrics[bestModel];
    
    // Status Bar & Overview Card metrics
    document.getElementById('model-status').textContent = `Best Model: ${bestModel}`;
    document.getElementById('forecast-model-name').textContent = `Model: ${bestModel}`;
    document.getElementById('exec-best-model').textContent = bestModel;
    
    const total30Forecast = fc.forecast_30.forecast.reduce((a, b) => a + b, 0);
    const total90Forecast = fc.forecast_90.forecast.reduce((a, b) => a + b, 0);
    
    document.getElementById('metric-forecasted-sales').textContent = formatCurrency(total90Forecast);
    document.getElementById('exec-30-sales').textContent = formatCurrency(total30Forecast);
    document.getElementById('exec-90-sales').textContent = formatCurrency(total90Forecast);
    
    // Read the precomputed weekly aggregated forecast accuracy from API
    const accuracy = fc.accuracy;
    document.getElementById('metric-accuracy').textContent = `${accuracy.toFixed(1)}%`;
    
    // Model Comparison Matrix Table
    const comparisonBody = document.querySelector('#model-comparison-table tbody');
    comparisonBody.innerHTML = '';
    
    Object.keys(fc.metrics).forEach(modelName => {
        const metrics = fc.metrics[modelName];
        const isBest = modelName === bestModel;
        const row = document.createElement('tr');
        if (isBest) row.style.backgroundColor = 'var(--accent-glow)';
        
        row.innerHTML = `
            <td><strong>${modelName}</strong></td>
            <td>${formatCurrency(metrics.MAE)}</td>
            <td>${formatCurrency(metrics.RMSE)}</td>
            <td>${metrics.R2.toFixed(4)}</td>
            <td><span class="badge ${isBest ? 'badge-success' : 'badge-neutral'}">${isBest ? 'Selected' : 'Evaluated'}</span></td>
        `;
        comparisonBody.appendChild(row);
    });
    
    // Selected Model Profile card
    document.getElementById('profile-name').textContent = bestModel;
    document.getElementById('profile-mae').textContent = formatCurrency(bestModelMetrics.MAE);
    document.getElementById('profile-rmse').textContent = formatCurrency(bestModelMetrics.RMSE);
    document.getElementById('profile-r2').textContent = bestModelMetrics.R2.toFixed(4);
    
    const profileFeatures = document.getElementById('profile-features');
    profileFeatures.innerHTML = '';
    
    const features = {
        'Linear Regression': ['Trend (Growth gradient baseline)', 'Quarter & Year temporal factors', 'Weekend holiday factors'],
        'Random Forest': ['Seasonal cycle components (sine/cosine)', 'Trend trajectory days elapsed', 'Week of year index'],
        'XGBoost': ['Cyclical sine/cosine day-of-year features', 'Relative week-number patterns', 'Segment category variations']
    };
    
    (features[bestModel] || ['Trend components', 'Seasonality indicators']).forEach(feat => {
        const li = document.createElement('li');
        li.textContent = feat;
        profileFeatures.appendChild(li);
    });
}

// ------------------ CHART GENERATION (CHART.JS) ------------------

function renderAllCharts() {
    renderFutureForecastChart();
    renderMonthlyTrendChart();
    renderProfitTrendChart();
    renderCategoryChart();
    renderRegionChart();
    renderForecastVsActualChart();
}

function updateChartsThemes() {
    const c = getThemeColors();
    
    Object.values(charts).forEach(chart => {
        // Update grid line colors
        if (chart.options.scales) {
            if (chart.options.scales.x) {
                chart.options.scales.x.grid.color = c.grid;
                chart.options.scales.x.ticks.color = c.text;
            }
            if (chart.options.scales.y) {
                chart.options.scales.y.grid.color = c.grid;
                chart.options.scales.y.ticks.color = c.text;
            }
            if (chart.options.scales.y1) {
                chart.options.scales.y1.grid.color = c.grid;
                chart.options.scales.y1.ticks.color = c.text;
            }
        }
        
        // Update legend title color
        if (chart.options.plugins && chart.options.plugins.legend) {
            chart.options.plugins.legend.labels.color = c.text;
        }
        
        // Update custom tooltip options
        if (chart.options.plugins && chart.options.plugins.tooltip) {
            chart.options.plugins.tooltip.backgroundColor = c.tooltipBg;
            chart.options.plugins.tooltip.titleColor = c.tooltipText;
            chart.options.plugins.tooltip.bodyColor = c.tooltipText;
            chart.options.plugins.tooltip.borderColor = c.tooltipBorder;
        }
        
        chart.update();
    });
}

// 1. Future Forecast Chart
function renderFutureForecastChart() {
    const ctx = document.getElementById('futureForecastChart').getContext('2d');
    const c = getThemeColors();
    
    // We aggregate predictions weekly to make the chart look super smooth and clean
    const fc = forecastData[`forecast_${activeHorizon}`];
    const weeklyData = aggregateWeekly(fc.dates, fc.forecast, fc.lower_bound, fc.upper_bound);
    
    // Create soft gradients
    const forecastGrad = ctx.createLinearGradient(0, 0, 0, 400);
    forecastGrad.addColorStop(0, 'rgba(139, 92, 246, 0.4)');
    forecastGrad.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

    charts.futureForecast = new Chart(ctx, {
        type: 'line',
        data: {
            labels: weeklyData.dates,
            datasets: [
                {
                    label: 'Projected Sales',
                    data: weeklyData.forecast,
                    borderColor: c.forecast,
                    borderWidth: 3,
                    pointRadius: 2,
                    tension: 0.35,
                    fill: true,
                    backgroundColor: forecastGrad
                },
                {
                    label: 'Lower Bound (95% CI)',
                    data: weeklyData.lower,
                    borderColor: 'transparent',
                    pointRadius: 0,
                    tension: 0.35,
                    fill: false
                },
                {
                    label: '95% Confidence boundary',
                    data: weeklyData.upper,
                    borderColor: 'transparent',
                    pointRadius: 0,
                    tension: 0.35,
                    fill: '-1', // Fill area between lower and upper
                    backgroundColor: c.bound
                }
            ]
        },
        options: getCommonChartOptions('Timeline', 'Sales ($)', false)
    });
}

function updateFutureForecastChart() {
    const chart = charts.futureForecast;
    if (!chart) return;
    
    const fc = forecastData[`forecast_${activeHorizon}`];
    const weeklyData = aggregateWeekly(fc.dates, fc.forecast, fc.lower_bound, fc.upper_bound);
    
    chart.data.labels = weeklyData.dates;
    chart.data.datasets[0].data = weeklyData.forecast;
    chart.data.datasets[1].data = weeklyData.lower;
    chart.data.datasets[2].data = weeklyData.upper;
    
    chart.update();
}

// 2. Historical Monthly Sales Trend
function renderMonthlyTrendChart() {
    const ctx = document.getElementById('monthlyTrendChart').getContext('2d');
    const c = getThemeColors();
    
    const labels = dashboardData.monthly_trend.map(d => formatYearMonth(d.YearMonth));
    const sales = dashboardData.monthly_trend.map(d => d.Sales);
    
    const grad = ctx.createLinearGradient(0, 0, 0, 300);
    grad.addColorStop(0, 'rgba(59, 130, 246, 0.35)');
    grad.addColorStop(1, 'rgba(59, 130, 246, 0.0)');
    
    charts.monthlyTrend = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Monthly Sales',
                data: sales,
                borderColor: c.sales,
                borderWidth: 3,
                pointBackgroundColor: c.sales,
                pointRadius: 3,
                tension: 0.4,
                fill: true,
                backgroundColor: grad
            }]
        },
        options: getCommonChartOptions('Timeline', 'Sales ($)', true)
    });
}

// 3. Profit Trend Chart
function renderProfitTrendChart() {
    const ctx = document.getElementById('profitTrendChart').getContext('2d');
    const c = getThemeColors();
    
    const labels = dashboardData.monthly_trend.map(d => formatYearMonth(d.YearMonth));
    const profit = dashboardData.monthly_trend.map(d => d.Profit);
    
    const grad = ctx.createLinearGradient(0, 0, 0, 300);
    grad.addColorStop(0, 'rgba(16, 185, 129, 0.35)');
    grad.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
    
    charts.profitTrend = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Monthly Profit',
                data: profit,
                borderColor: c.profit,
                borderWidth: 3,
                pointBackgroundColor: c.profit,
                pointRadius: 3,
                tension: 0.4,
                fill: true,
                backgroundColor: grad
            }]
        },
        options: getCommonChartOptions('Timeline', 'Profit ($)', true)
    });
}

// 4. Sales by Category (Grouped Dual-Axis Bar)
function renderCategoryChart() {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    const c = getThemeColors();
    
    const labels = dashboardData.sales_by_category.map(d => d.Category);
    const sales = dashboardData.sales_by_category.map(d => d.Sales);
    const profit = dashboardData.sales_by_category.map(d => d.Profit);
    
    charts.category = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Sales',
                    data: sales,
                    backgroundColor: 'rgba(59, 130, 246, 0.75)',
                    borderColor: c.sales,
                    borderWidth: 1,
                    borderRadius: 6,
                    yAxisID: 'y'
                },
                {
                    label: 'Total Profit',
                    data: profit,
                    backgroundColor: 'rgba(16, 185, 129, 0.75)',
                    borderColor: c.profit,
                    borderWidth: 1,
                    borderRadius: 6,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: c.grid },
                    ticks: { color: c.text, font: { family: 'Plus Jakarta Sans' } }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    grid: { color: c.grid },
                    ticks: { 
                        color: c.text, 
                        font: { family: 'Plus Jakarta Sans' },
                        callback: value => '$' + value / 1000 + 'k'
                    },
                    title: { display: true, text: 'Sales ($)', color: c.text, font: { family: 'Plus Jakarta Sans', weight: 'bold' } }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    grid: { drawOnChartArea: false }, // Only draw grid lines for sales axis
                    ticks: { 
                        color: c.text, 
                        font: { family: 'Plus Jakarta Sans' },
                        callback: value => '$' + value / 1000 + 'k'
                    },
                    title: { display: true, text: 'Profit ($)', color: c.text, font: { family: 'Plus Jakarta Sans', weight: 'bold' } }
                }
            },
            plugins: {
                legend: {
                    labels: { color: c.text, font: { family: 'Plus Jakarta Sans', weight: 'bold' } }
                },
                tooltip: {
                    backgroundColor: c.tooltipBg,
                    titleColor: c.tooltipText,
                    bodyColor: c.tooltipText,
                    borderColor: c.tooltipBorder,
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            }
        }
    });
}

// 5. Sales by Region (Horizontal Bar Chart)
function renderRegionChart() {
    const ctx = document.getElementById('regionChart').getContext('2d');
    const c = getThemeColors();
    
    // Sort by sales descending
    const sorted = [...dashboardData.sales_by_region].sort((a,b) => b.Sales - a.Sales);
    const labels = sorted.map(d => d.Region);
    const sales = sorted.map(d => d.Sales);
    
    charts.region = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total Sales by Region',
                data: sales,
                backgroundColor: [
                    'rgba(59, 130, 246, 0.75)', // Blue
                    'rgba(139, 92, 246, 0.75)', // Purple
                    'rgba(20, 184, 166, 0.75)', // Teal
                    'rgba(245, 158, 11, 0.75)'  // Amber
                ],
                borderColor: c.grid,
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y', // Make it horizontal
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: c.grid },
                    ticks: { 
                        color: c.text, 
                        font: { family: 'Plus Jakarta Sans' },
                        callback: value => '$' + value / 1000 + 'k'
                    }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: c.text, font: { family: 'Plus Jakarta Sans', weight: 'bold' } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: c.tooltipBg,
                    titleColor: c.tooltipText,
                    bodyColor: c.tooltipText,
                    borderColor: c.tooltipBorder,
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return `Sales: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            }
        }
    });
}

// 6. Forecast vs Actual (Validation Hold-out set)
function renderForecastVsActualChart() {
    const ctx = document.getElementById('forecastVsActualChart').getContext('2d');
    const c = getThemeColors();
    
    const tp = forecastData.test_predictions;
    const bestModel = forecastData.best_model;
    
    // Aggregate daily validation predictions to weekly for layout clarity
    const weeklyData = aggregateValidationWeekly(tp.dates, tp.actual, tp[bestModel]);
    
    charts.forecastVsActual = new Chart(ctx, {
        type: 'line',
        data: {
            labels: weeklyData.dates,
            datasets: [
                {
                    label: 'Actual Sales',
                    data: weeklyData.actual,
                    borderColor: c.sales,
                    borderWidth: 2.5,
                    pointBackgroundColor: c.sales,
                    pointRadius: 2,
                    tension: 0.35,
                    fill: false
                },
                {
                    label: `Forecasted (${bestModel})`,
                    data: weeklyData.forecast,
                    borderColor: c.forecast,
                    borderWidth: 2.5,
                    borderDash: [5, 5],
                    pointBackgroundColor: c.forecast,
                    pointRadius: 2,
                    tension: 0.35,
                    fill: false
                }
            ]
        },
        options: getCommonChartOptions('Test Timeline (Weekly)', 'Sales ($)', false)
    });
}

// Common Chart.js Config Generator
function getCommonChartOptions(xTitle, yTitle, shortenY = false) {
    const c = getThemeColors();
    return {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                grid: { color: c.grid },
                ticks: { color: c.text, font: { family: 'Plus Jakarta Sans' } }
            },
            y: {
                grid: { color: c.grid },
                ticks: { 
                    color: c.text, 
                    font: { family: 'Plus Jakarta Sans' },
                    callback: value => shortenY ? '$' + value / 1000 + 'k' : '$' + value.toLocaleString()
                }
            }
        },
        plugins: {
            legend: {
                labels: { color: c.text, font: { family: 'Plus Jakarta Sans', weight: 'bold' } }
            },
            tooltip: {
                backgroundColor: c.tooltipBg,
                titleColor: c.tooltipText,
                bodyColor: c.tooltipText,
                borderColor: c.tooltipBorder,
                borderWidth: 1,
                callbacks: {
                    label: function(context) {
                        return `${context.dataset.label}: ${formatCurrency(context.raw)}`;
                    }
                }
            }
        }
    };
}

// ------------------ DATA MANIPULATION HELPERS ------------------

function aggregateWeekly(dates, forecast, lower, upper) {
    // Aggregates 30/90 daily forecast to weekly summaries
    let weekly = { dates: [], forecast: [], lower: [], upper: [] };
    
    let currentSum = 0;
    let currentLower = 0;
    let currentUpper = 0;
    let count = 0;
    
    for (let i = 0; i < dates.length; i++) {
        currentSum += forecast[i];
        currentLower += lower[i];
        currentUpper += upper[i];
        count++;
        
        // At the end of the week or dataset, write record
        if (count === 7 || i === dates.length - 1) {
            // Use starting date
            const startIdx = i - count + 1;
            weekly.dates.push(dates[startIdx]);
            weekly.forecast.push(currentSum);
            weekly.lower.push(currentLower);
            weekly.upper.push(currentUpper);
            
            // Reset
            currentSum = 0;
            currentLower = 0;
            currentUpper = 0;
            count = 0;
        }
    }
    return weekly;
}

function aggregateValidationWeekly(dates, actual, forecast) {
    let weekly = { dates: [], actual: [], forecast: [] };
    
    let actSum = 0;
    let fcSum = 0;
    let count = 0;
    
    for (let i = 0; i < dates.length; i++) {
        actSum += actual[i];
        fcSum += forecast[i];
        count++;
        
        if (count === 7 || i === dates.length - 1) {
            const startIdx = i - count + 1;
            weekly.dates.push(dates[startIdx]);
            weekly.actual.push(actSum);
            weekly.forecast.push(fcSum);
            
            actSum = 0;
            fcSum = 0;
            count = 0;
        }
    }
    return weekly;
}

// Formatting helpers
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

function formatYearMonth(ymStr) {
    // format "2016-05" to "May 2016"
    const parts = ymStr.split('-');
    const year = parts[0];
    const month = parseInt(parts[1]) - 1;
    const date = new Date(year, month, 1);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

function truncateText(str, n) {
    return (str.length > n) ? str.substr(0, n - 1) + '&hellip;' : str;
}
