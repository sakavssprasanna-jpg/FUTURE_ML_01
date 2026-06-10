import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_pdf_report(df_raw, eda_data, model_results, forecast_30, forecast_90, output_path):
    """
    Generate an executive-ready sales forecasting report.
    """
    # 1. Generate the Chart PNG
    chart_img_path = 'temp_forecast_chart.png'
    create_report_chart(model_results['daily_df'], forecast_90, chart_img_path)
    
    # 2. Setup document
    # Set page size and margins (0.5 inch margins to fit content neatly)
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=letter,
        leftMargin=36, 
        rightMargin=36,
        topMargin=36, 
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    # Primary theme: Dark Teal / Navy
    primary_color = colors.HexColor('#004d61')
    secondary_color = colors.HexColor('#008080')
    dark_neutral = colors.HexColor('#2d3748')
    light_bg = colors.HexColor('#f7fafc')
    accent_green = colors.HexColor('#2f855a')
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.white
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#b2dfdb')
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=dark_neutral,
        spaceAfter=4
    )
    
    body_bold = ParagraphStyle(
        'ReportBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    bullet_style = ParagraphStyle(
        'ReportBullet',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=6
    )
    
    card_title_style = ParagraphStyle(
        'CardTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#4a5568'),
        alignment=1 # Center
    )
    
    card_value_style = ParagraphStyle(
        'CardValue',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        textColor=primary_color,
        alignment=1 # Center
    )
    
    story = []
    
    # ------------------ HEADER ------------------
    header_data = [
        [
            Paragraph("SUPERSTORE EXECUTIVE SALES FORECASTING REPORT", title_style),
            Paragraph(f"GENERATED: {datetime.now().strftime('%Y-%m-%d')}<br/>SELECTED MODEL: {model_results['best_model'].upper()}", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[380, 160])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), primary_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('LEFTPADDING', (0,0), (-1,-1), 15),
        ('RIGHTPADDING', (0,0), (-1,-1), 15),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    # ------------------ KPI CARDS ------------------
    # Calculated Forecast Summaries
    total_fc_30 = sum(forecast_30['forecast'])
    total_fc_90 = sum(forecast_90['forecast'])
    best_model = model_results['best_model']
    best_model_metrics = model_results['metrics'][best_model]
    accuracy = model_results.get('accuracy', 72.4)
    
    kpi_data = [
        [
            Paragraph("TOTAL HISTORICAL SALES", card_title_style),
            Paragraph("TOTAL HISTORICAL PROFIT", card_title_style),
            Paragraph("30-DAY SALES FORECAST", card_title_style),
            Paragraph("90-DAY SALES FORECAST", card_title_style)
        ],
        [
            Paragraph(f"${eda_data['total_sales']:,.2f}", card_value_style),
            Paragraph(f"${eda_data['total_profit']:,.2f}", card_value_style),
            Paragraph(f"${total_fc_30:,.2f}", card_value_style),
            Paragraph(f"${total_fc_90:,.2f}", card_value_style)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (0,0), 6),
        ('BOTTOMPADDING', (0,0), (0,0), 2),
        ('TOPPADDING', (0,1), (-1,1), 2),
        ('BOTTOMPADDING', (0,1), (-1,1), 6),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 10))
    
    # ------------------ SECTION: FORECASTING MODEL EVALUATION ------------------
    story.append(Paragraph("1. Forecasting Model Comparison & Evaluation", h1_style))
    story.append(Paragraph(
        f"To identify the most reliable forecasting algorithm for the Superstore dataset, we ran training evaluations on "
        f"three machine learning methods using a time-series split. The last 90 days of the dataset were used as the hold-out testing set. "
        f"The <b>{best_model}</b> model outperformed the others with the lowest Root Mean Squared Error (RMSE) and was selected "
        f"automatically to project future sales.", body_style))
    story.append(Spacer(1, 5))
    
    # Model Table
    model_table_data = [[
        Paragraph("<b>Model Name</b>", body_bold),
        Paragraph("<b>Mean Absolute Error (MAE)</b>", body_bold),
        Paragraph("<b>Root Mean Squared Error (RMSE)</b>", body_bold),
        Paragraph("<b>R² Score (Variance Explained)</b>", body_bold),
        Paragraph("<b>Status</b>", body_bold)
    ]]
    
    for name, metrics in model_results['metrics'].items():
        is_best = (name == best_model)
        status_text = "<b><font color='teal'>Selected</font></b>" if is_best else "Evaluated"
        bg_col = colors.HexColor('#e6fffa') if is_best else colors.white
        
        model_table_data.append([
            Paragraph(f"<b>{name}</b>" if is_best else name, body_style),
            Paragraph(f"${metrics['MAE']:,.2f}", body_style),
            Paragraph(f"${metrics['RMSE']:,.2f}", body_style),
            Paragraph(f"{metrics['R2']:.4f}", body_style),
            Paragraph(status_text, body_style)
        ])
        
    model_table = Table(model_table_data, colWidths=[130, 110, 110, 110, 80])
    model_table_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#edf2f7')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]
    # Highlight the best model row background
    for idx, name in enumerate(model_results['metrics'].keys()):
        if name == best_model:
            model_table_style.append(('BACKGROUND', (0, idx + 1), (-1, idx + 1), colors.HexColor('#e6fffa')))
            
    model_table.setStyle(TableStyle(model_table_style))
    story.append(model_table)
    story.append(Spacer(1, 10))
    
    # ------------------ SECTION: VISUAL TREND CHART ------------------
    story.append(Paragraph("2. Historical vs. Forecasted Sales Visualisation", h1_style))
    if os.path.exists(chart_img_path):
        story.append(Image(chart_img_path, width=540, height=230))
    story.append(Spacer(1, 8))
    
    # ------------------ PAGE BREAK OR KEEP TOGETHER FOR INSIGHTS & WEEKLY FORECAST ------------------
    # Insights and Weekly forecast
    bottom_section = []
    bottom_section.append(Paragraph("3. Executive Business Insights & Strategic Recommendations", h1_style))
    
    # Compute insights helper
    insights = generate_insights_summary(df_raw, forecast_30, forecast_90)
    
    for rec in insights['recommendations']:
        bottom_section.append(Paragraph(f"&bull; <b>{rec.split(':')[0]}:</b>{rec.split(':')[1]}", bullet_style))
        
    bottom_section.append(Spacer(1, 5))
    
    # Weekly forecast summary table
    bottom_section.append(Paragraph("4. Forecast Schedule (Weekly Aggregation)", h1_style))
    bottom_section.append(Paragraph(
        "For tactical inventory planning, here is the weekly breakdown of the projected sales for the next 90 days:", body_style
    ))
    bottom_section.append(Spacer(1, 4))
    
    weekly_forecast_table = create_weekly_forecast_table(forecast_90, body_bold, body_style, primary_color, light_bg)
    bottom_section.append(weekly_forecast_table)
    
    # Wrap bottom section in KeepTogether or let it flow, since we have 0.5 in margins it usually fits on 2 pages.
    # Actually, let's put a page break before Section 3 to make it a perfect 2-page report!
    story.append(Spacer(1, 10))
    story.append(KeepTogether(bottom_section))
    
    # Build Document
    doc.build(story)
    
    # Clean up chart file
    if os.path.exists(chart_img_path):
        try:
            os.remove(chart_img_path)
        except:
            pass

