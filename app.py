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
    Load and structure data with custom headers
    """
    try:
        # Read Excel file without headers first
        df = pd.read_excel("collections_data.xlsx", header=None)
        
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
        st.error(f"Error loading data: {str(e)}")
        # Debug information
        st.write("Available columns:", list(df.columns))
        st.write("Data sample:")
        st.write(df.head())
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
    """Display enhanced dashboard with advanced analytics"""
    # Load data
    df = load_data()
    
    if df is None:
        st.error("Unable to load data. Please check your Excel file.")
        return
    
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
    st.title("Collections & Outstanding Analysis")
    
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
            col1, col2 = st.columns(2)
            with col1:
                date1 = st.selectbox("First Date", dates, index=0)
            with col2:
                date2 = st.selectbox("Second Date", dates, index=len(dates)-1)
            
            # Calculate changes
            compare_df = pd.DataFrame()
            compare_df['Branch'] = selected_branches
            
            for branch in selected_branches:
                branch_data = filtered_df[filtered_df['Branch Name'] == branch]
                if not branch_data.empty:
                    compare_df.loc[compare_df['Branch'] == branch, f'Balance_{date1}'] = \
                        branch_data[f'Balance_{date1}'].values[0]
                    compare_df.loc[compare_df['Branch'] == branch, f'Balance_{date2}'] = \
                        branch_data[f'Balance_{date2}'].values[0]
            
            compare_df['Change'] = compare_df[f'Balance_{date2}'] - compare_df[f'Balance_{date1}']
            compare_df['Change%'] = (compare_df['Change'] / compare_df[f'Balance_{date1}'] * 100).round(2)
            
            # Comparison Chart
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Bar(
                x=compare_df['Branch'],
                y=compare_df['Change'],
                name='Change in Balance',
                marker_color=np.where(compare_df['Change'] >= 0, 'green', 'red')
            ))
            fig_comp.update_layout(title=f"Balance Change ({date1} vs {date2})")
            st.plotly_chart(fig_comp, use_container_width=True)
            
            # Comparison Table
            st.dataframe(compare_df.sort_values('Change', ascending=False), height=400)
            
        except Exception as e:
            st.error(f"Error in comparative analysis: {str(e)}")

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