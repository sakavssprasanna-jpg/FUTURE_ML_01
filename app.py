import os
import io
import pandas as pd
from flask import Flask, jsonify, send_file, render_template
from forecaster import (
    load_and_clean_data, 
    get_eda_metrics, 
    train_and_evaluate, 
    forecast_future_sales, 
    generate_business_insights
)
from report_generator import generate_pdf_report

app = Flask(__name__)

# Global cache variables
DATA_FILE = 'stores_sales_forecasting.csv'
CLEANED_DF = None
EDA_METRICS = None
MODEL_RESULTS = None
FORECAST_30 = None
FORECAST_90 = None
INSIGHTS = None

def init_cache():
    """
    Initialize the global data and model predictions cache on startup.
    This prevents retraining models on every single API request.
    """
    global CLEANED_DF, EDA_METRICS, MODEL_RESULTS, FORECAST_30, FORECAST_90, INSIGHTS
    
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"Missing dataset file: {DATA_FILE}")
        
    print("=== [Initialization] Loading and Cleaning Data ===")
    CLEANED_DF = load_and_clean_data(DATA_FILE)
    
    print("=== [Initialization] Computing EDA Metrics ===")
    EDA_METRICS = get_eda_metrics(CLEANED_DF)
    
    print("=== [Initialization] Training & Evaluating Models ===")
    # Evaluates LR, RF, XGBoost on train/test split (last 90 days as test)
    MODEL_RESULTS = train_and_evaluate(CLEANED_DF)
    
    print(f"=== [Initialization] Selected Best Model: {MODEL_RESULTS['best_model']} ===")
    best_model = MODEL_RESULTS['best_model']
    daily_df = MODEL_RESULTS['daily_df']
    min_date = MODEL_RESULTS['min_date']
    
    print("=== [Initialization] Forecasting Future Sales ===")
    # Forecast future sales (trained on full dataset)
    FORECAST_30 = forecast_future_sales(daily_df, best_model, min_date, forecast_days=30)
    FORECAST_90 = forecast_future_sales(daily_df, best_model, min_date, forecast_days=90)
    
    print("=== [Initialization] Generating Business Insights ===")
    INSIGHTS = generate_business_insights(CLEANED_DF, FORECAST_30, FORECAST_90)
    
    print("=== [Initialization] Complete! Server Ready ===")

@app.route('/')
def index():
    """Serve the single page dashboard application."""
    return render_template('index.html')

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """API for getting high-level statistics and EDA charts data."""
    if EDA_METRICS is None:
        return jsonify({'error': 'Cache not initialized'}), 500
    return jsonify(EDA_METRICS)

@app.route('/api/forecast')
def get_forecast():
    """API returning model metrics, test evaluation predictions, and future predictions."""
    if MODEL_RESULTS is None or FORECAST_30 is None or FORECAST_90 is None:
        return jsonify({'error': 'Cache not initialized'}), 500
        
    # Exclude raw pandas dataframe from API response to avoid JSON serialization error
    api_results = {
        'metrics': MODEL_RESULTS['metrics'],
        'best_model': MODEL_RESULTS['best_model'],
        'test_predictions': MODEL_RESULTS['test_predictions'], # actual vs test forecast
        'forecast_30': FORECAST_30,
        'forecast_90': FORECAST_90,
        'accuracy': MODEL_RESULTS['accuracy']
    }

    return jsonify(api_results)

@app.route('/api/insights')
def get_insights():
    """API returning computed business insights and inventory recommendations."""
    if INSIGHTS is None:
        return jsonify({'error': 'Cache not initialized'}), 500
    return jsonify(INSIGHTS)

@app.route('/api/export/csv')
def export_csv():
    """API to export the 90-day forecast as a CSV file."""
    if FORECAST_90 is None:
        return jsonify({'error': 'Forecast not initialized'}), 400
        
    # Build DataFrame
    df_export = pd.DataFrame({
        'Date': FORECAST_90['dates'],
        'Forecasted_Sales': FORECAST_90['forecast'],
        'Lower_Bound_95_CI': FORECAST_90['lower_bound'],
        'Upper_Bound_95_CI': FORECAST_90['upper_bound']
    })
    
    # Save CSV into an in-memory buffer
    csv_buf = io.StringIO()
    df_export.to_csv(csv_buf, index=False)
    csv_data = csv_buf.getvalue()
    
    return send_file(
        io.BytesIO(csv_data.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='sales_forecast_90_days.csv'
    )

@app.route('/api/export/pdf')
def export_pdf():
    """API to export the executive summary forecasting report as a PDF."""
    if FORECAST_90 is None:
        return jsonify({'error': 'Forecast not initialized'}), 400
        
    pdf_filename = 'sales_forecasting_executive_report.pdf'
    
    try:
        generate_pdf_report(
            CLEANED_DF,
            EDA_METRICS,
            MODEL_RESULTS,
            FORECAST_30,
            FORECAST_90,
            pdf_filename
        )
        
        # Read the generated file and return it to client
        return send_file(
            pdf_filename, 
            mimetype='application/pdf',
            as_attachment=True, 
            download_name=pdf_filename
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Failed to generate PDF: {str(e)}"}), 500

if __name__ == '__main__':
    # Initialize cache on startup
    init_cache()
    # Run the server
    app.run(debug=True, host='0.0.0.0', port=5000)
