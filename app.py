```python
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

# Custom CSS for enhanced UI
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

# Authentication credentials (replace with secure database in production)
CREDENTIALS = {
    "admin": {
        "password": "admin123",
        "role": "admin"
    },
    "ceo": {
        "password": "ceo123",
        "role": "executive"
    },
    "manager": {
        "password": "manager123",
        "role": "manager"
    }
}

def load_data():
    """
    Load data from your Excel files or database
    Replace this with your actual data loading logic
    """
    # Example data structure
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
    """Calculate key performance metrics"""
    metrics = {
        'total_collection': df['Collection'].sum(),
        'total_outstanding': df['Outstanding'].sum(),
        'collection_efficiency': (df['Collection'].sum() / df['Invoice'].sum() * 100),
        'top_branch': df.groupby('Branch Name')['Collection'].sum().idxmax(),
        'most_improved': df.groupby('Branch Name')['Outstanding'].pct_change().idxmax()
    }
    return metrics

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
    # Sidebar filters
    st.sidebar.title("Filters")
    
    # Date range filter
    date_filter = st.sidebar.selectbox(
        "Select Date Range",
        ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Custom Range"]
    )
    
    if date_filter == "Custom Range":
        start_date = st.sidebar.date_input("Start Date")
        end_date = st.sidebar.date_input("End Date")
    
    # Region filter
    regions = ["All", "North", "South", "East", "West"]
    selected_region = st.sidebar.multiselect("Select Region", regions, default="All")
    
    # Branch filter
    branches = ["All", "Kota", "Guwahati", "Kolkata", "Faridabad", "Rajkot"]
    selected_branches = st.sidebar.multiselect("Select Branches", branches, default="All")
    
    # Amount range filter
    st.sidebar.subheader("Amount Range")
    min_amount = st.sidebar.number_input("Minimum Amount", value=0)
    max_amount = st.sidebar.number_input("Maximum Amount", value=1000000)
    
    # Load and filter data
    df = load_data()
    
    # Apply filters
    if selected_region != ["All"]:
        df = df[df['Region'].isin(selected_region)]
    if selected_branches != ["All"]:
        df = df[df['Branch Name'].isin(selected_branches)]
    df = df[
        (df['Outstanding'] >= min_amount) & 
        (df['Outstanding'] <= max_amount)
    ]
    
    # Main dashboard content
    st.title("Collections & Outstanding Analysis Dashboard")
    
    # Key Metrics Row
    metrics = calculate_metrics(df)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Collections",
            f"₹{metrics['total_collection']:,.2f}",
            f"{df['Collection'].pct_change().mean()*100:+.1f}%"
        )
    with col2:
        st.metric(
            "Total Outstanding",
            f"₹{metrics['total_outstanding']:,.2f}",
            f"{df['Outstanding'].pct_change().mean()*100:+.1f}%"
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
    
    # Trend Analysis
    st.subheader("Trend Analysis")
    tab1, tab2, tab3 = st.tabs(["Collections", "Outstanding", "Comparison"])
    
    with tab1:
        # Collections trend
        fig_collections = px.line(
            df.groupby('Date')['Collection'].sum().reset_index(),
            x='Date',
            y='Collection',
            title="Daily Collections Trend"
        )
        st.plotly_chart(fig_collections, use_container_width=True)
        
    with tab2:
        # Outstanding trend
        fig_outstanding = px.line(
            df.groupby('Date')['Outstanding'].sum().reset_index(),
            x='Date',
            y='Outstanding',
            title="Daily Outstanding Trend"
        )
        st.plotly_chart(fig_outstanding, use_container_width=True)
        
    with tab3:
        # Comparison chart
        fig_comparison = go.Figure()
        fig_comparison.add_trace(go.Scatter(
            x=df.groupby('Date')['Collection'].sum().index,
            y=df.groupby('Date')['Collection'].sum().values,
            name="Collections"
        ))
        fig_comparison.add_trace(go.Scatter(
            x=df.groupby('Date')['Outstanding'].sum().index,
            y=df.groupby('Date')['Outstanding'].sum().values,
            name="Outstanding"
        ))
        fig_comparison.update_layout(title="Collections vs Outstanding Trend")
        st.plotly_chart(fig_comparison, use_container_width=True)
    
    # Branch Performance Analysis
    st.subheader("Branch Performance Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Branch-wise collections
        fig_branch = px.bar(
            df.groupby('Branch Name')['Collection'].sum().reset_index(),
            x='Branch Name',
            y='Collection',
            title="Branch-wise Collections"
        )
        st.plotly_chart(fig_branch, use_container_width=True)
        
    with col2:
        # Collection efficiency by branch
        branch_efficiency = (df.groupby('Branch Name').agg({
            'Collection': 'sum',
            'Invoice': 'sum'
        }).reset_index())
        branch_efficiency['Efficiency'] = (
            branch_efficiency['Collection'] / branch_efficiency['Invoice'] * 100
        )
        fig_efficiency = px.bar(
            branch_efficiency,
            x='Branch Name',
            y='Efficiency',
            title="Collection Efficiency by Branch (%)"
        )
        st.plotly_chart(fig_efficiency, use_container_width=True)
    
    # Detailed Data View
    st.subheader("Detailed Data View")
    view_type = st.selectbox(
        "Select View",
        ["Summary View", "Detailed View", "Pivot Analysis"]
    )
    
    if view_type == "Summary View":
        summary_df = df.groupby('Branch Name').agg({
            'Invoice': 'sum',
            'Collection': 'sum',
            'Outstanding': 'sum'
        }).round(2)
        st.dataframe(
            summary_df.style.background_gradient(cmap='RdYlGn'),
            height=400
        )
        
    elif view_type == "Detailed View":
        st.dataframe(df, height=400)
        
    else:  # Pivot Analysis
        pivot_index = st.selectbox("Select Row", ["Branch Name", "Region"])
        pivot_values = st.selectbox("Select Values", ["Collection", "Outstanding"])
        pivot_df = pd.pivot_table(
            df,
            index=pivot_index,
            values=pivot_values,
            aggfunc='sum'
        )
        st.dataframe(
            pivot_df.style.background_gradient(cmap='RdYlGn'),
            height=400
        )
    
    # Export Options
    st.sidebar.markdown("---")
    st.sidebar.subheader("Export Options")
    if st.sidebar.button("Export to Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Detailed Data', index=False)
            summary_df.to_excel(writer, sheet_name='Summary')
        st.sidebar.download_button(
            label="Download Excel File",
            data=output.getvalue(),
            file_name=f"collection_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel"
        )

def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_dashboard()
        
        # Logout button in sidebar
        st.sidebar.markdown("---")
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

if __name__ == "__main__":
    main()
```