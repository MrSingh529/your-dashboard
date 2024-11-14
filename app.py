import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from functools import lru_cache
import time
import hashlib
from functools import lru_cache

# Configure page settings
st.set_page_config(
    page_title="TSG Payment Receivables Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with loading animation
st.markdown("""
    <style>
    .main {
        padding: 20px;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .filter-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .comparison-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .trend-positive {
        color: #2ecc71;
        font-weight: bold;
    }
    .trend-negative {
        color: #e74c3c;
        font-weight: bold;
    }
    .loading {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(0,0,0,.1);
        border-radius: 50%;
        border-top-color: #2ecc71;
        animation: spin 1s ease-in-out infinite;
    }
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    </style>
""", unsafe_allow_html=True)

# Enhanced security with password hashing
import hashlib
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Credentials for Google Drive
CREDENTIALS = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "ceo": hashlib.sha256("ceo123".encode()).hexdigest(),
    "manager": hashlib.sha256("manager123".encode()).hexdigest()
}

FILE_IDS = {
    'collections_data': '1zCSAx8jzOLewJXxOQlHjlUxXKoHbdopD',
    'itss_tender': '1o6SjeyNuvSyt9c5uCsq4MGFlZV1moC3V',
    'sdr_trend': '1PixxavAM29QrtjZUh-TMpa8gDSE7lg60',
    'tsg_trend': '1Kf8nHi1shw6q0oozXFEScyE0bmhhPDPo'
}

@st.cache_resource(ttl=3600)  # Cache authentication for 1 hour
def authenticate_drive():
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["google_drive"],
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        st.error(f"Failed to authenticate with Google Drive: {str(e)}")
        return None

@st.cache_data(ttl=300)
def load_data_from_drive(file_id):
    try:
        service = authenticate_drive()
        if not service:
            return None

        request = service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_buffer.seek(0)
        df = pd.read_excel(file_buffer, header=None)

        # Assign appropriate columns based on file structure
        columns = ['Branch Name', 'Reduced Pending Amount']
        dates = ['03-Nov-24', '27-Oct-24', '20-Oct-24', '12-Oct-24', '06-Oct-24', '30-Sep-24', '21-Sep-24']
        for date in dates:
            columns.extend([f'Balance_{date}', f'Pending_{date}'])

        df.columns = columns[:len(df.columns)]
        df = df.iloc[1:].reset_index(drop=True)

        # Convert data to numeric format
        for col in df.columns:
            if col != 'Branch Name':
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.strip(), errors='coerce')

        return df

    except Exception as e:
        st.error(f"Error loading data from Google Drive: {str(e)}")
        return None

# Enhanced metrics calculation
def calculate_branch_metrics(df, selected_date):
    metrics = {}
    
    balance_col = f'Balance_{selected_date}'
    pending_col = f'Pending_{selected_date}'
    
    try:
        # Basic metrics with error handling
        metrics['total_balance'] = df[balance_col].sum()
        metrics['total_pending'] = df[pending_col].sum()
        metrics['total_reduced'] = df['Reduced Pending Amount'].sum()
        
        # Performance metrics
        metrics['top_balance_branch'] = df.nlargest(1, balance_col)['Branch Name'].iloc[0]
        metrics['lowest_pending_branch'] = df.nsmallest(1, pending_col)['Branch Name'].iloc[0]
        metrics['most_improved'] = df.nlargest(1, 'Reduced Pending Amount')['Branch Name'].iloc[0]
        
        # Enhanced efficiency metrics
        total = df[balance_col].sum() + df[pending_col].sum()
        metrics['collection_ratio'] = (df[balance_col].sum() / total * 100) if total != 0 else 0
        
        # Trend analysis
        change_col = f'Balance_Change_{selected_date}'
        if change_col in df.columns:
            metrics['avg_balance_change'] = df[change_col].mean()
            metrics['best_performing_branch'] = df.nlargest(1, change_col)['Branch Name'].iloc[0]
            metrics['worst_performing_branch'] = df.nsmallest(1, change_col)['Branch Name'].iloc[0]
        
        return metrics
    
    except Exception as e:
        st.error(f"Error calculating metrics: {str(e)}")
        return None

