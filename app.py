import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import io
import re
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
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Credentials for Google Drive (use Streamlit secrets to keep them secure)
CREDENTIALS = {
    "admin": hash_password(st.secrets["users"]["admin"]),
    "ceo": hash_password(st.secrets["users"]["ceo"]),
    "manager": hash_password(st.secrets["users"]["manager"])
}

FILE_IDS = {
    'collections_data': st.secrets["google_drive"]["collections_data"],
    'itss_tender': st.secrets["google_drive"]["itss_tender"],
    'sdr_trend': st.secrets["google_drive"]["sdr_trend"],
    'tsg_trend': st.secrets["google_drive"]["tsg_trend"]
}

@st.cache_resource(ttl=3600)  # Cache authentication for 1 hour
def authenticate_drive():
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["google_drive_credentials"],
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        st.error(f"Failed to authenticate with Google Drive: {str(e)}")
        return None

@st.cache_data(ttl=300)
def load_data_from_drive(file_id):
    """Load Collections Dashboard data from Google Drive"""
    try:
        service = authenticate_drive()
        if not service:
            return None

        # Download the file from Google Drive
        request = service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        # Read the data as a DataFrame
        file_buffer.seek(0)
        
        # Read the Excel file with explicit header selection
        df = pd.read_excel(file_buffer, header=0)  # Assuming the first row is the header
        
        # Verify the columns to ensure correct headers
        if df.columns[0] != "Branch Name":
            # If the first column isn't "Branch Name", assume that we may need to reassign columns
            st.write("Initial columns identified: ", df.columns.tolist())
            df.columns = df.iloc[0]  # Assign the first row as the header
            df = df.drop(0).reset_index(drop=True)  # Drop the first row from the data

        # Clean up the column names to remove any potential issues
        df.columns = [str(col).strip() for col in df.columns]

        # Ensure the expected 'Branch Name' column is present
        if 'Branch Name' not in df.columns:
            st.error("Failed to find the 'Branch Name' column. Please check the uploaded data format.")

        # Convert the 'Date' column to datetime if it exists
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        # Convert numeric columns to the correct type
        numeric_cols = df.columns.difference(['Branch Name', 'Date'])
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').replace('-', '0'), errors='coerce')

        # Display the first few rows for debugging purposes
        st.write("Data preview after processing:", df.head())

        return df

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def deduplicate_columns(columns):
    """Function to deduplicate column names."""
    new_columns = []
    seen = {}

    for col in columns:
        if col not in seen:
            seen[col] = 0
            new_columns.append(col)
        else:
            seen[col] += 1
            new_columns.append(f"{col}_{seen[col]}")

    return new_columns

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
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    st.error("Invalid credentials")
            st.markdown("</div>", unsafe_allow_html=True)
        return False
    return True
        
# Specific functions to load each dataset
@st.cache_data(ttl=300)
def load_itss_data():
    """Load ITSS Tender data from Google Drive with fixed column separation"""
    try:
        # Load data from Google Drive using the appropriate file_id
        df = load_data_from_drive(FILE_IDS['itss_tender'])
        
        if df is None:
            return None
        
        # Expected column names
        expected_columns = [
            'Account Name', 'Date', '61-90', '91-120', '121-180', 
            '181-360', '361-720', 'More than 2 Yr'
        ]
        
        # Assign columns if they don't match
        if len(df.columns) != len(expected_columns):
            st.error("Column mismatch detected. Current columns:")
            st.write(df.columns.tolist())
            st.write("Expected columns:")
            st.write(expected_columns)
            return None

        # Assign column names explicitly
        df.columns = expected_columns

        # Convert date column
        if 'Date' in df.columns:
            # First, clean the date strings
            df['Date'] = df['Date'].astype(str)
            df['Date'] = df['Date'].replace('None', None)
            df['Date'] = df['Date'].replace('', None)
            
            # Try to parse dates that are not None
            mask = df['Date'].notna()
            if mask.any():
                try:
                    df.loc[mask, 'Date'] = pd.to_datetime(df.loc[mask, 'Date'], format='%d-%m-%Y')
                except:
                    try:
                        df.loc[mask, 'Date'] = pd.to_datetime(df.loc[mask, 'Date'])
                    except:
                        st.error("Failed to parse dates")
            
            # For rows where Date is None or invalid, use current date
            df.loc[df['Date'].isna(), 'Date'] = pd.Timestamp.now().floor('D')

        # Convert numeric columns and handle '-' values
        numeric_columns = ['61-90', '91-120', '121-180', '181-360', '361-720', 'More than 2 Yr']
        for col in numeric_columns:
            df[col] = df[col].replace('-', '0')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

    except Exception as e:
        st.error(f"Error loading ITSS data: {str(e)}")
        return None

