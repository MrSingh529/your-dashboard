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
    Load and structure data with specific date columns and merged cells
    """
    try:
        # Read the Excel file
        df = pd.read_excel("collections_data.xlsx", header=None)
        
        # Create structured DataFrame
        dates = ['03-Nov-24', '27-Oct-24', '20-Oct-24', '12-Oct-24', '06-Oct-24', '30-Sep-24']
        
        # Create empty DataFrame with proper structure
        structured_data = []
        
        # Skip first row and last row (Grand Total)
        for row in range(1, len(df) - 1):
            branch_data = {
                'Branch Name': df.iloc[row, 0],
                'Reduced Pending Amount': df.iloc[row, 1]
            }
            
            # For each date, get Balance and Pending columns
            col_idx = 2  # Starting index for first date's data
            for date in dates:
                branch_data[f'Balance_{date}'] = df.iloc[row, col_idx]
                branch_data[f'Pending_{date}'] = df.iloc[row, col_idx + 1]
                col_idx += 2
            
            structured_data.append(branch_data)
        
        # Create DataFrame from structured data
        final_df = pd.DataFrame(structured_data)
        
        # Convert amount columns to numeric, handling currency formatting
        amount_columns = [col for col in final_df.columns if col != 'Branch Name']
        for col in amount_columns:
            final_df[col] = pd.to_numeric(final_df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        return final_df
    
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
    branches = sorted(df['Branch Name'].unique().tolist())
    selected_branches = st.sidebar.multiselect(
        "Select Branches",
        options=branches,
        default=branches[:5]
    )
    
    # Date filter
    dates = ['03-Nov-24', '27-Oct-24', '20-Oct-24', '12-Oct-24', '06-Oct-24', '30-Sep-24']
    selected_date = st.sidebar.selectbox("Select Date", dates)
    
    # Filter data
    filtered_df = df[df['Branch Name'].isin(selected_branches)] if selected_branches else df
    
    # Main dashboard
    st.title("Branch-wise Collection Analysis")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_reduced = filtered_df['Reduced Pending Amount'].sum()
        st.metric(
            "Total Reduced Pending",
            f"₹{total_reduced:,.2f}"
        )
    
    with col2:
        current_balance = filtered_df[f'Balance_{selected_date}'].sum()
        st.metric(
            f"Current Balance ({selected_date})",
            f"₹{current_balance:,.2f}"
        )
    
    with col3:
        current_pending = filtered_df[f'Pending_{selected_date}'].sum()
        st.metric(
            f"Current Pending ({selected_date})",
            f"₹{current_pending:,.2f}"
        )
    
    # Trend Analysis
    st.subheader("Balance Trend Analysis")
    
    # Prepare trend data
    trend_data = []
    for branch in selected_branches:
        branch_df = filtered_df[filtered_df['Branch Name'] == branch]
        for date in dates:
            trend_data.append({
                'Branch': branch,
                'Date': date,
                'Balance': branch_df[f'Balance_{date}'].iloc[0],
                'Pending': branch_df[f'Pending_{date}'].iloc[0]
            })
    
    trend_df = pd.DataFrame(trend_data)
    
    # Balance Trend
    fig_balance = px.line(
        trend_df,
        x='Date',
        y='Balance',
        color='Branch',
        title="Balance Trend by Branch"
    )
    st.plotly_chart(fig_balance, use_container_width=True)
    
    # Pending Amount Trend
    st.subheader("Pending Amount Analysis")
    fig_pending = px.bar(
        trend_df,
        x='Branch',
        y='Pending',
        color='Date',
        title="Pending Amount by Branch",
        barmode='group'
    )
    st.plotly_chart(fig_pending, use_container_width=True)
    
    # Branch Performance Table
    st.subheader("Branch Performance Summary")
    performance_df = filtered_df.copy()
    performance_df['Current Balance'] = performance_df[f'Balance_{selected_date}']
    performance_df['Current Pending'] = performance_df[f'Pending_{selected_date}']
    performance_df['Reduced Amount'] = performance_df['Reduced Pending Amount']
    
    summary_cols = ['Branch Name', 'Current Balance', 'Current Pending', 'Reduced Amount']
    st.dataframe(
        performance_df[summary_cols].sort_values('Current Balance', ascending=False),
        height=400
    )
    
    # Export Option
    if st.sidebar.button("Export Analysis"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            filtered_df.to_excel(writer, sheet_name='Detailed Analysis', index=False)
            trend_df.to_excel(writer, sheet_name='Trends', index=False)
        
        st.sidebar.download_button(
            label="Download Excel Report",
            data=output.getvalue(),
            file_name=f"branch_analysis_{selected_date}.xlsx",
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