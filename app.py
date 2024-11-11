import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import io
import socket
import toml
import ssl
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import os

class DashboardNotifier:
    def __init__(self, smtp_config):
        """Initialize the notifier with SMTP configuration"""
        if not smtp_config:
            raise ValueError("SMTP configuration cannot be empty.")
        self.smtp_config = smtp_config
        self.report_state_file = 'report_states.json'
        self.subscriber_file = 'subscribers.json'
        
    def load_report_states(self):
        """Load the last known state of reports"""
        if os.path.exists(self.report_state_file):
            with open(self.report_state_file, 'r') as f:
                return json.load(f)
        return {}
        
    def save_report_states(self, states):
        """Save the current state of reports"""
        with open(self.report_state_file, 'w') as f:
            json.dump(states, f)
            
    def load_subscribers(self):
        """Load the list of subscribers"""
        if os.path.exists(self.subscriber_file):
            with open(self.subscriber_file, 'r') as f:
                return json.load(f)
        return {'users': []}
        
    def save_subscribers(self, subscribers):
        """Save the list of subscribers"""
        with open(self.subscriber_file, 'w') as f:
            json.dump(subscribers, f)
            
    def add_subscriber(self, email):
        """Add a new subscriber"""
        subscribers = self.load_subscribers()
        if email not in subscribers['users']:
            subscribers['users'].append(email)
            self.save_subscribers(subscribers)
            return True
        return False
        
    def remove_subscriber(self, email):
        """Remove a subscriber"""
        subscribers = self.load_subscribers()
        if email in subscribers['users']:
            subscribers['users'].remove(email)
            self.save_subscribers(subscribers)
            return True
        return False

    def check_report_updates(self, current_reports):
        """Check for updates in reports and send notifications"""
        previous_states = self.load_report_states()
        updates = []
        
        for report_name, report_info in current_reports.items():
            if report_name not in previous_states:
                # New report
                updates.append({
                    'report': report_name,
                    'type': 'new',
                    'date': report_info['last_updated']
                })
            elif report_info['last_updated'] != previous_states[report_name]['last_updated']:
                # Updated report
                updates.append({
                    'report': report_name,
                    'type': 'update',
                    'date': report_info['last_updated']
                })
        
        if updates:
            self.send_update_notifications(updates)
            self.save_report_states(current_reports)
            
        return updates

    def send_update_notifications(self, updates):
        """Send email notifications for updates (updated to match the successful simple script)"""
        try:
            subscribers = self.load_subscribers()
            
            if not subscribers['users']:
                st.warning("No subscribers found. Add subscribers first.")
                return

            # Create email content
            subject = "Dashboard Report Updates"
            body = self._create_email_body(updates)

            # Set up the email message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from_email']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))

            # Use SSL to connect, as done in the working test script
            context = ssl.create_default_context()

            # Send emails using SMTP_SSL
            try:
                with smtplib.SMTP_SSL(self.smtp_config['server'], self.smtp_config['port'], context=context) as server:
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
                    
                    for user_email in subscribers['users']:
                        try:
                            msg['To'] = user_email
                            server.sendmail(
                                self.smtp_config['from_email'],
                                user_email,
                                msg.as_string()
                            )
                            st.success(f"✉️ Notification sent to {user_email}")
                        except Exception as e:
                            st.error(f"Failed to send email to {user_email}: {str(e)}")
            except Exception as e:
                st.error(f"Failed to connect to SMTP server: {str(e)}")
                        
        except Exception as e:
            st.error(f"Error in notification system: {str(e)}")
            
    def _create_email_body(self, updates):
        """Create HTML email body for updates"""
        html = """
        <html>
            <head>
                <style>
                    .container { font-family: Arial, sans-serif; padding: 20px; }
                    .update-item { margin: 10px 0; padding: 10px; border-left: 4px solid #4CAF50; }
                    .new { border-left-color: #2196F3; }
                    .title { font-weight: bold; color: #333; }
                    .date { color: #666; font-size: 0.9em; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Dashboard Report Updates</h2>
        """
        
        for update in updates:
            update_type = "New Report Available" if update['type'] == 'new' else "Report Updated"
            html += f"""
                    <div class="update-item {'new' if update['type'] == 'new' else ''}">
                        <div class="title">{update_type}: {update['report']}</div>
                        <div class="date">Date: {update['date']}</div>
                    </div>
            """
            
        html += """
                    <p>Visit the dashboard to view the latest reports.</p>
                </div>
            </body>
        </html>
        """
        return html

