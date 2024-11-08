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
    Load data from your Excel files or database
    """
    try:
        df = pd.read_excel("collections_data.xlsx")
        
        # Display available columns for debugging
        st.sidebar.write("Available columns:", list(df.columns))
        
        # Display data sample for verification
        st.sidebar.write("Data sample:")
        st.sidebar.dataframe(df.head(2))
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return create_sample_data()
        
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
    # Load data first
    df = load_data()
    
    # Sidebar filters
    st.sidebar.title("Filters")
    
    # Dynamic branch filter based on actual data
    branch_col = [col for col in df.columns if any(x in col.lower() for x in ['branch', 'branch name'])]
    if branch_col:
        branches = ["All"] + sorted(df[branch_col[0]].unique().tolist())
        selected_branches = st.sidebar.multiselect("Select Branches", branches, default="All")
    
    # Dynamic amount range filter
    st.sidebar.subheader("Amount Range")
    amount_col = [col for col in df.columns if any(x in col.lower() for x in ['outstanding', 'amount', 'balance'])]
    if amount_col:
        min_val = float(df[amount_col[0]].min())
        max_val = float(df[amount_col[0]].max())
        min_amount = st.sidebar.number_input("Minimum Amount", value=min_val)
        max_amount = st.sidebar.number_input("Maximum Amount", value=max_val)
    
    # Apply filters
    filtered_df = df.copy()
    if branch_col and selected_branches != ["All"]:
        filtered_df = filtered_df[filtered_df[branch_col[0]].isin(selected_branches)]
    if amount_col:
        filtered_df = filtered_df[
            (filtered_df[amount_col[0]] >= min_amount) & 
            (filtered_df[amount_col[0]] <= max_amount)
        ]
    
    # Main dashboard content
    st.title("Collections & Outstanding Analysis Dashboard")
    
    # Display data preview
    st.subheader("Data Preview")
    st.dataframe(filtered_df.head(), height=200)
    
    # Key Metrics
    metrics = calculate_metrics(filtered_df)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Collections",
            f"₹{metrics['total_collection']:,.2f}"
        )
    with col2:
        st.metric(
            "Total Outstanding",
            f"₹{metrics['total_outstanding']:,.2f}"
        )
    with col3:
        st.metric(
            "Collection Efficiency",
            f"{metrics['collection_efficiency']:.1f}%"
        )
    with col4:
        st.metric(
            "Top Performing Branch",
            metrics['top_branch']
        )
    
    # Allow user to download data
    st.sidebar.markdown("---")
    st.sidebar.subheader("Export Options")
    if st.sidebar.button("Export to Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            filtered_df.to_excel(writer, sheet_name='Detailed Data', index=False)
        
        st.sidebar.download_button(
            label="Download Excel File",
            data=output.getvalue(),
            file_name=f"collection_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
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