# Add this helper function to directly check the Excel file
def verify_excel_structure(file_path):
    """Verify the structure of the Excel file"""
    try:
        # Try reading with different options
        df_regular = pd.read_excel(file_path, engine='openpyxl')
        st.write("Standard Excel read:")
        st.write(df_regular.head())
        
        df_no_header = pd.read_excel(file_path, engine='openpyxl', header=None)
        st.write("\nExcel read without header:")
        st.write(df_no_header.head())
        
        # Show column information
        st.write("\nColumn names:")
        st.write(df_regular.columns.tolist())
        
        # Show data types
        st.write("\nData types:")
        st.write(df_regular.dtypes)
        
        return df_regular
        
    except Exception as e:
        st.error(f"Error verifying Excel structure: {str(e)}")
        return None

@st.cache_data(ttl=300)
def load_sdr_trend():
    """Load CSD SDR Trend data from Google Drive"""
    try:
        # Load data from Google Drive using the appropriate file_id
        service = authenticate_drive()
        if not service:
            return None

        request = service.files().get_media(fileId=FILE_IDS['sdr_trend'])
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_buffer.seek(0)

        # Read Excel and automatically assign headers
        df = pd.read_excel(file_buffer, engine='openpyxl', header=0)

        # Deduplicate column names manually if duplicates are found
        df.columns = deduplicate_columns(df.columns)

        # Convert amount columns to numeric (excluding 'Ageing Category' and 'Reduced OS')
        static_columns = ['Ageing Category', 'Reduced OS']
        for col in df.columns:
            if col not in static_columns:
                # Removing commas, converting to numeric, and filling NaNs with 0
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        return df

    except Exception as e:
        st.error(f"Error loading SDR data: {str(e)}")
        st.write("Error details:", str(e))
        return None

def deduplicate_columns(columns):
    """Function to deduplicate column names."""
    new_columns = []
    seen = {}

    for col in columns:
        if col not in seen:
            seen[col] = 0
            new_columns.append(col)
        else:
            seen[col] += 1
            new_columns.append(f"{col}_{seen[col]}")

    return new_columns

@st.cache_data(ttl=300)
def load_tsg_trend():
    """Load TSG Payment Receivables Trend data from Google Drive"""
    try:
        # Load data from Google Drive using the appropriate file_id
        df = load_data_from_drive(FILE_IDS['tsg_trend'])
        
        if df is None:
            return None

        # Assign column names to the DataFrame
        columns = [
            'Ageing Category', '8-Nov-24', '25-Oct-24', '18-Oct-24', 
            '4-Oct-24', '27-Sep-24', '13-Sep-24', '6-Sep-24', '2-Sep-24', '24-Aug-24',	'20-Aug-24',	'12-Aug-24',	'5-Aug-24'
        ]
        df.columns = columns[:len(df.columns)]

        # Convert amounts from string (with commas) to numeric, handling non-numeric values
        for col in df.columns:
            if col != 'Ageing Category':
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

        return df
    except Exception as e:
        st.error(f"Error loading TSG data: {str(e)}")
        st.write("Error details:", str(e))
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

