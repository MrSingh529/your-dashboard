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

# Configure page settings
st.set_page_config(
    page_title="Collections & Outstanding Analysis Dashboard",
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
    .login-container {
        max-width: 400px;
        margin: auto;
        padding: 20px;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
        margin-top: 10px;
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

CREDENTIALS = {
    "admin": hash_password("admin123"),
    "ceo": hash_password("ceo123"),
    "manager": hash_password("manager123")
}

# File IDs configuration with error handling
FILE_IDS = {
    'collections_data': '1zCSAx8jzOLewJXxOQlHjlUxXKoHbdopD',
    'itss_tender': '1o6SjeyNuvSyt9c5uCsq4MGFlZV1moC3V',
    'sdr_trend': '1PixxavAM29QrtjZUh-TMpa8gDSE7lg60',
    'tsg_trend': '1Kf8nHi1shw6q0oozXFEScyE0bmhhPDPo'
}

# Enhanced Google Drive authentication with retry mechanism
@st.cache_resource(ttl=3600)  # Cache for 1 hour
def authenticate_drive():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["google_drive"],
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            service = build('drive', 'v3', credentials=credentials)
            return service
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"❌ Failed to authenticate after {max_retries} attempts: {str(e)}")
                return None
            time.sleep(1)  # Wait before retrying

# Enhanced data loading with caching and progress tracking
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data_from_drive(file_id):
    try:
        with st.spinner("Loading data..."):
            service = authenticate_drive()
            if not service:
                return None

            request = service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            progress_bar = st.progress(0)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                progress_bar.progress(status.progress())

            file_buffer.seek(0)
            df = pd.read_excel(file_buffer, header=None)

            # Enhanced column handling
            date_columns = [
                datetime.strptime(date, '%d-%b-%y').strftime('%d-%b-%y')
                for date in ['03-Nov-24', '27-Oct-24', '20-Oct-24', '12-Oct-24', 
                            '06-Oct-24', '30-Sep-24', '21-Sep-24']
            ]

            columns = ['Branch Name', 'Reduced Pending Amount']
            for date in date_columns:
                columns.extend([f'Balance_{date}', f'Pending_{date}'])

            df.columns = columns[:len(df.columns)]
            df = df.iloc[1:].reset_index(drop=True)

            # Enhanced data cleaning
            for col in df.columns:
                if col != 'Branch Name':
                    df[col] = pd.to_numeric(
                        df[col].astype(str).str.replace(',', '').str.strip(), 
                        errors='coerce'
                    )
            
            # Add percentage change columns
            for i in range(len(date_columns)-1):
                current_date = date_columns[i]
                prev_date = date_columns[i+1]
                df[f'Balance_Change_{current_date}'] = (
                    (df[f'Balance_{current_date}'] - df[f'Balance_{prev_date}']) /
                    df[f'Balance_{prev_date}'] * 100
                ).round(2)

            return df

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
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
                
                if username in CREDENTIALS and CREDENTIALS[username] == hash_password(password):
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
    
    # Enhanced filters with session state
    if 'selected_branches' not in st.session_state:
        st.session_state.selected_branches = df['Branch Name'].unique().tolist()[:3]
    
    st.sidebar.title("Filter Options")
    selected_branches = st.sidebar.multiselect(
        "Select Branches:",
        df['Branch Name'].unique().tolist(),
        st.session_state.selected_branches
    )
    st.session_state.selected_branches = selected_branches
    
    date_columns = [col for col in df.columns if 'Balance_' in col]
    selected_date = st.sidebar.selectbox("Select Date for Analysis:", date_columns)
    
    # Filter data
    filtered_df = df[df['Branch Name'].isin(selected_branches)]
    
    # Calculate and display metrics
    metrics = calculate_branch_metrics(filtered_df, selected_date)
    if metrics:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Balance",
                f"₹{metrics['total_balance']:,.2f}",
                f"{metrics.get('avg_balance_change', 0):.1f}%"
            )
        with col2:
            st.metric(
                "Total Pending",
                f"₹{metrics['total_pending']:,.2f}"
            )
        with col3:
            st.metric(
                "Collection Ratio",
                f"{metrics['collection_ratio']:.2f}%"
            )
        
        # Enhanced visualizations
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(
                filtered_df,
                x='Branch Name',
                y=selected_date,
                title="Branch-wise Balance",
                color='Branch Name',
                labels={'value': 'Amount (₹)'}
            )
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
            
        with col2:
            if f'Balance_Change_{selected_date}' in filtered_df.columns:
                fig2 = px.scatter(
                    filtered_df,
                    x='Branch Name',
                    y=f'Balance_Change_{selected_date}',
                    size=selected_date,
                    title="Balance Change by Branch",
                    color=f'Balance_Change_{selected_date}',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig2, use_container_width=True)

# Main function
def main():
    if not check_password():
        return

    st.sidebar.title("Navigation")
    report_option = st.sidebar.radio(
        "Choose a Report",
        ["Collections Dashboard", "SDR Trend Analysis", 
         "TSG Payment Receivables", "ITSS Tender Analysis", "Exit"]
    )

    # Session info
    st.sidebar.markdown(f"Logged in as: **{st.session_state.username}**")
    
    if report_option == "Collections Dashboard":
        show_collections_dashboard()
    elif report_option == "SDR Trend Analysis":
        show_sdr_dashboard()
    elif report_option == "TSG Payment Receivables":
        show_tsg_dashboard()
    elif report_option == "ITSS Tender Analysis":
        show_itss_dashboard()
    elif report_option == "Exit":
        st.stop()

    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

if __name__ == "__main__":
    main()