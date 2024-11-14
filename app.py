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

# Configure page settings
st.set_page_config(
    page_title="Collections & Outstanding Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (keeping the existing CSS)
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
    </style>
""", unsafe_allow_html=True)

# Credentials for authentication
CREDENTIALS = {
    "admin": "admin123",
    "ceo": "ceo123",
    "manager": "manager123"
}

# File IDs for Google Drive spreadsheets
FILE_IDS = {
    'collections_data': '1zCSAx8jzOLewJXxOQlHjlUxXKoHbdopD',
    'itss_tender': '1o6SjeyNuvSyt9c5uCsq4MGFlZV1moC3V',
    'sdr_trend': '1PixxavAM29QrtjZUh-TMpa8gDSE7lg60',
    'tsg_trend': '1Kf8nHi1shw6q0oozXFEScyE0bmhhPDPo'
}

# Authenticate Google Drive API
@st.cache_resource()
def authenticate_drive():
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["google_drive"]
        )
        service = build('drive', 'v3', credentials=credentials)
        st.write("✅ Credentials loaded successfully.")
        return service
    except Exception as e:
        st.error(f"❌ Error loading credentials: {str(e)}")
        return None

drive_service = authenticate_drive()

# Load data from Google Drive
def load_data_from_drive(file_id):
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        # Reset file buffer's pointer to the beginning
        file_buffer.seek(0)
        
        df = pd.read_excel(file_buffer, header=None)
        
        # Create proper column names
        columns = [
            'Branch Name',
            'Reduced Pending Amount'
        ]
        
        # Add date-based column names
        dates = ['03-Nov-24', '27-Oct-24', '20-Oct-24', '12-Oct-24', '06-Oct-24', '30-Sep-24', '21-Sep-24']
        for date in dates:
            columns.extend([f'Balance_{date}', f'Pending_{date}'])
        
        # Assign columns to dataframe
        df.columns = columns[:len(df.columns)]
        
        # Skip the header row
        df = df.iloc[1:].reset_index(drop=True)
        
        # Convert amount columns to numeric
        for col in df.columns:
            if col != 'Branch Name':
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error loading data from Google Drive: {str(e)}")
        return None

# Check password for login
def check_password():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<div class='login-container'><h2 style='text-align: center; margin-bottom: 20px;'>Dashboard Login</h2></div>", unsafe_allow_html=True)
            username = st.text_input("Username").lower()
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if username in CREDENTIALS and CREDENTIALS[username] == password:
                    st.session_state.authenticated = True
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials")
        return False
    return True

def calculate_branch_metrics(df, selected_date):
    """Calculate advanced branch performance metrics"""
    metrics = {}

    balance_col = f'Balance_{selected_date}'
    pending_col = f'Pending_{selected_date}'

    # Basic metrics
    metrics['total_balance'] = df[balance_col].sum()
    metrics['total_pending'] = df[pending_col].sum()
    metrics['total_reduced'] = df['Reduced Pending Amount'].sum()

    # Performance metrics
    metrics['top_balance_branch'] = df.nlargest(1, balance_col)['Branch Name'].iloc[0]
    metrics['lowest_pending_branch'] = df.nsmallest(1, pending_col)['Branch Name'].iloc[0]
    metrics['most_improved'] = df.nlargest(1, 'Reduced Pending Amount')['Branch Name'].iloc[0]

    # Efficiency metrics
    metrics['collection_ratio'] = (
        (df[balance_col].sum() / (df[balance_col].sum() + df[pending_col].sum())) * 100
        if (df[balance_col].sum() + df[pending_col].sum()) != 0 else 0
    )

    return metrics

# Dashboard functions
def show_collections_dashboard():
    df = load_data_from_drive(FILE_IDS['collections_data'])
    if df is None:
        st.error("Unable to load data. Please check the Google Drive file.")
        return

    st.title("Collections Dashboard")

    # Sidebar Filters
    st.sidebar.title("Filter Options")
    all_branches = df['Branch Name'].unique().tolist()
    selected_branches = st.sidebar.multiselect("Select Branches:", all_branches, all_branches[:3])
    date_columns = [col for col in df.columns if 'Balance_' in col]
    selected_date = st.sidebar.selectbox("Select Date for Analysis:", date_columns)

    # Filtering Data
    filtered_df = df[df['Branch Name'].isin(selected_branches)]

    # Metrics
    metrics = calculate_branch_metrics(filtered_df, selected_date)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Balance", f"₹{metrics['total_balance']:,.2f}")
    with col2:
        st.metric("Total Pending", f"₹{metrics['total_pending']:,.2f}")
    with col3:
        st.metric("Collection Ratio", f"{metrics['collection_ratio']:.2f}%")

    # Plots and Charts
    fig = px.bar(filtered_df, x='Branch Name', y=selected_date, title="Branch-wise Balance")
    st.plotly_chart(fig)

def show_sdr_dashboard():
    df = load_data_from_drive(FILE_IDS['sdr_trend'])
    if df is None:
        st.error("Unable to load SDR data. Please check the Google Drive file.")
        return

    st.title("SDR Trend Analysis")
    st.write("SDR Data:", df.head())

def show_tsg_dashboard():
    df = load_data_from_drive(FILE_IDS['tsg_trend'])
    if df is None:
        st.error("Unable to load TSG data. Please check the Google Drive file.")
        return

    st.title("TSG Payment Receivables Analysis")
    st.write("TSG Data:", df.head())

def show_itss_dashboard():
    df = load_data_from_drive(FILE_IDS['itss_tender'])
    if df is None:
        st.error("Unable to load ITSS data. Please check the Google Drive file.")
        return

    st.title("ITSS Tender Analysis")
    st.write("ITSS Data:", df.head())

# Main function to handle the entire app flow
def main():
    if not check_password():
        return

    st.sidebar.title("Select Report Type")
    report_option = st.sidebar.radio(
        "Choose a Report",
        ["Collections Dashboard", "SDR Trend Analysis", "TSG Payment Receivables", "ITSS Tender Analysis", "Exit"]
    )

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
        st.session_state.authenticated = False
        st.experimental_rerun()

if __name__ == "__main__":
    main()