def style_comparison_df(df, dates):
    """
    Style the comparison DataFrame with corrected color coding:
    - Green when pending amount decreases (improvement)
    - Red when pending amount increases (deterioration)
    """
    def highlight_pending_changes(row):
        styles = [''] * len(df.columns)
        
        for i, date in enumerate(dates):
            if i < len(dates) - 1:  # Skip the last date as it has no next date to compare
                current_pending_col = f'Pending_{date}'
                next_pending_col = f'Pending_{dates[i+1]}'
                
                if current_pending_col in df.columns and next_pending_col in df.columns:
                    current_pending = row[current_pending_col]
                    next_pending = row[next_pending_col]
                    
                    # Get column index for current pending column
                    col_idx = df.columns.get_loc(current_pending_col)
                    
                    try:
                        current_pending = float(current_pending)
                        next_pending = float(next_pending)
                        
                        if pd.notna(current_pending) and pd.notna(next_pending):
                            if current_pending < next_pending:  # Pending amount decreased
                                styles[col_idx] = 'background-color: #92D050'  # Green
                            elif current_pending > next_pending:  # Pending amount increased
                                styles[col_idx] = 'background-color: #FF7575'  # Red
                    except:
                        pass
                        
        return styles
    
    # Format numbers and apply highlighting
    return df.style.apply(highlight_pending_changes, axis=1)\
                  .format({col: '₹{:,.2f}' for col in df.columns if col != 'Branch Name'})

def show_comparative_analysis(filtered_df, dates, selected_branches):
    """Enhanced comparative analysis with corrected highlighting"""
    st.subheader("Weekly Pending Amount Comparison")
    
    try:
        # Create comparison DataFrame
        comparison_df = pd.DataFrame()
        comparison_df['Branch Name'] = selected_branches
        
        # Add data for selected dates
        for date in dates:
            balance_col = f'Balance_{date}'
            pending_col = f'Pending_{date}'
            
            comparison_df[balance_col] = [
                filtered_df[filtered_df['Branch Name'] == branch][balance_col].iloc[0]
                for branch in selected_branches
            ]
            comparison_df[pending_col] = [
                filtered_df[filtered_df['Branch Name'] == branch][pending_col].iloc[0]
                for branch in selected_branches
            ]
        
        # Display styled table
        styled_df = style_comparison_df(comparison_df, dates)
        st.dataframe(
            styled_df,
            height=400,
            use_container_width=True
        )
        
        # Add summary analytics
        st.markdown("### Summary of Changes")
        for branch in selected_branches:
            branch_data = comparison_df[comparison_df['Branch Name'] == branch]
            changes = []
            
            for i in range(len(dates)-1):
                current_pending = branch_data[f'Pending_{dates[i]}'].iloc[0]
                prev_pending = branch_data[f'Pending_{dates[i+1]}'].iloc[0]
                
                if current_pending < prev_pending:
                    changes.append({
                        'date': dates[i],
                        'change': prev_pending - current_pending,
                        'type': 'decrease'
                    })
                elif current_pending > prev_pending:
                    changes.append({
                        'date': dates[i],
                        'change': current_pending - prev_pending,
                        'type': 'increase'
                    })
            
            if changes:
                st.markdown(f"**{branch}**")
                for change in changes:
                    if change['type'] == 'decrease':
                        st.markdown(f"- 🟢 Reduced by ₹{abs(change['change']):,.2f} on {change['date']}")
                    else:
                        st.markdown(f"- 🔴 Increased by ₹{abs(change['change']):,.2f} on {change['date']}")
        
        # Summary metrics
        st.markdown("### Overall Metrics")
        col1, col2 = st.columns(2)
        
        with col1:
            latest_total = comparison_df[f'Pending_{dates[0]}'].sum()
            prev_total = comparison_df[f'Pending_{dates[1]}'].sum()
            change = latest_total - prev_total
            st.metric(
                "Total Pending Change",
                f"₹{change:,.2f}",
                delta=-change  # Negative is good for pending
            )
        
        with col2:
            improvement = ((prev_total - latest_total) / prev_total * 100)
            st.metric(
                "Improvement Percentage",
                f"{improvement:.2f}%",
                delta=improvement
            )
            
    except Exception as e:
        st.error(f"Error in comparative analysis: {str(e)}")
        st.write("Please check the data structure and selected filters")

