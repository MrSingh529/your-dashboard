import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import io
import base64

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

# Simplified credentials
CREDENTIALS = {
    "admin": "admin123",
    "ceo": "ceo123",
    "manager": "manager123"
}

def check_password():
    """Returns `True` if the user had a correct password."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        # Center the login form
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("""
                <div class="login-container">
                    <h2 style='text-align: center; margin-bottom: 20px;'>Dashboard Login</h2>
                </div>
            """, unsafe_allow_html=True)
            username = st.text_input("Username").lower()
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                if username in CREDENTIALS and CREDENTIALS[username] == password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        return False
    return True

def load_data():
    """
    Load data from Excel file with specific column structure
    """
    try:
        df = pd.read_excel("collections_data.xlsx")
        
        # Rename columns to match exact structure
        columns = {
            'Branch Name': 'Branch',
            'Reduced Pending Amount': 'Reduced_Pending',
            'Balance As On': 'Balance',
            'Pending Amount': 'Pending'
        }
        
        # Clean the dataframe
        df = clean_dataframe(df)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None
        
def clean_dataframe(df):
    """
    Clean and structure the dataframe for branch-wise analysis
    """
    try:
        # Keep only the required columns
        required_cols = ['Branch Name', 'Reduced Pending Amount']
        date_cols = []
        
        # Group columns by date
        for i in range(len(df.columns)):
            if 'Balance As On' in str(df.columns[i]):
                date = df.columns[i-1]
                balance_col = df.columns[i]
                pending_col = df.columns[i+1]
                
                date_cols.append({
                    'date': date,
                    'balance': balance_col,
                    'pending': pending_col
                })
        
        # Restructure the data
        clean_df = pd.DataFrame()
        clean_df['Branch'] = df['Branch Name']
        clean_df['Reduced_Pending'] = df['Reduced Pending Amount']
        
        for date_group in date_cols:
            date = pd.to_datetime(date_group['date']).strftime('%Y-%m-%d')
            clean_df[f'Balance_{date}'] = df[date_group['balance']]
            clean_df[f'Pending_{date}'] = df[date_group['pending']]
        
        return clean_df
    except Exception as e:
        st.error(f"Error cleaning data: {str(e)}")
        return df
 
def create_sample_data():
    """Create sample data when actual data isn't available"""
    dates = pd.date_range(start='2024-01-01', end='2024-03-31', freq='D')
    branch_data = pd.DataFrame({
        'Date': dates.repeat(5),
        'Branch Name': ['Kota', 'Guwahati', 'Kolkata', 'Faridabad', 'Rajkot'] * len(dates),
        'Invoice': np.random.uniform(1000, 10000, len(dates) * 5),
        'Collection': np.random.uniform(800, 9000, len(dates) * 5),
        'Outstanding': np.random.uniform(100, 2000, len(dates) * 5),
        'Region': ['North', 'East', 'East', 'North', 'West'] * len(dates)
    })
    return branch_data

def calculate_metrics(df):
    """Calculate key performance metrics with error handling"""
    try:
        metrics = {}
        
        # Total Collection (assuming column name might be different)
        collection_col = [col for col in df.columns if 'collection' in col.lower()]
        if collection_col:
            metrics['total_collection'] = df[collection_col[0]].sum()
        else:
            metrics['total_collection'] = 0
            
        # Total Outstanding
        outstanding_col = [col for col in df.columns if 'outstanding' in col.lower()]
        if outstanding_col:
            metrics['total_outstanding'] = df[outstanding_col[0]].sum()
        else:
            metrics['total_outstanding'] = 0
            
        # Collection Efficiency
        invoice_col = [col for col in df.columns if 'invoice' in col.lower()]
        if collection_col and invoice_col:
            metrics['collection_efficiency'] = (df[collection_col[0]].sum() / df[invoice_col[0]].sum() * 100)
        else:
            metrics['collection_efficiency'] = 0
            
        # Top Branch
        branch_col = [col for col in df.columns if any(x in col.lower() for x in ['branch', 'branch name'])]
        if branch_col and collection_col:
            metrics['top_branch'] = df.groupby(branch_col[0])[collection_col[0]].sum().idxmax()
        else:
            metrics['top_branch'] = "N/A"
            
        return metrics
    except Exception as e:
        st.error(f"Error calculating metrics: {str(e)}")
        return {
            'total_collection': 0,
            'total_outstanding': 0,
            'collection_efficiency': 0,
            'top_branch': "N/A"
        }

