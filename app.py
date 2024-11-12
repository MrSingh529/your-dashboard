import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import io
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import secrets
import bcrypt

# Configure page settings
st.set_page_config(
    page_title="Collections & Outstanding Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

# Load data from OneDrive using Streamlit Secrets
def load_data_from_onedrive(link):
    try:
        response = requests.get(link)
        if response.status_code == 200:
            data = response.content
            df = pd.read_excel(io.BytesIO(data))
            return df
        else:
            st.error(f"Failed to load data from OneDrive: Status code {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error loading data from OneDrive: {str(e)}")
        return None

# Load specific data files based on links in Streamlit secrets
def load_collections_data():
    link = st.secrets["onedrive_links"]["collections_data"]
    return load_data_from_onedrive(link)

def load_itss_data():
    link = st.secrets["onedrive_links"]["itss_tender"]
    return load_data_from_onedrive(link)

def load_sdr_data():
    link = st.secrets["onedrive_links"]["sdr_trend"]
    return load_data_from_onedrive(link)

def load_tsg_data():
    link = st.secrets["onedrive_links"]["tsg_trend"]
    return load_data_from_onedrive(link)

# Branch Reconciliation Dashboard
def show_collections_dashboard():
    st.title("Collections & Outstanding Analysis Dashboard")
    df = load_collections_data()
    if df is None:
        st.error("Unable to load collections data. Please check your OneDrive link.")
        return

    # Sidebar filters
    st.sidebar.title("Analysis Controls")
    all_branches = df['Branch Name'].unique().tolist()
    selected_branches = st.sidebar.multiselect("Select Branches", options=all_branches, default=all_branches[:5])
    dates = [col.split('_')[1] for col in df.columns if col.startswith('Balance_')]
    selected_date = st.sidebar.selectbox("Select Analysis Date", options=dates)

    # Filter data
    filtered_df = df[df['Branch Name'].isin(selected_branches)] if selected_branches else df

    # Metrics
    balance_col = f"Balance_{selected_date}"
    pending_col = f"Pending_{selected_date}"
    total_balance = filtered_df[balance_col].sum()
    total_pending = filtered_df[pending_col].sum()

    col1, col2 = st.columns(2)
    col1.metric("Total Balance", f"₹{total_balance:,.2f}")
    col2.metric("Total Pending", f"₹{total_pending:,.2f}")

    # Trend Analysis
    st.subheader("Trend Analysis")
    trend_data = []
    for branch in selected_branches:
        branch_data = filtered_df[filtered_df['Branch Name'] == branch]
        for date in dates:
            trend_data.append({
                'Branch': branch,
                'Date': date,
                'Balance': branch_data[f'Balance_{date}'].values[0],
                'Pending': branch_data[f'Pending_{date}'].values[0]
            })
    trend_df = pd.DataFrame(trend_data)

    # Interactive plot
    fig = go.Figure()
    for branch in selected_branches:
        branch_trend = trend_df[trend_df['Branch'] == branch]
        fig.add_trace(go.Scatter(x=branch_trend['Date'], y=branch_trend['Balance'], 
                               name=f"{branch} - Balance", mode='lines+markers'))
        fig.add_trace(go.Scatter(x=branch_trend['Date'], y=branch_trend['Pending'], 
                               name=f"{branch} - Pending", line=dict(dash='dot')))
    fig.update_layout(title="Balance and Pending Trends", 
                     xaxis_title="Date", 
                     yaxis_title="Amount (₹)", 
                     hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

# SDR Dashboard
def show_sdr_dashboard():
    st.title("CSD SDR Trend Analysis")
    df = load_sdr_data()
    if df is None:
        st.error("Unable to load SDR data. Please check the data file.")
        return

    # Summary metrics
    total_reduced = df['Reduced OS'].sum()
    latest_date = df.columns[-1]
    prev_date = df.columns[-2]
    latest_total = df[latest_date].sum()
    prev_total = df[prev_date].sum()
    change = latest_total - prev_total

    st.metric("Total Reduced OS", f"{total_reduced:,.2f}")
    st.metric(f"Latest Total ({latest_date})", f"{latest_total:,.2f}", delta=-change)

    # Line Chart
    trend_data = df.melt(id_vars=['Ageing Category'], value_vars=df.columns[1:], 
                        var_name='Date', value_name='Amount')
    fig = px.line(trend_data, x='Date', y='Amount', color='Ageing Category', 
                 title="SDR Trends by Ageing Category")
    st.plotly_chart(fig, use_container_width=True)

# TSG Dashboard
def show_tsg_dashboard():
    st.title("TSG Payment Receivables Trend Analysis")
    df = load_tsg_data()
    if df is None:
        st.error("Unable to load TSG data. Please check the data file.")
        return

    # Summary metrics
    latest_date = df.columns[-1]
    prev_date = df.columns[-2]
    latest_total = df[latest_date].sum()
    prev_total = df[prev_date].sum()
    change = latest_total - prev_total

    st.metric(f"Total Receivables ({latest_date})", f"₹{latest_total:,.0f}", 
             delta=f"₹{-change:,.0f}")

    # Line Chart
    trend_data = df.melt(id_vars=['Ageing Category'], value_vars=df.columns[1:], 
                        var_name='Date', value_name='Amount')
    fig = px.line(trend_data, x='Date', y='Amount', color='Ageing Category', 
                 title="Receivables Trend by Ageing Category")
    st.plotly_chart(fig, use_container_width=True)

# ITSS Dashboard
def show_itss_dashboard():
    st.title("ITSS SDR Aging Analysis")
    df = load_itss_data()
    if df is None:
        st.error("Unable to load ITSS data. Please check your OneDrive link.")
        return

    # Summary metrics
    aging_categories = ['61-90', '91-120', '121-180', '181-360', '361-720', 'More than 2 Yr']
    total_outstanding = df[aging_categories].sum().sum()
    high_risk = df[['361-720', 'More than 2 Yr']].sum().sum()

    st.metric("Total Outstanding", f"₹{total_outstanding:.2f} Lakhs")
    st.metric("High Risk Amount", f"₹{high_risk:.2f} Lakhs", 
             f"{(high_risk/total_outstanding*100 if total_outstanding else 0):.1f}%")

    # Distribution Pie Chart
    dist_data = df[aging_categories].sum()
    fig_pie = px.pie(values=dist_data.values, names=dist_data.index, 
                    title="Distribution by Aging Category")
    st.plotly_chart(fig_pie, use_container_width=True)

def main():
    # Initialize session state
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None

    # Define credentials
    credentials = {
        "usernames": {
            "admin@rvsolutions.in": {
                "name": "Admin User",
                "password": "$2b$12$N5.FZF6H8TxMGoxmbHgQRuXb/ZOPtZpAe340qagZncUCGbVCnC4Wm"  # admin123
            },
            "ceo@rvsolutions.in": {
                "name": "CEO User",
                "password": "$2b$12$9.6TKF0bHJrJRNX9FSrRSeS/fyoYYm7ZP5pUjmR6bX7WYNYIFwj8e"  # ceo123
            },
            "manager@rvsolutions.in": {
                "name": "Manager User",
                "password": "$2b$12$GLV17UqLv7WaP3dPG4nMneL8hC3k7XVXQVaAE0XmZI9H9E3ZB.Y4O"  # manager123
            }
        }
    }

    # Create authenticator object
    authenticator = stauth.Authenticate(
        credentials,
        "rvsolutions_dashboard",
        "d4f56a74b8ac4a7b9eeb8ecf7185ed72",
        cookie_expiry_days=30
    )

    # Authentication
    name, authentication_status, username = authenticator.login('Login', 'main')

    # Handle authentication state
    if authentication_status:
        st.sidebar.success(f'Welcome {name}')
        
        # Department Reports Section
        st.sidebar.title("Department Reports")
        report_type = st.sidebar.radio(
            "Select Report Type",
            ["Branch Reco Trend", "CSD SDR Trend", "TSG Payment Receivables", "ITSS SDR Analysis"]
        )

        if report_type == "Branch Reco Trend":
            show_collections_dashboard()
        elif report_type == "CSD SDR Trend":
            show_sdr_dashboard()
        elif report_type == "TSG Payment Receivables":
            show_tsg_dashboard()
        elif report_type == "ITSS SDR Analysis":
            show_itss_dashboard()

        # Logout button
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.experimental_rerun()

    elif authentication_status is False:
        st.error("Username or password is incorrect")
    else:
        st.warning("Please enter your username and password")

if __name__ == "__main__":
    main()