def create_report_chart(daily_df, forecast_90, output_path):
    """
    Generate the matplotlib chart for the PDF report.
    """
    plt.figure(figsize=(10, 4.5))
    
    # Aggregating daily data to weekly to make the plot clean and readable
    df_chart = daily_df.copy()
    df_chart['Order Date'] = pd.to_datetime(df_chart['Order Date'])
    df_chart = df_chart.set_index('Order Date')
    
    # Resample weekly
    weekly_actual = df_chart['Sales'].resample('W').sum().reset_index()
    
    # Future dates weekly
    future_dates = pd.to_datetime(forecast_90['dates'])
    future_sales = forecast_90['forecast']
    future_lower = forecast_90['lower_bound']
    future_upper = forecast_90['upper_bound']
    
    df_future = pd.DataFrame({
        'Date': future_dates,
        'Forecast': future_sales,
        'Lower': future_lower,
        'Upper': future_upper
    }).set_index('Date')
    
    weekly_future = df_future.resample('W').agg({
        'Forecast': 'sum',
        'Lower': 'sum',
        'Upper': 'sum'
    }).reset_index()
    
    # Limit historical plot to last 12 months for clarity
    max_hist_date = weekly_actual['Order Date'].max()
    historical_plot_cutoff = max_hist_date - timedelta(days=365)
    weekly_actual_subset = weekly_actual[weekly_actual['Order Date'] >= historical_plot_cutoff]
    
    # Plotting
    plt.plot(weekly_actual_subset['Order Date'], weekly_actual_subset['Sales'], 
             color='#1a365d', linewidth=2, label='Actual Sales (Weekly)')
             
    plt.plot(weekly_future['Date'], weekly_future['Forecast'], 
             color='#008080', linewidth=2, linestyle='--', label='Projected Forecast')
             
    plt.fill_between(weekly_future['Date'], weekly_future['Lower'], weekly_future['Upper'], 
                     color='#008080', alpha=0.15, label='95% Confidence Boundary')
    
    plt.title('Superstore Sales Forecasting - Weekly Trend Analysis', fontsize=12, fontweight='bold', pad=10, color='#1a365d')
    plt.xlabel('Timeline', fontsize=9, color='#2d3748')
    plt.ylabel('Weekly Sales ($)', fontsize=9, color='#2d3748')
    plt.grid(True, linestyle=':', alpha=0.5, color='#cbd5e0')
    plt.legend(loc='upper left', fontsize=8, frameon=True, facecolor='#f7fafc')
    
    # Formatting dates
    plt.gca().xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%b %Y'))
    plt.tick_params(axis='both', which='major', labelsize=8)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()

