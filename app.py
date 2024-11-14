import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import io
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Configure page settings
st.set_page_config(
    page_title="Collections & Outstanding Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (keeping your existing CSS)
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

# Google Drive file IDs for each data set
COLLECTIONS_DATA_FILE_ID = '1zCSAx8jzOLewJXxOQlHjlUxXKoHbdopD'
ITSS_TENDER_FILE_ID = '1o6SjeyNuvSyt9c5uCsq4MGFlZV1moC3V'
SDR_TREND_FILE_ID = '1PixxavAM29QrtjZUh-TMpa8gDSE7lg60'
TSG_TREND_FILE_ID = '1Kf8nHi1shw6q0oozXFEScyE0bmhhPDPo'

# Authenticate with Google Drive
@st.cache_resource()
def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # This will prompt for Google login
    drive = GoogleDrive(gauth)
    return drive

drive = authenticate_drive()

# Load data from Google Drive
def load_data_from_drive(file_id):
    try:
        file = drive.CreateFile({'id': file_id})
        file.GetContentFile('data.xlsx')  # Save file locally
        df = pd.read_excel('data.xlsx', header=None)
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

# Dashboard function to load collections data
def show_collections_dashboard():
    df = load_data_from_drive(COLLECTIONS_DATA_FILE_ID)
    if df is None:
        st.error("Unable to load data. Please check the Google Drive file.")
        return

    # Prepare the data for usage (structure and assign columns)
    columns = ['Branch Name', 'Reduced Pending Amount'] + [f'Balance_{date}' for date in df.iloc[0, 2:].tolist()]
    df.columns = columns
    df = df.iloc[1:]  # Removing first row (which served as headers)

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
    st.metric("Total Balance", filtered_df[selected_date].sum())

    # Plots and Charts
    fig = px.bar(filtered_df, x='Branch Name', y=selected_date, title="Branch-wise Balance")
    st.plotly_chart(fig)

# Dashboard function for SDR Trend
def show_sdr_dashboard():
    df = load_data_from_drive(SDR_TREND_FILE_ID)
    if df is None:
        st.error("Unable to load SDR data. Please check the Google Drive file.")
        return

    st.title("SDR Trend Analysis")

    # Sidebar Filters
    date_columns = [col for col in df.columns if 'Balance_' in col]
    selected_date = st.sidebar.selectbox("Select Date for Analysis:", date_columns)

    # Display Data
    st.write("Showing SDR Trend Data", df.head())

# Dashboard function for TSG Payment Receivables
def show_tsg_dashboard():
    df = load_data_from_drive(TSG_TREND_FILE_ID)
    if df is None:
        st.error("Unable to load TSG data. Please check the Google Drive file.")
        return

    st.title("TSG Payment Receivables Analysis")

    # Sidebar Filters
    date_columns = [col for col in df.columns if 'Balance_' in col]
    selected_date = st.sidebar.selectbox("Select Date for Analysis:", date_columns)

    # Display Data
    st.write("Showing TSG Trend Data", df.head())

# Dashboard function for ITSS Tender Data
def show_itss_dashboard():
    df = load_data_from_drive(ITSS_TENDER_FILE_ID)
    if df is None:
        st.error("Unable to load ITSS data. Please check the Google Drive file.")
        return

    st.title("ITSS Tender Data Analysis")

    # Sidebar Filters
    date_columns = [col for col in df.columns if 'Balance_' in col]
    selected_date = st.sidebar.selectbox("Select Date for Analysis:", date_columns)

    # Display Data
    st.write("Showing ITSS Data", df.head())

# Main function to handle the entire app flow
def main():
    if not check_password():
        return

    # Sidebar for selecting the report
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

    # Logout option
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.experimental_rerun()

if __name__ == "__main__":
    main()