# Enhanced authentication
def check_password():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.login_attempts = 0

    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<div class='login-container'>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center; margin-bottom: 20px;'>Dashboard Login</h2>", unsafe_allow_html=True)
            username = st.text_input("Username").lower()
            password = st.text_input("Password", type="password")

            if st.button("Login"):
                if st.session_state.login_attempts >= 3:
                    st.error("Too many failed attempts. Please try again later.")
                    time.sleep(5)
                    return False

                if username in CREDENTIALS and CREDENTIALS[username] == hashlib.sha256(password.encode()).hexdigest():
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.experimental_rerun()
                else:
                    st.session_state.login_attempts += 1
                    st.error("Invalid credentials")
            st.markdown("</div>", unsafe_allow_html=True)
        return False
    return True

def style_comparison_df(df, dates):
    """
    Style the comparison DataFrame with corrected color coding:
    - Green when pending amount decreases (improvement)
    - Red when pending amount increases (deterioration)
    """
    def highlight_pending_changes(row):
        styles = [''] * len(df.columns)
        
        for i, date in enumerate(dates):
            if i < len(dates) - 1:  # Skip the last date as it has no next date to compare
                current_pending_col = f'Pending_{date}'
                next_pending_col = f'Pending_{dates[i+1]}'
                
                if current_pending_col in df.columns and next_pending_col in df.columns:
                    current_pending = row[current_pending_col]
                    next_pending = row[next_pending_col]
                    
                    # Get column index for current pending column
                    col_idx = df.columns.get_loc(current_pending_col)
                    
                    try:
                        current_pending = float(current_pending)
                        next_pending = float(next_pending)
                        
                        if pd.notna(current_pending) and pd.notna(next_pending):
                            if current_pending < next_pending:  # Pending amount decreased
                                styles[col_idx] = 'background-color: #92D050'  # Green
                            elif current_pending > next_pending:  # Pending amount increased
                                styles[col_idx] = 'background-color: #FF7575'  # Red
                    except:
                        pass
                        
        return styles
    
    # Format numbers and apply highlighting
    return df.style.apply(highlight_pending_changes, axis=1)\
                  .format({col: '₹{:,.2f}' for col in df.columns if col != 'Branch Name'})

def show_comparative_analysis(filtered_df, dates, selected_branches):
    """Enhanced comparative analysis with corrected highlighting"""
    st.subheader("Weekly Pending Amount Comparison")
    
    try:
        # Create comparison DataFrame
        comparison_df = pd.DataFrame()
        comparison_df['Branch Name'] = selected_branches
        
        # Add data for selected dates
        for date in dates:
            balance_col = f'Balance_{date}'
            pending_col = f'Pending_{date}'
            
            comparison_df[balance_col] = [
                filtered_df[filtered_df['Branch Name'] == branch][balance_col].iloc[0]
                for branch in selected_branches
            ]
            comparison_df[pending_col] = [
                filtered_df[filtered_df['Branch Name'] == branch][pending_col].iloc[0]
                for branch in selected_branches
            ]
        
        # Display styled table
        styled_df = style_comparison_df(comparison_df, dates)
        st.dataframe(
            styled_df,
            height=400,
            use_container_width=True
        )
        
        # Add summary analytics
        st.markdown("### Summary of Changes")
        for branch in selected_branches:
            branch_data = comparison_df[comparison_df['Branch Name'] == branch]
            changes = []
            
            for i in range(len(dates)-1):
                current_pending = branch_data[f'Pending_{dates[i]}'].iloc[0]
                prev_pending = branch_data[f'Pending_{dates[i+1]}'].iloc[0]
                
                if current_pending < prev_pending:
                    changes.append({
                        'date': dates[i],
                        'change': prev_pending - current_pending,
                        'type': 'decrease'
                    })
                elif current_pending > prev_pending:
                    changes.append({
                        'date': dates[i],
                        'change': current_pending - prev_pending,
                        'type': 'increase'
                    })
            
            if changes:
                st.markdown(f"**{branch}**")
                for change in changes:
                    if change['type'] == 'decrease':
                        st.markdown(f"- 🟢 Reduced by ₹{abs(change['change']):,.2f} on {change['date']}")
                    else:
                        st.markdown(f"- 🔴 Increased by ₹{abs(change['change']):,.2f} on {change['date']}")
        
        # Summary metrics
        st.markdown("### Overall Metrics")
        col1, col2 = st.columns(2)
        
        with col1:
            latest_total = comparison_df[f'Pending_{dates[0]}'].sum()
            prev_total = comparison_df[f'Pending_{dates[1]}'].sum()
            change = latest_total - prev_total
            st.metric(
                "Total Pending Change",
                f"₹{change:,.2f}",
                delta=-change  # Negative is good for pending
            )
        
        with col2:
            improvement = ((prev_total - latest_total) / prev_total * 100)
            st.metric(
                "Improvement Percentage",
                f"{improvement:.2f}%",
                delta=improvement
            )
            
    except Exception as e:
        st.error(f"Error in comparative analysis: {str(e)}")
        st.write("Please check the data structure and selected filters")