# Functions outside the class
def load_smtp_config():
    """Load SMTP configuration from the TOML file"""
    try:
        # Assuming the `config.toml` file is located in the `.streamlit` directory
        config_path = os.path.join('.streamlit', 'config.toml')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Load the configuration
        config = toml.load(config_path)
        if 'smtp' not in config:
            raise KeyError("The SMTP configuration section `[smtp]` is missing in the config.toml file.")
        
        smtp_config = config['smtp']
        required_keys = ['server', 'port', 'username', 'password', 'from_email']
        for key in required_keys:
            if key not in smtp_config:
                raise KeyError(f"Missing required SMTP configuration key: {key}")

        return smtp_config

    except Exception as e:
        print(f"Error loading SMTP configuration: {e}")
        return None
        
def init_notification_system():
    """Initialize the notification system with SMTP configuration"""
    smtp_config = {
        'server': 'mail.rvsolutions.in',
        'port': 587,
        'username': 'harpinder.singh@rvsolutions.in',
        'password': '@BaljeetKaur529',
        'from_email': 'harpinder.singh@rvsolutions.in',
    }
    return DashboardNotifier(smtp_config)
    
def test_smtp_connection():
    """Test SMTP connection with detailed error handling"""
    with st.spinner('Testing SMTP connection...'):
        try:
            # Print connection details for debugging
            st.write("Attempting to connect to:", 'mail.rvsolutions.in', "on port:", 465)
            
            # Create SSL context
            context = ssl.create_default_context()
            
            try:
                # First try to create socket connection
                with socket.create_connection(('mail.rvsolutions.in', 465), timeout=10) as sock:
                    st.info("Socket connection successful")
                    
                    # Create SMTP connection using SSL context and existing socket
                    with smtplib.SMTP_SSL(host='mail.rvsolutions.in', port=465, context=context) as server:
                        st.info("SMTP connection established")
                        
                        # Try login
                        try:
                            server.login('harpinder.singh@rvsolutions.in', '@BaljeetKaur529')
                            st.success("✅ Login successful!")
                            return True
                        except smtplib.SMTPAuthenticationError:
                            st.error("❌ Authentication failed - Username or password incorrect")
                            return False
                        except Exception as e:
                            st.error(f"❌ Login failed: {str(e)}")
                            return False
                    
            except socket.timeout:
                st.error("❌ Connection timed out - The server took too long to respond")
                return False
            except socket.gaierror:
                st.error("❌ DNS lookup failed - Could not find the mail server")
                return False
            except ConnectionRefusedError:
                st.error("❌ Connection refused - The server actively refused the connection")
                return False
            except Exception as e:
                st.error(f"❌ Connection error: {str(e)}")
                return False
                
        except Exception as e:
            st.error(f"❌ Setup error: {str(e)}")
            return False

def check_file_updates():
    """Check if any report files have been updated"""
    files_to_monitor = {
        "collections_data.xlsx": "Branch Reco Trend",
        "sdr_trend.xlsx": "CSD SDR Trend",
        "tsg_trend.xlsx": "TSG Payment Receivables",
        "itss_tender.xlsx": "ITSS SDR Analysis"
    }
    
    updates = []
    for file_name, report_name in files_to_monitor.items():
        try:
            if os.path.exists(file_name):
                modified_time = os.path.getmtime(file_name)
                updates.extend(update_report_tracking(report_name))
        except Exception as e:
            st.error(f"Error checking {file_name}: {str(e)}")
    return updates

def update_report_tracking(report_name):
    """Track report updates"""
    try:
        notifier = init_notification_system()
        current_reports = notifier.load_report_states()
        
        current_reports[report_name] = {
            'last_updated': datetime.now().isoformat(),
            'type': 'update' if report_name in current_reports else 'new'
        }
        
        updates = notifier.check_report_updates(current_reports)
        return updates
    except Exception as e:
        st.error(f"Error tracking report update: {str(e)}")
        return []

