import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from datetime import datetime, timedelta

def load_and_clean_data(file_path):
    """
    Load the dataset, handle missing values, remove duplicates, 
    and convert Order Date into datetime.
    """
    df = pd.read_csv(file_path, encoding='latin1')
    
    # 1. Clean duplicates
    df = df.drop_duplicates()
    
    # 2. Convert Order Date and Ship Date to datetime
    df['Order Date'] = pd.to_datetime(df['Order Date'], format='mixed')
    df['Ship Date'] = pd.to_datetime(df['Ship Date'], format='mixed')
    
    # 3. Handle missing values (though raw CSV has none, safety check)
    df = df.dropna(subset=['Order Date', 'Sales'])
    
    # Ensure numeric columns are correct type
    for col in ['Sales', 'Profit', 'Quantity', 'Discount']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    return df

def get_eda_metrics(df):
    """
    Compute Exploratory Data Analysis metrics.
    """
    total_sales = float(df['Sales'].sum())
    total_profit = float(df['Profit'].sum())
    total_orders = int(df['Order ID'].nunique())
    avg_sales = float(df['Sales'].mean())
    
    # Sales and Profit by Category
    cat_df = df.groupby('Category').agg({'Sales': 'sum', 'Profit': 'sum', 'Quantity': 'sum'}).reset_index()
    sales_by_category = cat_df.to_dict(orient='records')
    
    # Sales by Region
    region_df = df.groupby('Region').agg({'Sales': 'sum', 'Profit': 'sum'}).reset_index()
    sales_by_region = region_df.to_dict(orient='records')
    
    # Monthly Sales Trend
    df['YearMonth'] = df['Order Date'].dt.to_period('M')
    monthly_df = df.groupby('YearMonth').agg({'Sales': 'sum', 'Profit': 'sum'}).reset_index()
    monthly_df['YearMonth'] = monthly_df['YearMonth'].astype(str)
    monthly_trend = monthly_df.to_dict(orient='records')
    
    # Top Selling Products (Top 10)
    prod_df = df.groupby('Product Name').agg({'Sales': 'sum', 'Quantity': 'sum', 'Profit': 'sum'}).reset_index()
    prod_df = prod_df.sort_values(by='Sales', ascending=False).head(10)
    top_products = prod_df.to_dict(orient='records')
    
    # Profit Trend by month
    profit_trend = monthly_trend  # contains both Sales and Profit monthly
    
    return {
        'total_sales': total_sales,
        'total_profit': total_profit,
        'total_orders': total_orders,
        'avg_sales': avg_sales,
        'sales_by_category': sales_by_category,
        'sales_by_region': sales_by_region,
        'monthly_trend': monthly_trend,
        'top_products': top_products
    }

def engineer_features(df_daily, min_date):
    """
    Generate calendar, seasonal, and trend features for a daily aggregated dataframe.
    """
    df_features = df_daily.copy()
    
    # Calendar features
    df_features['Year'] = df_features['Order Date'].dt.year
    df_features['Month'] = df_features['Order Date'].dt.month
    df_features['Quarter'] = df_features['Order Date'].dt.quarter
    df_features['DayOfWeek'] = df_features['Order Date'].dt.dayofweek
    df_features['WeekOfYear'] = df_features['Order Date'].dt.isocalendar().week.astype(int)
    df_features['DayOfYear'] = df_features['Order Date'].dt.dayofyear
    df_features['IsWeekend'] = (df_features['DayOfWeek'] >= 5).astype(int)
    
    # Seasonal features (sin/cos encoding of month and day of year)
    df_features['Month_Sin'] = np.sin(2 * np.pi * df_features['Month'] / 12.0)
    df_features['Month_Cos'] = np.cos(2 * np.pi * df_features['Month'] / 12.0)
    df_features['DayOfYear_Sin'] = np.sin(2 * np.pi * df_features['DayOfYear'] / 365.25)
    df_features['DayOfYear_Cos'] = np.cos(2 * np.pi * df_features['DayOfYear'] / 365.25)
    
    # Seasons mapping
    # 1: Winter (12, 1, 2), 2: Spring (3, 4, 5), 3: Summer (6, 7, 8), 4: Fall (9, 10, 11)
    def get_season_indicator(month, season_name):
        if season_name == 'Spring':
            return 1 if month in [3, 4, 5] else 0
        elif season_name == 'Summer':
            return 1 if month in [6, 7, 8] else 0
        elif season_name == 'Fall':
            return 1 if month in [9, 10, 11] else 0
        elif season_name == 'Winter':
            return 1 if month in [12, 1, 2] else 0
        return 0
        
    df_features['Season_Spring'] = df_features['Month'].apply(lambda m: get_season_indicator(m, 'Spring'))
    df_features['Season_Summer'] = df_features['Month'].apply(lambda m: get_season_indicator(m, 'Summer'))
    df_features['Season_Fall'] = df_features['Month'].apply(lambda m: get_season_indicator(m, 'Fall'))
    df_features['Season_Winter'] = df_features['Month'].apply(lambda m: get_season_indicator(m, 'Winter'))
    
    # Trend feature (days since start of the dataset)
    df_features['Trend'] = (df_features['Order Date'] - min_date).dt.days
    
    return df_features