# Enhanced dashboard display
def show_collections_dashboard():
    # Load data from Google Drive
    df = load_data_from_drive(FILE_IDS['collections_data'])
    if df is None:
        return

    # Debugging: Display columns to confirm the actual column names
    st.sidebar.write("Available columns in DataFrame:", list(df.columns))
    st.write("Data preview after processing:", df.head())

    # If 'Branch Name' column is not found, handle gracefully
    if 'Branch Name' not in df.columns:
        st.error("The column 'Branch Name' is not available in the dataset. Please verify the column names.")
        return

    st.title("Collections Dashboard")

    # Display data info for verification
    st.sidebar.write("Data loaded successfully")
    st.sidebar.write("Number of branches:", len(df['Branch Name'].unique()))

    # Sidebar Controls for Filtering
    st.sidebar.title("Analysis Controls")
    
    # Branch Selection with Search
    all_branches = sorted(df['Branch Name'].unique().tolist())
    selected_branches = st.multiselect(
        "Select Branches (Search/Select)",
        options=all_branches,
        default=all_branches[:5] if len(all_branches) >= 5 else all_branches
    )

    # Extract available dates from the "Date" column
    if 'Date' in df.columns:
        available_dates = df['Date'].dropna().unique()
        available_dates = sorted(available_dates, reverse=True)  # Sort dates in descending order
    else:
        available_dates = []

    # Handle case when no valid dates are found
    if len(available_dates) == 0:
        st.error("No valid dates found in the dataset for analysis.")
        return

    # Date Selection
    selected_date = st.selectbox("Select Analysis Date", available_dates, format_func=lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else "Invalid Date")

    # Filter Data based on Branches Selection and Date Selection
    filtered_df = df.copy()
    if selected_branches:
        filtered_df = filtered_df[filtered_df['Branch Name'].isin(selected_branches)]
    filtered_df = filtered_df[filtered_df['Date'] == selected_date]

    # Check if filtered data is empty
    if filtered_df.empty:
        st.warning("No data available for the selected branches and date.")
        return

    # Key Metrics Dashboard
    st.title("Branch Reco Trend")
    
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
                branch_data = df[df['Branch Name'] == branch]
                if not branch_data.empty:
                    for date in available_dates:
                        trend_data.append({
                            'Branch': branch,
                            'Date': date,
                            'Balance': branch_data[branch_data['Date'] == date]['Balance As On'].values[0] if not branch_data[branch_data['Date'] == date].empty else 0,
                            'Pending': branch_data[branch_data['Date'] == date]['Pending Amount'].values[0] if not branch_data[branch_data['Date'] == date].empty else 0
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
            if 'Balance As On' in performance_df.columns and 'Pending Amount' in performance_df.columns:
                performance_df['Net Position'] = performance_df['Balance As On'] - performance_df['Pending Amount']

                # Performance Chart
                fig_perf = px.bar(
                    performance_df,
                    x='Branch Name',
                    y=['Balance As On', 'Pending Amount', 'Net Position'],
                    title="Branch Performance",
                    barmode='group'
                )
                st.plotly_chart(fig_perf, use_container_width=True)

                # Metrics Table
                st.dataframe(
                    performance_df[['Branch Name', 'Balance As On', 'Pending Amount', 'Net Position']]
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
            # Create comparison DataFrame
            comparison_df = pd.DataFrame()
            comparison_df['Branch Name'] = selected_branches

            # Add data for all dates
            for date in available_dates:
                balance_col = next((col for col in filtered_df.columns if date in col and "Balance As On" in col), None)
                pending_col = next((col for col in filtered_df.columns if date in col and "Pending Amount" in col), None)

                if balance_col and pending_col:
                    comparison_df[f'Balance_{date}'] = [
                        filtered_df[filtered_df['Branch Name'] == branch][balance_col].iloc[0]
                        for branch in selected_branches
                    ]
                    comparison_df[f'Pending_{date}'] = [
                        filtered_df[filtered_df['Branch Name'] == branch][pending_col].iloc[0]
                        for branch in selected_branches
                    ]

            # Display styled comparison table
            st.markdown("### Weekly Pending Amount Comparison")
            styled_df = style_comparison_df(comparison_df, available_dates)
            st.dataframe(
                styled_df,
                height=400,
                use_container_width=True
            )

            st.write("Comparative analysis is being prepared...")
        except Exception as e:
            st.error(f"Error in comparative analysis: {str(e)}")
            st.write("Error details:", str(e))

    # Export Options
    st.sidebar.markdown("---")
    st.sidebar("Export Options")

    if st.sidebar.button("Export Complete Analysis"):
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                filtered_df.to_excel(writer, sheet_name='Raw Data', index=False)
                if 'trend_df' in locals():
                    trend_df.to_excel(writer, sheet_name='Trends', index=False)
                if 'performance_df' in locals():
                    performance_df.to_excel(writer, sheet_name='Performance', index=False)
                if 'comparison_df' in locals():
                    comparison_df.to_excel(writer, sheet_name='Comparison', index=False)

            st.sidebar.download_button(
                label="📥 Download Full Report",
                data=output.getvalue(),
                file_name=f"collection_analysis_{selected_date}.xlsx",
                mime="application/vnd.ms-excel"
            )
        except Exception as e:
            st.sidebar.error(f"Error exporting data: {str(e)}")

def style_sdr_trend(df):
    """
    Style the SDR trend dataframe with correct color coding:
    - Green when value decreases (improvement)
    - Red when value increases (deterioration)
    - Yellow for no change
    """
    def color_values(val, col_name):
        try:
            if col_name == 'Reduced OS':
                # For Reduced OS column, negative is good (green)
                if pd.isna(val):
                    return ''
                elif val < 0:
                    return 'background-color: #92D050'  # Green
                elif val > 0:
                    return 'background-color: #FF7575'  # Red
                else:
                    return 'background-color: #FFFF00'  # Yellow
            else:
                # Get the date columns in order
                date_cols = [col for col in df.columns if col not in ['Ageing Category', 'Reduced OS']]
                date_cols.sort(reverse=True)  # Most recent first
                
                if col_name in date_cols:
                    col_idx = date_cols.index(col_name)
                    if col_idx < len(date_cols) - 1:  # If not the last date
                        next_col = date_cols[col_idx + 1]
                        current_val = val
                        next_val = df.loc[df[col_name] == val, next_col].iloc[0]
                        
                        if pd.isna(current_val) or pd.isna(next_val):
                            return ''
                        elif current_val < next_val:  # Decreased (improved)
                            return 'background-color: #92D050'  # Green
                        elif current_val > next_val:  # Increased (deteriorated)
                            return 'background-color: #FF7575'  # Red
                        else:
                            return 'background-color: #FFFF00'  # Yellow
            return ''
        except:
            return ''
    
    # Apply styling
    styled = df.style.apply(lambda x: [color_values(val, col) for val, col in zip(x, x.index)], axis=1)
    
    # Format numbers
    numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
    return styled.format("{:.2f}", subset=numeric_columns)

def show_sdr_dashboard():
    df = load_sdr_trend()
    if df is None:
        return

    st.title("CSD SDR Trend Analysis")
    
    try:
        # Get date columns in correct order
        date_columns = [col for col in df.columns 
                       if col not in ['Ageing Category', 'Reduced OS']]
        date_columns.sort(reverse=True)  # Most recent first
        
        # Display current data
        st.markdown("### SDR Ageing Analysis")
        styled_df = style_sdr_trend(df)
        st.dataframe(styled_df, height=400, use_container_width=True)
        
        # Summary metrics
        st.markdown("### Summary Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_reduced = df['Reduced OS'].sum()
            st.metric(
                "Total Reduced OS",
                f"{total_reduced:,.2f}",
                delta=total_reduced
            )
        
        with col2:
            latest_date = date_columns[0]
            prev_date = date_columns[1]
            latest_total = df[latest_date].sum()
            prev_total = df[prev_date].sum()
            change = latest_total - prev_total
            st.metric(
                f"Latest Total ({latest_date})",
                f"{latest_total:,.2f}",
                delta=-change  # Negative change is good
            )
        
        with col3:
            reduction_percent = ((prev_total - latest_total) / prev_total * 100)
            st.metric(
                "Week-on-Week Improvement",
                f"{reduction_percent:.2f}%",
                delta=reduction_percent
            )
        
        # Trend Analysis
        st.markdown("### Trend Analysis")
        
        # Create trend data
        trend_data = []
        for idx, row in df.iterrows():
            for date in date_columns:
                trend_data.append({
                    'Ageing Category': row['Ageing Category'],
                    'Date': date,
                    'Amount': row[date]
                })
        
        trend_df = pd.DataFrame(trend_data)
        
        # Line chart for trends
        fig = px.line(
            trend_df,
            x='Date',
            y='Amount',
            color='Ageing Category',
            title="SDR Trends by Ageing Category"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Category Analysis
        st.markdown("### Category-wise Analysis")
        
        latest_date = date_columns[0]
        prev_date = date_columns[1]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart for latest distribution
            fig_pie = px.pie(
                df,
                values=latest_date,
                names='Ageing Category',
                title=f"Distribution as of {latest_date}"
            )
            st.plotly_chart(fig_pie)
        
        with col2:
            # Bar chart for changes
            df_changes = df.copy()
            df_changes['Change'] = df_changes[latest_date] - df_changes[prev_date]
            
            fig_changes = px.bar(
                df_changes,
                x='Ageing Category',
                y='Change',
                title=f"Changes from {prev_date} to {latest_date}",
                color='Change',
                color_continuous_scale=['green', 'yellow', 'red']
            )
            st.plotly_chart(fig_changes)
        
        # Export Option
        if st.sidebar.button("Export SDR Analysis"):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='SDR Data', index=False)
                trend_df.to_excel(writer, sheet_name='Trend Analysis', index=False)
            
            st.sidebar.download_button(
                label="📥 Download SDR Report",
                data=buffer.getvalue(),
                file_name=f"sdr_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
    except Exception as e:
        st.error(f"Error in SDR analysis: {str(e)}")
        st.write("Error details:", str(e))

def style_itss_data(df, aging_categories):
    """Style the ITSS dataframe"""
    def highlight_values(val):
        try:
            if pd.isna(val) or val == 0:
                return ''
            elif val > 0:
                return 'background-color: #FF7575'  # Red
            else:
                return 'background-color: #92D050'  # Green
        except:
            return ''
    
    # Apply styling
    return df.style.applymap(
        highlight_values,
        subset=aging_categories
    ).format(
        {col: '{:.2f}' for col in aging_categories}
    )

def style_itss_trend(df, selected_date):
    """Style the ITSS tender dataframe with color coding comparing to previous date"""
    def get_comparison_value(row, col):
        try:
            current_value = row[f"{selected_date}_{col}"]
            dates = sorted([c.split('_')[0] for c in df.columns if '_' in c and col in c], reverse=True)
            current_date_idx = dates.index(selected_date)
            if current_date_idx < len(dates) - 1:
                next_date = dates[current_date_idx + 1]
                previous_value = row[f"{next_date}_{col}"]
                if pd.notna(current_value) and pd.notna(previous_value):
                    return current_value - previous_value
            return None
        except:
            return None
    
    def color_changes(val, comparison_val):
        if pd.isna(val) or val == 0:
            return ''
        if comparison_val is not None:
            if comparison_val < 0:
                return 'background-color: #92D050'  # Green for decrease
            elif comparison_val > 0:
                return 'background-color: #FF7575'  # Red for increase
        return ''
    
    # Get aging categories
    aging_categories = ['61-90', '91-120', '121-180', '181-360', '361-720', 'More than 2 Yr']
    
    # Create StyleFrame
    comparison_styles = pd.DataFrame(index=df.index, columns=df.columns)
    
    for category in aging_categories:
        col_name = f"{selected_date}_{category}"
        if col_name in df.columns:
            comparison_values = df.apply(
                lambda row: get_comparison_value(row, category),
                axis=1
            )
            comparison_styles[col_name] = comparison_values.apply(
                lambda x: color_changes(x, x)
            )
    
    # Apply styling
    return df.style.apply(lambda _: comparison_styles, axis=None)\
                  .format(lambda x: '{:.2f}'.format(x) if isinstance(x, (int, float)) and pd.notna(x) else '-')    

def show_itss_dashboard():
    df = load_itss_data()
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
        valid_dates = sorted(df['Date'].unique(), reverse=True)
        if len(valid_dates) == 0:
            st.error("No valid dates found for analysis.")
            return
        
        selected_date = st.selectbox(
            "Select Date for Analysis",
            valid_dates,
            format_func=lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else "Invalid Date"
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

def style_tsg_trend(df):
    """
    Style the TSG trend dataframe with color coding:
    - Green when amount decreases (improvement)
    - Red when amount increases (deterioration)
    """
    def color_changes(row):
        styles = [''] * len(df.columns)
        
        # Get date columns (exclude 'Ageing Category' and any other non-date columns)
        date_cols = [col for col in df.columns if col != 'Ageing Category']
        date_cols.sort(reverse=True)  # Most recent first
        
        for i in range(len(date_cols)-1):
            current_col = date_cols[i]
            next_col = date_cols[i+1]
            current_val = row[current_col]
            next_val = row[next_col]
            
            col_idx = df.columns.get_loc(current_col)
            
            try:
                if pd.notna(current_val) and pd.notna(next_val):
                    if current_val < next_val:  # Amount decreased (improved)
                        styles[col_idx] = 'background-color: #92D050'  # Green
                    elif current_val > next_val:  # Amount increased (deteriorated)
                        styles[col_idx] = 'background-color: #FF7575'  # Red
            except:
                pass
                
        return styles
    
    # Format numbers and apply highlighting
    styled = df.style.apply(color_changes, axis=1)
    
    # Format large numbers with commas and proper decimal places
    return styled.format(lambda x: '{:,.0f}'.format(x) if pd.notna(x) and isinstance(x, (int, float)) else x)

def show_tsg_dashboard():
    df = load_tsg_trend()
    if df is None:
        return

    st.title("TSG Payment Receivables Trend Analysis")
    
    try:
        # Get date columns in correct order
        date_cols = [col for col in df.columns if col != 'Ageing Category']
        date_cols.sort(reverse=True)  # Most recent first
        
        # Summary metrics
        st.markdown("### Summary Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            latest_total = df[date_cols[0]].sum()
            prev_total = df[date_cols[1]].sum()
            change = latest_total - prev_total
            st.metric(
                f"Total Receivables ({date_cols[0]})",
                f"₹{latest_total:,.0f}",
                delta=f"₹{-change:,.0f}"
            )
        
        with col2:
            week_change_pct = ((prev_total - latest_total) / prev_total * 100)
            st.metric(
                "Week-on-Week Change",
                f"{week_change_pct:.2f}%",
                delta=week_change_pct
            )
            
        with col3:
            month_start = df[date_cols[-1]].sum()
            month_change = ((month_start - latest_total) / month_start * 100)
            st.metric(
                "Month-to-Date Change",
                f"{month_change:.2f}%",
                delta=month_change
            )
        
        # Main trend table
        st.markdown("### Ageing-wise Trend Analysis")
        styled_df = style_tsg_trend(df)
        st.dataframe(styled_df, height=400, use_container_width=True)
        
        # Trend Analysis
        st.markdown("### Trend Visualization")
        
        # Prepare data for plotting
        trend_data = df.melt(
            id_vars=['Ageing Category'],
            value_vars=date_cols,
            var_name='Date',
            value_name='Amount'
        )
        
        # Line chart
        fig_line = px.line(
            trend_data,
            x='Date',
            y='Amount',
            color='Ageing Category',
            title="Receivables Trend by Ageing Category"
        )
        fig_line.update_layout(yaxis_title="Amount (₹)")
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Category Analysis
        st.markdown("### Category-wise Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            # Latest distribution pie chart
            fig_pie = px.pie(
                df,
                values=date_cols[0],
                names='Ageing Category',
                title=f"Distribution as of {date_cols[0]}"
            )
            st.plotly_chart(fig_pie)
        
        with col2:
            # Week-on-week changes
            changes_df = pd.DataFrame({
                'Category': df['Ageing Category'],
                'Change': df[date_cols[0]] - df[date_cols[1]]
            })
            fig_changes = px.bar(
                changes_df,
                x='Category',
                y='Change',
                title="Week-on-Week Changes by Category",
                color='Change',
                color_continuous_scale=['green', 'yellow', 'red']
            )
            st.plotly_chart(fig_changes)
        
        # Export Option
        if st.sidebar.button("Export TSG Analysis"):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='TSG Trend', index=False)
            
            st.sidebar.download_button(
                label="📥 Download TSG Report",
                data=buffer.getvalue(),
                file_name=f"tsg_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
    except Exception as e:
        st.error(f"Error in TSG analysis: {str(e)}")
        st.write("Error details:", str(e))

# Define menu structure
DEPARTMENT_REPORTS = {
    "CSD": {
        "Branch Reco Trend": show_collections_dashboard,
        "CSD SDR Trend": show_sdr_dashboard
    },
    "TSG": {
        "TSG Payment Receivables": show_tsg_dashboard
    },
    "ITSS": {
        "ITSS SDR Analysis": show_itss_dashboard
    },
    "Finance": {
        # Add Finance reports here
    }
}

def define_department_structure():
    """Define the department and report structure"""
    return {
        "CSD": {
            "Branch Reco Trend": show_collections_dashboard,
            "CSD SDR Trend": show_sdr_dashboard
        },
        "TSG": {
            "TSG Payment Receivables": show_tsg_dashboard
        },
        "ITSS": {
            "ITSS SDR Analysis": show_itss_dashboard
        },
        "Finance": {
            # Add Finance reports here
        }
    }

def show_department_menu():
    """Display hierarchical department menu"""
    # Department selection
    st.sidebar.title("Select Department")
    
    # Get department structure
    DEPARTMENT_REPORTS = define_department_structure()
    
    # Initialize session state for menu
    if 'selected_department' not in st.session_state:
        st.session_state.selected_department = None
    if 'selected_report' not in st.session_state:
        st.session_state.selected_report = None
    
    # Department selection
    departments = list(DEPARTMENT_REPORTS.keys())
    
    # Create department buttons
    for dept in departments:
        if st.sidebar.button(
            dept,
            key=f"dept_{dept}",
            help=f"View {dept} department reports"
        ):
            st.session_state.selected_department = dept
            st.session_state.selected_report = None
            st.rerun()
    
    # Show reports for selected department
    if st.session_state.selected_department:
        st.sidebar.markdown("---")
        st.sidebar.subheader(f"{st.session_state.selected_department} Reports")
        
        reports = list(DEPARTMENT_REPORTS[st.session_state.selected_department].keys())
        
        for report in reports:
            if st.sidebar.radio(
                "",
                [report],
                key=f"report_{report}",
                index=0 if st.session_state.selected_report == report else None,
                label_visibility="collapsed"
            ):
                st.session_state.selected_report = report
                return DEPARTMENT_REPORTS[st.session_state.selected_department][report]
    
    return None

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
        st.rerun()

if __name__ == "__main__":
    main()