def create_weekly_forecast_table(forecast_90, header_style, cell_style, primary_color, light_bg):
    """
    Create a weekly forecast table.
    """
    dates = pd.to_datetime(forecast_90['dates'])
    sales = forecast_90['forecast']
    
    df_forecast = pd.DataFrame({
        'Date': dates,
        'Forecast': sales
    }).set_index('Date')
    
    weekly = df_forecast.resample('W').sum().reset_index()
    
    table_data = [[
        Paragraph("<b>Week Starting</b>", header_style),
        Paragraph("<b>Forecasted Weekly Sales</b>", header_style),
        Paragraph("<b>Week Starting</b>", header_style),
        Paragraph("<b>Forecasted Weekly Sales</b>", header_style)
    ]]
    
    # Render table in two columns to fit nicely on the page
    num_rows = (len(weekly) + 1) // 2
    for i in range(num_rows):
        row = []
        
        # Col 1
        w1 = weekly.iloc[i]
        row.append(Paragraph(w1['Date'].strftime('%Y-%m-%d'), cell_style))
        row.append(Paragraph(f"${w1['Forecast']:,.2f}", cell_style))
        
        # Col 2
        idx2 = i + num_rows
        if idx2 < len(weekly):
            w2 = weekly.iloc[idx2]
            row.append(Paragraph(w2['Date'].strftime('%Y-%m-%d'), cell_style))
            row.append(Paragraph(f"${w2['Forecast']:,.2f}", cell_style))
        else:
            row.append(Paragraph("", cell_style))
            row.append(Paragraph("", cell_style))
            
        table_data.append(row)
        
    table = Table(table_data, colWidths=[130, 130, 130, 130])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#edf2f7')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    return table

def generate_insights_summary(df, forecast_30, forecast_90):
    """
    Generate quick insights dictionary without requiring all parameters from main app.
    """
    # 1. Best performing categories
    cat_sales = df.groupby('Category').agg({'Sales': 'sum', 'Profit': 'sum'}).reset_index()
    cat_sales['Margin'] = cat_sales['Profit'] / cat_sales['Sales']
    best_cat = cat_sales.sort_values(by='Sales', ascending=False).iloc[0]
    most_profitable_cat = cat_sales.sort_values(by='Profit', ascending=False).iloc[0]
    
    # 2. Best performing regions
    reg_sales = df.groupby('Region').agg({'Sales': 'sum'}).reset_index()
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
    
    total_fc_30 = sum(forecast_30['forecast'])
    total_fc_90 = sum(forecast_90['forecast'])
    
    return {
        'recommendations': [
            f"Inventory Allocations: Increase stock levels for {best_cat['Category']} by 15-20% before {peak_month_name} to meet high seasonal demand.",
            f"Regional Marketing: Launch region-specific campaigns in {best_reg['Region']} to capitalize on their high sales volume.",
            f"Margin Optimisation: Leverage {most_profitable_cat['Category']}'s high profit margins ({most_profitable_cat['Margin']:.1%}) by bundling it with high volume categories.",
            f"Revenue Projections: Next 30 days are expected to generate ${total_fc_30:,.2f} in revenue, whereas the next 90 days are projected at ${total_fc_90:,.2f}. Adjust short-term staffing and cash flow allocations accordingly."
        ]
    }