def get_daily_series(df):
    """
    Aggregate transactional data to daily frequency and fill in missing dates with 0.
    """
    # Group by Order Date and sum
    daily_df = df.groupby('Order Date').agg({
        'Sales': 'sum',
        'Profit': 'sum',
        'Quantity': 'sum'
    }).reset_index()
    
    # Set Order Date as index and resample to daily to fill gaps
    daily_df = daily_df.set_index('Order Date')
    daily_df = daily_df.resample('D').sum().reset_index()
    
    return daily_df

def train_and_evaluate(df_cleaned):
    """
    Prepares features, splits into train/test, trains LR, RF, and XGBoost,
    compares metrics, and identifies the best model.
    """
    daily_df = get_daily_series(df_cleaned)
    min_date = daily_df['Order Date'].min()
    
    # Feature engineering
    daily_df_feat = engineer_features(daily_df, min_date)
    
    # Feature lists
    features = [
        'Year', 'Month', 'Quarter', 'DayOfWeek', 'WeekOfYear', 'IsWeekend', 
        'Month_Sin', 'Month_Cos', 'DayOfYear_Sin', 'DayOfYear_Cos', 
        'Season_Spring', 'Season_Summer', 'Season_Fall', 'Season_Winter', 'Trend'
    ]
    
    # Split: Last 90 days as test set
    split_date = daily_df_feat['Order Date'].max() - timedelta(days=90)
    train_df = daily_df_feat[daily_df_feat['Order Date'] < split_date]
    test_df = daily_df_feat[daily_df_feat['Order Date'] >= split_date]
    
    X_train, y_train = train_df[features], train_df['Sales']
    X_test, y_test = test_df[features], test_df['Sales']
    
    models = {
        'Linear Regression': LinearRegression(),
        'Random Forest': RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42),
        'XGBoost': XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42)
    }
    
    metrics_summary = {}
    test_predictions = {}
    
    # Keep dates for charting
    test_dates = test_df['Order Date'].dt.strftime('%Y-%m-%d').tolist()
    test_predictions['dates'] = test_dates
    test_predictions['actual'] = y_test.tolist()
    
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        # Clamping predictions to be non-negative
        preds = np.clip(preds, 0, None)
        
        # Calculate metrics
        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)
        
        metrics_summary[name] = {
            'MAE': float(mae),
            'RMSE': float(rmse),
            'R2': float(r2)
        }
        test_predictions[name] = preds.tolist()
        
    # Auto-select the best model based on lowest RMSE
    best_model_name = min(metrics_summary, key=lambda k: metrics_summary[k]['RMSE'])
    
    # Calculate weekly WAPE to display a meaningful executive accuracy
    test_dates_dt = pd.to_datetime(test_dates)
    df_test_acc = pd.DataFrame({
        'Date': test_dates_dt,
        'Actual': y_test.values,
        'Pred': test_predictions[best_model_name]
    }).set_index('Date')
    weekly_acc_df = df_test_acc.resample('W').sum()
    sum_actual = weekly_acc_df['Actual'].sum()
    if sum_actual > 0:
        wape_weekly = np.sum(np.abs(weekly_acc_df['Actual'] - weekly_acc_df['Pred'])) / sum_actual
        weekly_accuracy = max(0.0, (1 - wape_weekly) * 100)
    else:
        weekly_accuracy = 0.0
    
    return {
        'metrics': metrics_summary,
        'best_model': best_model_name,
        'test_predictions': test_predictions,
        'features': features,
        'daily_df': daily_df_feat,
        'min_date': min_date,
        'accuracy': float(weekly_accuracy)
    }