def manage_subscribers():
    """Manage email subscribers"""
    st.subheader("Email Notification Settings")
    
    try:
        notifier = init_notification_system()
        
        # Test SMTP Connection
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🔄 Test SMTP Connection"):
                test_smtp_connection()
        
        # Add subscriber
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        new_email = col1.text_input("Add new subscriber email")
        if col2.button("Add") and new_email:
            if notifier.add_subscriber(new_email):
                st.success(f"Added {new_email} to subscribers")
            else:
                st.info("Email already subscribed")
                
        # Show current subscribers
        subscribers = notifier.load_subscribers()
        if subscribers['users']:
            st.markdown("### Current Subscribers")
            for email in subscribers['users']:
                col1, col2 = st.columns([3, 1])
                col1.write(email)
                if col2.button("Remove", key=f"remove_{email}"):
                    notifier.remove_subscriber(email)
                    st.rerun()
        
        # Add test button
        st.markdown("---")
        if st.button("📧 Send Test Email"):
            test_email_notification()
            
    except Exception as e:
        st.error(f"Error managing subscribers: {str(e)}")

def test_email_notification():
    """Test the email notification system"""
    try:
        with st.spinner('Setting up email test...'):
            notifier = init_notification_system()
            if notifier is None:
                st.error("Failed to initialize the notification system. Check the SMTP configuration.")
                return
            
            # Check if there are subscribers
            subscribers = notifier.load_subscribers()
            if not subscribers['users']:
                st.warning("No subscribers found. Please add at least one subscriber first.")
                return
                
            # Send test email
            test_updates = [{
                'report': 'Test Report',
                'type': 'test',
                'date': datetime.now().isoformat()
            }]
            
            with st.spinner('Sending test email...'):
                try:
                    with smtplib.SMTP_SSL(notifier.smtp_config['server'], notifier.smtp_config['port']) as server:
                        # Try to login
                        server.login(notifier.smtp_config['username'], notifier.smtp_config['password'])
                        notifier.send_update_notifications(test_updates)
                        st.success("✅ Test email sent successfully!")
                except smtplib.SMTPAuthenticationError:
                    st.error("Login failed: Incorrect username or password.")
                except Exception as e:
                    st.error(f"Failed to send email: {str(e)}")
                    
    except Exception as e:
        st.error(f"Error setting up email test: {str(e)}")

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
        
        # Add this at the end of the try block, just before returning df
        update_report_tracking("Branch Reco Trend")
        
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

def show_collections_dashboard():
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
    st.title("Branch Reco Trend")
    
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
            # Get all dates for comparison
            dates = ['03-Nov-24', '27-Oct-24', '20-Oct-24', '12-Oct-24', '06-Oct-24', '30-Sep-24', '21-Sep-24']
            
            # Create comparison DataFrame
            comparison_df = pd.DataFrame()
            comparison_df['Branch Name'] = selected_branches
            
            # Add data for all dates
            for date in dates:
                comparison_df[f'Balance_{date}'] = [
                    filtered_df[filtered_df['Branch Name'] == branch][f'Balance_{date}'].iloc[0]
                    for branch in selected_branches
                ]
                comparison_df[f'Pending_{date}'] = [
                    filtered_df[filtered_df['Branch Name'] == branch][f'Pending_{date}'].iloc[0]
                    for branch in selected_branches
                ]
            
            # Display styled comparison table
            st.markdown("### Weekly Pending Amount Comparison")
            styled_df = style_comparison_df(comparison_df, dates)
            st.dataframe(
                styled_df,
                height=400,
                use_container_width=True
            )
            
            # Add insights about pending amount trends
            st.markdown("### Pending Amount Trends")
            for branch in selected_branches:
                branch_data = comparison_df[comparison_df['Branch Name'] == branch]
                pending_trend = []
                
                # Compare pending amounts across dates
                for i in range(len(dates)-1):
                    current = branch_data[f'Pending_{dates[i]}'].iloc[0]
                    previous = branch_data[f'Pending_{dates[i+1]}'].iloc[0]
                    if current < previous:
                        pending_trend.append(f"Decreased from ₹{previous:,.2f} to ₹{current:,.2f}")
                    elif current > previous:
                        pending_trend.append(f"Increased from ₹{previous:,.2f} to ₹{current:,.2f}")
                
                if pending_trend:
                    st.markdown(f"**{branch}**:")
                    for trend in pending_trend[:3]:  # Show last 3 changes
                        st.markdown(f"- {trend}")
                    st.markdown("---")
            
        except Exception as e:
            st.error(f"Error in comparative analysis: {str(e)}")
            st.write("Error details:", str(e))

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