# Enhanced dashboard display
def show_collections_dashboard():
    df = load_data_from_drive(FILE_IDS['collections_data'])
    if df is None:
        return

    st.title("Collections Dashboard")
    
    # Display data info for verification
    st.sidebar.write("Data loaded successfully")
    st.sidebar.write("Number of branches:", len(df['Branch Name'].unique()))
    
    # Sidebar Controls
    st.sidebar.title("Analysis Controls")
    
    # Advanced Filtering
    filter_container = st.sidebar.container()
    with filter_container:
        st.subheader("Filters")
        
        # Branch Selection with Search
        all_branches = sorted(df['Branch Name'].unique().tolist())
        selected_branches = st.multiselect(
            "Select Branches (Search/Select)",
            options=all_branches,
            default=all_branches[:5] if len(all_branches) >= 5 else all_branches
        )
        
        # Date Selection
        dates = ['03-Nov-24', '27-Oct-24', '20-Oct-24', '12-Oct-24', '06-Oct-24', '30-Sep-24', '21-Sep-24']
        selected_date = st.selectbox("Select Analysis Date", dates)

    # Filter Data
    filtered_df = df.copy()
    if selected_branches:
        filtered_df = filtered_df[filtered_df['Branch Name'].isin(selected_branches)]
    
    balance_col = f'Balance_{selected_date}'
    pending_col = f'Pending_{selected_date}'
    
    # Main Dashboard
    st.title("Branch Reco Trend")
    
    # Key Metrics Dashboard
    metrics = calculate_branch_metrics(filtered_df, selected_date)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Total Balance",
            f"₹{metrics['total_balance']:,.2f}",
            delta=metrics['total_reduced']
        )
    with col2:
        st.metric(
            "Total Pending",
            f"₹{metrics['total_pending']:,.2f}"
        )
    with col3:
        st.metric(
            "Collection Ratio",
            f"{metrics['collection_ratio']:.1f}%"
        )
    with col4:
        st.metric(
            "Best Performing Branch",
            metrics['top_balance_branch']
        )

    # Analysis Tabs
    tab1, tab2, tab3 = st.tabs(["Trend Analysis", "Branch Performance", "Comparative Analysis"])
    
    with tab1:
        st.subheader("Balance & Pending Trends")
        
        try:
            # Prepare trend data safely
            trend_data = []
            for branch in selected_branches:
                branch_data = filtered_df[filtered_df['Branch Name'] == branch]
                if not branch_data.empty:
                    for date in dates:
                        balance_col = f'Balance_{date}'
                        pending_col = f'Pending_{date}'
                        if balance_col in branch_data.columns and pending_col in branch_data.columns:
                            trend_data.append({
                                'Branch': branch,
                                'Date': date,
                                'Balance': branch_data[balance_col].values[0],
                                'Pending': branch_data[pending_col].values[0]
                            })
            
            if trend_data:
                trend_df = pd.DataFrame(trend_data)
                
                # Create interactive plot
                fig = go.Figure()
                
                for branch in selected_branches:
                    branch_trend = trend_df[trend_df['Branch'] == branch]
                    if not branch_trend.empty:
                        # Balance line
                        fig.add_trace(go.Scatter(
                            x=branch_trend['Date'],
                            y=branch_trend['Balance'],
                            name=f"{branch} - Balance",
                            mode='lines+markers'
                        ))
                        # Pending line
                        fig.add_trace(go.Scatter(
                            x=branch_trend['Date'],
                            y=branch_trend['Pending'],
                            name=f"{branch} - Pending",
                            line=dict(dash='dot')
                        ))
                
                fig.update_layout(
                    title="Balance and Pending Trends",
                    xaxis_title="Date",
                    yaxis_title="Amount (₹)",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No trend data available for selected branches")
                
        except Exception as e:
            st.error(f"Error in trend analysis: {str(e)}")
            st.write("Please check the data structure and selected filters")
    
    with tab2:
        st.subheader("Branch Performance")
        try:
            # Performance metrics
            performance_df = filtered_df.copy()
            current_balance = f'Balance_{selected_date}'
            current_pending = f'Pending_{selected_date}'
            
            if current_balance in performance_df.columns and current_pending in performance_df.columns:
                performance_df['Current Balance'] = performance_df[current_balance]
                performance_df['Current Pending'] = performance_df[current_pending]
                performance_df['Net Position'] = performance_df['Current Balance'] - performance_df['Current Pending']
                
                # Performance Chart
                fig_perf = px.bar(
                    performance_df,
                    x='Branch Name',
                    y=['Current Balance', 'Current Pending', 'Net Position'],
                    title="Branch Performance",
                    barmode='group'
                )
                st.plotly_chart(fig_perf, use_container_width=True)
                
                # Metrics Table
                st.dataframe(
                    performance_df[['Branch Name', 'Current Balance', 'Current Pending', 'Net Position']]
                    .sort_values('Net Position', ascending=False),
                    height=400
                )
            else:
                st.warning("Performance data not available for selected date")
                
        except Exception as e:
            st.error(f"Error in performance analysis: {str(e)}")
    
    with tab3:
        st.subheader("Comparative Analysis")
        try:
            # Get all dates for comparison
            dates = ['03-Nov-24', '27-Oct-24', '20-Oct-24', '12-Oct-24', '06-Oct-24', '30-Sep-24', '21-Sep-24']
            
            # Create comparison DataFrame
            comparison_df = pd.DataFrame()
            comparison_df['Branch Name'] = selected_branches
            
            # Add data for all dates
            for date in dates:
                comparison_df[f'Balance_{date}'] = [
                    filtered_df[filtered_df['Branch Name'] == branch][f'Balance_{date}'].iloc[0]
                    for branch in selected_branches
                ]
                comparison_df[f'Pending_{date}'] = [
                    filtered_df[filtered_df['Branch Name'] == branch][f'Pending_{date}'].iloc[0]
                    for branch in selected_branches
                ]
            
            # Display styled comparison table
            st.markdown("### Weekly Pending Amount Comparison")
            styled_df = style_comparison_df(comparison_df, dates)
            st.dataframe(
                styled_df,
                height=400,
                use_container_width=True
            )
            
            # Add insights about pending amount trends
            st.markdown("### Pending Amount Trends")
            for branch in selected_branches:
                branch_data = comparison_df[comparison_df['Branch Name'] == branch]
                pending_trend = []
                
                # Compare pending amounts across dates
                for i in range(len(dates)-1):
                    current = branch_data[f'Pending_{dates[i]}'].iloc[0]
                    previous = branch_data[f'Pending_{dates[i+1]}'].iloc[0]
                    if current < previous:
                        pending_trend.append(f"Decreased from ₹{previous:,.2f} to ₹{current:,.2f}")
                    elif current > previous:
                        pending_trend.append(f"Increased from ₹{previous:,.2f} to ₹{current:,.2f}")
                
                if pending_trend:
                    st.markdown(f"**{branch}**:")
                    for trend in pending_trend[:3]:  # Show last 3 changes
                        st.markdown(f"- {trend}")
                    st.markdown("---")
            
        except Exception as e:
            st.error(f"Error in comparative analysis: {str(e)}")
            st.write("Error details:", str(e))

    # Export Options
    st.sidebar.markdown("---")
    st.sidebar.subheader("Export Options")
    
    if st.sidebar.button("Export Complete Analysis"):
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                filtered_df.to_excel(writer, sheet_name='Raw Data', index=False)
                if 'trend_df' in locals():
                    trend_df.to_excel(writer, sheet_name='Trends', index=False)
                if 'performance_df' in locals():
                    performance_df.to_excel(writer, sheet_name='Performance', index=False)
                if 'compare_df' in locals():
                    compare_df.to_excel(writer, sheet_name='Comparison', index=False)
            
            st.sidebar.download_button(
                label="📥 Download Full Report",
                data=output.getvalue(),
                file_name=f"collection_analysis_{selected_date}.xlsx",
                mime="application/vnd.ms-excel"
            )
        except Exception as e:
            st.sidebar.error(f"Error exporting data: {str(e)}")

def style_sdr_trend(df):
    """
    Style the SDR trend dataframe with correct color coding:
    - Green when value decreases (improvement)
    - Red when value increases (deterioration)
    - Yellow for no change
    """
    def color_values(val, col_name):
        try:
            if col_name == 'Reduced OS':
                # For Reduced OS column, negative is good (green)
                if pd.isna(val):
                    return ''
                elif val < 0:
                    return 'background-color: #92D050'  # Green
                elif val > 0:
                    return 'background-color: #FF7575'  # Red
                else:
                    return 'background-color: #FFFF00'  # Yellow
            else:
                # Get the date columns in order
                date_cols = [col for col in df.columns if col not in ['Ageing Category', 'Reduced OS']]
                date_cols.sort(reverse=True)  # Most recent first
                
                if col_name in date_cols:
                    col_idx = date_cols.index(col_name)
                    if col_idx < len(date_cols) - 1:  # If not the last date
                        next_col = date_cols[col_idx + 1]
                        current_val = val
                        next_val = df.loc[df[col_name] == val, next_col].iloc[0]
                        
                        if pd.isna(current_val) or pd.isna(next_val):
                            return ''
                        elif current_val < next_val:  # Decreased (improved)
                            return 'background-color: #92D050'  # Green
                        elif current_val > next_val:  # Increased (deteriorated)
                            return 'background-color: #FF7575'  # Red
                        else:
                            return 'background-color: #FFFF00'  # Yellow
            return ''
        except:
            return ''
    
    # Apply styling
    styled = df.style.apply(lambda x: [color_values(val, col) for val, col in zip(x, x.index)], axis=1)
    
    # Format numbers
    numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
    return styled.format("{:.2f}", subset=numeric_columns)

def show_sdr_dashboard():
    df = load_data_from_drive(FILE_IDS['sdr_trend'])
    if df is None:
        return

    st.title("CSD SDR Trend Analysis")
    
    try:
        # Get date columns in correct order
        date_columns = [col for col in df.columns 
                       if col not in ['Ageing Category', 'Reduced OS']]
        date_columns.sort(reverse=True)  # Most recent first
        
        # Display current data
        st.markdown("### SDR Ageing Analysis")
        styled_df = style_sdr_trend(df)
        st.dataframe(styled_df, height=400, use_container_width=True)
        
        # Summary metrics
        st.markdown("### Summary Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_reduced = df['Reduced OS'].sum()
            st.metric(
                "Total Reduced OS",
                f"{total_reduced:,.2f}",
                delta=total_reduced
            )
        
        with col2:
            latest_date = date_columns[0]
            prev_date = date_columns[1]
            latest_total = df[latest_date].sum()
            prev_total = df[prev_date].sum()
            change = latest_total - prev_total
            st.metric(
                f"Latest Total ({latest_date})",
                f"{latest_total:,.2f}",
                delta=-change  # Negative change is good
            )
        
        with col3:
            reduction_percent = ((prev_total - latest_total) / prev_total * 100)
            st.metric(
                "Week-on-Week Improvement",
                f"{reduction_percent:.2f}%",
                delta=reduction_percent
            )
        
        # Trend Analysis
        st.markdown("### Trend Analysis")
        
        # Create trend data
        trend_data = []
        for idx, row in df.iterrows():
            for date in date_columns:
                trend_data.append({
                    'Ageing Category': row['Ageing Category'],
                    'Date': date,
                    'Amount': row[date]
                })
        
        trend_df = pd.DataFrame(trend_data)
        
        # Line chart for trends
        fig = px.line(
            trend_df,
            x='Date',
            y='Amount',
            color='Ageing Category',
            title="SDR Trends by Ageing Category"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Category Analysis
        st.markdown("### Category-wise Analysis")
        
        latest_date = date_columns[0]
        prev_date = date_columns[1]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart for latest distribution
            fig_pie = px.pie(
                df,
                values=latest_date,
                names='Ageing Category',
                title=f"Distribution as of {latest_date}"
            )
            st.plotly_chart(fig_pie)
        
        with col2:
            # Bar chart for changes
            df_changes = df.copy()
            df_changes['Change'] = df_changes[latest_date] - df_changes[prev_date]
            
            fig_changes = px.bar(
                df_changes,
                x='Ageing Category',
                y='Change',
                title=f"Changes from {prev_date} to {latest_date}",
                color='Change',
                color_continuous_scale=['green', 'yellow', 'red']
            )
            st.plotly_chart(fig_changes)
        
        # Export Option
        if st.sidebar.button("Export SDR Analysis"):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='SDR Data', index=False)
                trend_df.to_excel(writer, sheet_name='Trend Analysis', index=False)
            
            st.sidebar.download_button(
                label="📥 Download SDR Report",
                data=buffer.getvalue(),
                file_name=f"sdr_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
    except Exception as e:
        st.error(f"Error in SDR analysis: {str(e)}")
        st.write("Error details:", str(e))

def show_itss_dashboard():
    df = load_data_from_drive(FILE_IDS['itss_tender'])
    if df is None:
        return

    st.title("ITSS Tender Analysis")
    
    try:
        # Define aging categories
        aging_categories = [
            '61-90', '91-120', '121-180', '181-360',
            '361-720', 'More than 2 Yr'
        ]
        
        # Date selection
        dates = sorted(df['Date'].unique(), reverse=True)
        selected_date = st.selectbox(
            "Select Date for Analysis",
            dates,
            format_func=lambda x: x.strftime('%Y-%m-%d')
        )
        
        # Filter data for selected date
        current_data = df[df['Date'] == selected_date].copy()
        
        # Summary metrics
        st.markdown("### Summary Metrics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            total_outstanding = current_data[aging_categories].sum().sum()
            st.metric(
                "Total Outstanding",
                f"₹{total_outstanding:.2f} Lakhs"
            )
        
        with col2:
            high_risk = current_data[['361-720', 'More than 2 Yr']].sum().sum()
            st.metric(
                "High Risk Amount",
                f"₹{high_risk:.2f} Lakhs",
                f"{(high_risk/total_outstanding*100 if total_outstanding else 0):.1f}%"
            )
        
        with col3:
            active_accounts = len(current_data[current_data[aging_categories].sum(axis=1) > 0])
            st.metric(
                "Active Accounts",
                str(active_accounts)
            )
        
        # Main data display
        st.markdown("### Account-wise Aging Analysis")
        display_cols = ['Account Name'] + aging_categories
        st.dataframe(
            style_itss_data(current_data[display_cols], aging_categories),
            height=400,
            use_container_width=True
        )
        
        # Visualizations
        st.markdown("### Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution pie chart
            dist_data = current_data[aging_categories].sum()
            fig_pie = px.pie(
                values=dist_data.values,
                names=dist_data.index,
                title="Distribution by Aging Category"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Top accounts
            current_data['Total'] = current_data[aging_categories].sum(axis=1)
            top_accounts = current_data.nlargest(5, 'Total')
            fig_bar = px.bar(
                top_accounts,
                x='Account Name',
                y='Total',
                title="Top 5 Accounts by Outstanding"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Export option
        if st.sidebar.button("Export Analysis"):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                current_data[display_cols].to_excel(
                    writer, 
                    sheet_name='ITSS Analysis',
                    index=False
                )
            
            st.sidebar.download_button(
                label="📥 Download Report",
                data=buffer.getvalue(),
                file_name=f"itss_analysis_{selected_date.strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )
        
    except Exception as e:
        st.error(f"Error in ITSS analysis: {str(e)}")
        st.write("Error details:", str(e))
        st.write("Available columns:", list(df.columns))

def show_tsg_dashboard():
    df = load_data_from_drive(FILE_IDS['tsg_trend'])
    if df is None:
        return

    st.title("TSG Payment Receivables Trend Analysis")
    
    try:
        # Get date columns in correct order
        date_cols = [col for col in df.columns if col != 'Ageing Category']
        date_cols.sort(reverse=True)  # Most recent first
        
        # Summary metrics
        st.markdown("### Summary Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            latest_total = df[date_cols[0]].sum()
            prev_total = df[date_cols[1]].sum()
            change = latest_total - prev_total
            st.metric(
                f"Total Receivables ({date_cols[0]})",
                f"₹{latest_total:,.0f}",
                delta=f"₹{-change:,.0f}"
            )
        
        with col2:
            week_change_pct = ((prev_total - latest_total) / prev_total * 100)
            st.metric(
                "Week-on-Week Change",
                f"{week_change_pct:.2f}%",
                delta=week_change_pct
            )
            
        with col3:
            month_start = df[date_cols[-1]].sum()
            month_change = ((month_start - latest_total) / month_start * 100)
            st.metric(
                "Month-to-Date Change",
                f"{month_change:.2f}%",
                delta=month_change
            )
        
        # Main trend table
        st.markdown("### Ageing-wise Trend Analysis")
        styled_df = style_tsg_trend(df)
        st.dataframe(styled_df, height=400, use_container_width=True)
        
        # Trend Analysis
        st.markdown("### Trend Visualization")
        
        # Prepare data for plotting
        trend_data = df.melt(
            id_vars=['Ageing Category'],
            value_vars=date_cols,
            var_name='Date',
            value_name='Amount'
        )
        
        # Line chart
        fig_line = px.line(
            trend_data,
            x='Date',
            y='Amount',
            color='Ageing Category',
            title="Receivables Trend by Ageing Category"
        )
        fig_line.update_layout(yaxis_title="Amount (₹)")
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Category Analysis
        st.markdown("### Category-wise Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            # Latest distribution pie chart
            fig_pie = px.pie(
                df,
                values=date_cols[0],
                names='Ageing Category',
                title=f"Distribution as of {date_cols[0]}"
            )
            st.plotly_chart(fig_pie)
        
        with col2:
            # Week-on-week changes
            changes_df = pd.DataFrame({
                'Category': df['Ageing Category'],
                'Change': df[date_cols[0]] - df[date_cols[1]]
            })
            fig_changes = px.bar(
                changes_df,
                x='Category',
                y='Change',
                title="Week-on-Week Changes by Category",
                color='Change',
                color_continuous_scale=['green', 'yellow', 'red']
            )
            st.plotly_chart(fig_changes)
        
        # Export Option
        if st.sidebar.button("Export TSG Analysis"):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='TSG Trend', index=False)
            
            st.sidebar.download_button(
                label="📥 Download TSG Report",
                data=buffer.getvalue(),
                file_name=f"tsg_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
    except Exception as e:
        st.error(f"Error in TSG analysis: {str(e)}")
        st.write("Error details:", str(e))

# Main function
def main():
    if not check_password():
        return

    st.sidebar.title("Navigation")
    report_option = st.sidebar.radio(
        "Choose a Report",
        ["Collections Dashboard", "CSD SDR Trend Analysis", "TSG Payment Receivables", "ITSS Tender Analysis"]
    )

    if report_option == "Collections Dashboard":
        show_collections_dashboard()
    elif report_option == "CSD SDR Trend Analysis":
        show_sdr_dashboard()
    elif report_option == "TSG Payment Receivables":
        show_tsg_dashboard()
    elif report_option == "ITSS Tender Analysis":
        show_itss_dashboard()

    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

if __name__ == "__main__":
    main()