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

# Enhanced dashboard display
def show_collections_dashboard():
    df = load_data_from_drive(FILE_IDS['collections_data'])
    if df is None:
        return

    st.title("Collections Dashboard")
    
    # Filters
    st.sidebar.title("Filter Options")
    selected_date = st.sidebar.selectbox(
        "Select Date for Analysis:",
        sorted([col for col in df.columns if 'Balance_' in col], reverse=True)
    )

    # Calculate Metrics
    balance_col = f"Balance_{selected_date.split('_')[-1]}"
    pending_col = f"Pending_{selected_date.split('_')[-1]}"
    
    try:
        avg_balance_change = df[balance_col].pct_change().replace([np.inf, -np.inf], np.nan).mean() * 100
        avg_balance_change_display = f"{avg_balance_change:.2f}%" if not pd.isna(avg_balance_change) else "N/A"
    except ZeroDivisionError:
        avg_balance_change_display = "N/A"
    
    metrics = {
        'total_balance': df[balance_col].sum(),
        'total_pending': df[pending_col].sum(),
        'avg_balance_change': avg_balance_change_display
    }
    
    # Display Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Balance", f"₹{metrics['total_balance']:,.2f}")
    with col2:
        st.metric("Total Pending", f"₹{metrics['total_pending']:,.2f}")
    with col3:
        st.metric("Average Balance Change", metrics['avg_balance_change'])
    
    # Highlight Increase/Decrease
    st.subheader("Branch-wise Balance and Pending Amounts with Changes")
    try:
        date_columns = [col for col in df.columns if 'Pending_' in col]
        comparison_df = df[['Branch Name'] + date_columns].copy()

        # Calculate changes between weeks
        for i in range(len(date_columns) - 1):
            current_col = date_columns[i]
            prev_col = date_columns[i + 1]
            comparison_df[f'Change_{current_col}'] = df[current_col] - df[prev_col]

        # Apply color formatting for improvements and regressions
        def highlight_changes(val):
            if pd.isna(val):
                return ''
            elif val < 0:
                return 'background-color: #92D050'  # Green for decrease in pending amount
            elif val > 0:
                return 'background-color: #FF7575'  # Red for increase in pending amount
            else:
                return ''

        styled_comparison_df = comparison_df.style.applymap(highlight_changes, subset=[col for col in comparison_df.columns if 'Change_' in col])
        st.dataframe(styled_comparison_df, height=600, use_container_width=True)
    except Exception as e:
        st.error(f"Error in highlighting changes: {str(e)}")

def show_sdr_dashboard():
    df = load_data_from_drive(FILE_IDS['sdr_trend'])
    if df is None:
        return

    st.title("CSD SDR Trend Analysis")
    
    # Filters
    st.sidebar.title("Filter Options")
    selected_date = st.sidebar.selectbox(
        "Select Date for Analysis:",
        sorted([col for col in df.columns if 'Balance_' in col], reverse=True)
    )

    # Calculate Metrics
    balance_col = f"Balance_{selected_date.split('_')[-1]}"
    pending_col = f"Pending_{selected_date.split('_')[-1]}"
    
    metrics = {
        'total_balance': df[balance_col].sum(),
        'total_pending': df[pending_col].sum(),
        'avg_balance_change': df[balance_col].pct_change().mean() * 100
    }
    
    # Display Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Balance", f"₹{metrics['total_balance']:,.2f}")
    with col2:
        st.metric("Total Pending", f"₹{metrics['total_pending']:,.2f}")
    with col3:
        st.metric("Average Balance Change", f"{metrics['avg_balance_change']:.2f}%")
    
    # Visualization
    st.subheader("SDR Trend by Ageing Category")
    trend_data = df.melt(
        id_vars=['Branch Name'],
        value_vars=[balance_col, pending_col],
        var_name='Category',
        value_name='Amount'
    )
    
    fig = px.bar(
        trend_data,
        x='Branch Name',
        y='Amount',
        color='Category',
        barmode='group',
        title="Branch-wise SDR Balance and Pending Amounts"
    )
    st.plotly_chart(fig, use_container_width=True)

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
    
    # Filters
    st.sidebar.title("Filter Options")
    selected_date = st.sidebar.selectbox(
        "Select Date for Analysis:",
        sorted([col for col in df.columns if 'Balance_' in col], reverse=True)
    )

    # Calculate Metrics
    balance_col = f"Balance_{selected_date.split('_')[-1]}"
    pending_col = f"Pending_{selected_date.split('_')[-1]}"
    
    metrics = {
        'total_balance': df[balance_col].sum(),
        'total_pending': df[pending_col].sum(),
        'avg_balance_change': df[balance_col].pct_change().mean() * 100
    }
    
    # Display Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Balance", f"₹{metrics['total_balance']:,.2f}")
    with col2:
        st.metric("Total Pending", f"₹{metrics['total_pending']:,.2f}")
    with col3:
        st.metric("Average Balance Change", f"{metrics['avg_balance_change']:.2f}%")
    
    # Visualization
    st.subheader("Receivables Trend by Ageing Category")
    trend_data = df.melt(
        id_vars=['Branch Name'],
        value_vars=[balance_col, pending_col],
        var_name='Category',
        value_name='Amount'
    )
    
    fig = px.bar(
        trend_data,
        x='Branch Name',
        y='Amount',
        color='Category',
        barmode='group',
        title="Branch-wise Balance and Pending Amounts"
    )
    st.plotly_chart(fig, use_container_width=True)

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