def load_sdr_data():
    """Load CSD SDR Trend data"""
    try:
        df = pd.read_excel("sdr_trend.xlsx")
        # Convert amount columns to numeric
        for col in df.columns:
            if col not in ['Ageing Category']:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        st.sidebar.write("SDR Data Columns:", list(df.columns))
        # Add this at the end of the try block, just before returning df
        update_report_tracking("CSD SDR Trend")
        
        return df
    except Exception as e:
        st.error(f"Error loading SDR data: {str(e)}")
        return None

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
    """Display SDR Trend Analysis"""
    st.title("CSD SDR Trend Analysis")
    
    # Load data
    df = load_sdr_data()
    if df is None:
        st.error("Unable to load SDR data. Please check the data file.")
        return
        
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

def load_tsg_data():
    """Load TSG Payment Receivables Trend data"""
    try:
        df = pd.read_excel("tsg_trend.xlsx")
        
        # Convert amounts from string (with commas) to numeric
        for col in df.columns:
            if col != 'Ageing Category':
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        # Add this at the end of the try block, just before returning df
        update_report_tracking("TSG Payment Receivables")
        
        return df
    except Exception as e:
        st.error(f"Error loading TSG data: {str(e)}")
        return None

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
    """Display TSG Payment Receivables Trend Analysis"""
    st.title("TSG Payment Receivables Trend Analysis")
    
    # Load data
    df = load_tsg_data()
    if df is None:
        return
        
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

def show_dashboard():
    """Main dashboard selector"""
    # Report Selection
    report_type = st.sidebar.radio(
        "Select Report Type",
        ["Branch Reco Trend", "CSD SDR Trend"]
    )
    
    if report_type == "Branch Reco Trend":
        show_collections_dashboard()  # Your existing dashboard function
    else:
        show_sdr_dashboard()

def load_itss_data():
    """Load ITSS Tender data"""
    try:
        # Read the Excel file
        df = pd.read_excel(
            "itss_tender.xlsx",
            parse_dates=['Date']
        )
        
        # Define aging categories
        aging_categories = [
            '61-90', '91-120', '121-180', '181-360',
            '361-720', 'More than 2 Yr'
        ]
        
        # Convert amount columns to numeric
        for col in aging_categories:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Add this at the end of the try block, just before returning df
        update_report_tracking("ITSS SDR Analysis")
        
        return df
    except Exception as e:
        st.error(f"Error loading ITSS data: {str(e)}")
        return None

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
    """Display ITSS Tender Analysis Dashboard"""
    st.title("ITSS SDR Aging Analysis")
    
    # Load data
    df = load_itss_data()
    if df is None:
        return
    
    try:
        # Define aging categories
        aging_categories = [
            '61-90', '91-120', '121-180', '181-360',
            '361-720', 'More than 2 Yr'
        ]
        
        # Date selection
        dates = sorted(df['Date'].unique(), reverse=True)
        selected_date = st.selectbox(
            "Select Date for Analysis",
            dates,
            format_func=lambda x: x.strftime('%Y-%m-%d')
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
    # Initialize session state for email management if not exists
    if 'show_email' not in st.session_state:
        st.session_state.show_email = False
    
    # Department selection
    st.sidebar.title("Select Department")
    
    # Add email management button for admin right at the top
    if st.session_state.username == "admin":
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            email_btn = st.button("📧 Manage Email Notifications", type="primary", key="email_btn")
            if email_btn:
                st.session_state.show_email = not st.session_state.show_email
        
        # Show/hide email management section
        if st.session_state.show_email:
            st.sidebar.markdown("### Email Notification Settings")
            manage_subscribers()
            st.sidebar.markdown("---")  # Add divider after email section
    
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

def show_dashboard():
    """Main dashboard selector"""
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
    else:
        show_itss_dashboard()

def main():
    if not check_password():
        return
    
    # Check for file updates
    updates = check_file_updates()
    if updates:
        st.info(f"Reports updated: {', '.join([u['report'] for u in updates])}")
    
    # Show department menu and selected report
    selected_report_func = show_department_menu()
    
    if selected_report_func:
        selected_report_func()
    else:
        st.title("Welcome to Department Reports Dashboard")
        st.markdown("""
            ### Please select a department from the sidebar
            
            Available Departments and Reports:
            - **CSD**: Branch Reconciliation and SDR Trends
            - **TSG**: Payment Receivables Analysis
            - **ITSS**: SDR Analysis
            - **Finance**: Financial Reports
            
            Click on a department to view available reports.
        """)
    
    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", type="secondary"):
        st.session_state.authenticated = False
        st.session_state.selected_department = None
        st.session_state.selected_report = None
        st.session_state.show_email = False  # Reset email management state
        st.rerun()

if __name__ == "__main__":
    main()