def show_login_page():
    """Display the login page"""
    st.markdown("""
        <div class="login-container">
            <h2 style='text-align: center; margin-bottom: 20px;'>Dashboard Login</h2>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if username in CREDENTIALS and CREDENTIALS[username]["password"] == password:
                st.session_state.authenticated = True
                st.session_state.user_role = CREDENTIALS[username]["role"]
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials")

def show_dashboard():
    """Display the main dashboard"""
    # Load data
    df = load_data()
    
    if df is None:
        st.error("Unable to load data. Please check your data file.")
        return
    
    # Sidebar filters
    st.sidebar.title("Filters")
    
    # Branch filter
    branches = sorted(df['Branch'].unique().tolist())
    selected_branches = st.sidebar.multiselect(
        "Select Branches",
        options=branches,
        default=branches[:5]  # Default to first 5 branches
    )
    
    # Filter data
    if selected_branches:
        filtered_df = df[df['Branch'].isin(selected_branches)]
    else:
        filtered_df = df
    
    # Main dashboard
    st.title("Branch-wise Collection Analysis")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    # Get latest date columns
    balance_cols = [col for col in df.columns if 'Balance_' in col]
    pending_cols = [col for col in df.columns if 'Pending_' in col]
    
    latest_balance_col = balance_cols[-1]
    latest_pending_col = pending_cols[-1]
    
    with col1:
        total_balance = filtered_df[latest_balance_col].sum()
        st.metric(
            "Total Current Balance",
            f"₹{total_balance:,.2f}"
        )
    
    with col2:
        total_pending = filtered_df[latest_pending_col].sum()
        st.metric(
            "Total Pending Amount",
            f"₹{total_pending:,.2f}"
        )
    
    with col3:
        total_reduced = filtered_df['Reduced_Pending'].sum()
        st.metric(
            "Total Reduced Amount",
            f"₹{total_reduced:,.2f}"
        )
    
    # Trend Analysis
    st.subheader("Balance Trend Analysis")
    
    # Prepare data for trend analysis
    trend_data = pd.melt(
        filtered_df,
        id_vars=['Branch'],
        value_vars=balance_cols,
        var_name='Date',
        value_name='Balance'
    )
    trend_data['Date'] = trend_data['Date'].str.replace('Balance_', '')
    trend_data['Date'] = pd.to_datetime(trend_data['Date'])
    
    fig = px.line(
        trend_data,
        x='Date',
        y='Balance',
        color='Branch',
        title="Balance Trend by Branch"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Pending Amount Analysis
    st.subheader("Pending Amount Analysis")
    pending_data = pd.melt(
        filtered_df,
        id_vars=['Branch'],
        value_vars=pending_cols,
        var_name='Date',
        value_name='Pending'
    )
    pending_data['Date'] = pending_data['Date'].str.replace('Pending_', '')
    pending_data['Date'] = pd.to_datetime(pending_data['Date'])
    
    fig_pending = px.bar(
        pending_data,
        x='Branch',
        y='Pending',
        color='Date',
        title="Pending Amount by Branch",
        barmode='group'
    )
    st.plotly_chart(fig_pending, use_container_width=True)
    
    # Detailed Data View
    st.subheader("Detailed Data View")
    st.dataframe(
        filtered_df.style.highlight_positive(color='lightgreen')
                       .highlight_negative(color='lightcoral'),
        height=400
    )
    
    # Export Option
    if st.sidebar.button("Export Data"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            filtered_df.to_excel(writer, sheet_name='Branch Analysis', index=False)
        
        st.sidebar.download_button(
            label="Download Excel File",
            data=output.getvalue(),
            file_name=f"branch_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel"
        )

def main():
    if not check_password():
        return
        
    show_dashboard()
    
    # Logout button in sidebar
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

if __name__ == "__main__":
    main()