def forecast_future_sales(daily_df, best_model_name, min_date, forecast_days=90):
    """
    Train the selected model on the entire dataset and forecast the future.
    """
    features = [
        'Year', 'Month', 'Quarter', 'DayOfWeek', 'WeekOfYear', 'IsWeekend', 
        'Month_Sin', 'Month_Cos', 'DayOfYear_Sin', 'DayOfYear_Cos', 
        'Season_Spring', 'Season_Summer', 'Season_Fall', 'Season_Winter', 'Trend'
    ]
    
    # 1. Define model
    if best_model_name == 'Linear Regression':
        model = LinearRegression()
    elif best_model_name == 'Random Forest':
        model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
    else:
        model = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42)
        
    # 2. Fit on all data
    X_full = daily_df[features]
    y_full = daily_df['Sales']
    model.fit(X_full, y_full)
    
    # Calculate residuals to estimate uncertainty bounds
    historical_preds = model.predict(X_full)
    historical_preds = np.clip(historical_preds, 0, None)
    residuals = y_full - historical_preds
    sigma = np.std(residuals)
    
    # 3. Create future dates
    last_date = daily_df['Order Date'].max()
    future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
    future_df = pd.DataFrame({'Order Date': future_dates})
    
    # 4. Feature engineering for future
    future_df = engineer_features(future_df, min_date)
    
    # 5. Predict future sales
    future_preds = model.predict(future_df[features])
    future_preds = np.clip(future_preds, 0, None)
    
    # 6. Uncertainty margins (95% CI)
    lower_bound = np.clip(future_preds - 1.96 * sigma, 0, None)
    upper_bound = future_preds + 1.96 * sigma
    
    # 7. Create output dict
    results = {
        'dates': [d.strftime('%Y-%m-%d') for d in future_dates],
        'forecast': future_preds.tolist(),
        'lower_bound': lower_bound.tolist(),
        'upper_bound': upper_bound.tolist()
    }
    
    return results

def generate_business_insights(df, forecast_data_30, forecast_data_90):
    """
    Generate actionable business insights based on the analysis.
    """
    # 1. Best performing categories
    cat_sales = df.groupby('Category').agg({'Sales': 'sum', 'Profit': 'sum'}).reset_index()
    cat_sales['Margin'] = cat_sales['Profit'] / cat_sales['Sales']
    best_cat = cat_sales.sort_values(by='Sales', ascending=False).iloc[0]
    most_profitable_cat = cat_sales.sort_values(by='Profit', ascending=False).iloc[0]
    
    # 2. Best performing regions
    reg_sales = df.groupby('Region').agg({'Sales': 'sum', 'Profit': 'sum'}).reset_index()
    best_reg = reg_sales.sort_values(by='Sales', ascending=False).iloc[0]
    
    # 3. Monthly seasonality pattern
    df['MonthNum'] = df['Order Date'].dt.month
    monthly_sales = df.groupby('MonthNum').agg({'Sales': 'sum'}).reset_index()
    peak_month_idx = monthly_sales.sort_values(by='Sales', ascending=False).iloc[0]['MonthNum']
    
    months_map = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
        7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }
    peak_month_name = months_map[int(peak_month_idx)]
    
    # 4. Forecast values summaries
    total_fc_30 = sum(forecast_data_30['forecast'])
    total_fc_90 = sum(forecast_data_90['forecast'])
    
    insights = {
        'best_category': {
            'name': best_cat['Category'],
            'sales': float(best_cat['Sales']),
            'profit': float(best_cat['Profit']),
            'margin': float(best_cat['Margin'])
        },
        'most_profitable_category': {
            'name': most_profitable_cat['Category'],
            'sales': float(most_profitable_cat['Sales']),
            'profit': float(most_profitable_cat['Profit']),
            'margin': float(most_profitable_cat['Margin'])
        },
        'best_region': {
            'name': best_reg['Region'],
            'sales': float(best_reg['Sales']),
            'profit': float(best_reg['Profit'])
        },
        'seasonality': {
            'peak_month': peak_month_name,
            'description': f"Retail sales peak in {peak_month_name}, indicating a strong seasonal end-of-year or mid-year buying pattern."
        },
        'forecast_totals': {
            'next_30_days': float(total_fc_30),
            'next_90_days': float(total_fc_90)
        },
        'recommendations': [
            f"Inventory: Increase stock levels for {best_cat['Category']} by 15-20% before {peak_month_name} to meet high seasonal demand.",
            f"Marketing: Launch region-specific campaigns in {best_reg['Region']} to capitalize on their high sales volume.",
            f"Profit Maximization: Leverage {most_profitable_cat['Category']}'s high profit margins ({most_profitable_cat['Margin']:.1%}) by bundle-selling it with higher volume categories.",
            f"Revenue Projections: Next 30 days are expected to generate ${total_fc_30:,.2f} in revenue, whereas the next 90 days are projected at ${total_fc_90:,.2f}. Adjust short-term staffing and cash flow allocations accordingly."
        ]
    }
    
    return insights
