import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import io
<<<<<<< HEAD
import streamlit_authenticator as stauth
=======
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

            # Use SSL or STARTTLS based on the port
            socket.setdefaulttimeout(30)  # Set socket timeout to 30 seconds
            context = ssl.create_default_context()

            if self.smtp_config['port'] == 465:
                # Using SSL for port 465
                with smtplib.SMTP_SSL(self.smtp_config['server'], self.smtp_config['port'], context=context) as server:
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
                    for user_email in subscribers['users']:
                        self._send_email(server, user_email, msg)
            else:
                # Use STARTTLS for other ports like 587
                with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
                    server.starttls(context=context)
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
                    for user_email in subscribers['users']:
                        self._send_email(server, user_email, msg)
        
        except Exception as e:
            st.error(f"Error in notification system: {str(e)}")
            
    def _send_email(self, server, user_email, msg):
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
            st.write("Attempting to connect to:", 'mail.rvsolutions.in', "on port:", 587)
            
            # Create SSL context
            context = ssl.create_default_context()
            
            try:
                # First try to create socket connection
                with socket.create_connection(('mail.rvsolutions.in', 587), timeout=10) as sock:
                    st.info("Socket connection successful")
                    
                    # Create SMTP connection using STARTTLS for port 587
                    with smtplib.SMTP('mail.rvsolutions.in', 587) as server:
                        server.starttls(context=context)
                        st.info("SMTP connection established with STARTTLS")
                        
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
>>>>>>> 069f321169cf577030336b0c60b28d34aa93adb7

# Configure page settings
st.set_page_config(
    page_title="Collections & Outstanding Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (for UI appearance)
st.markdown("""
    <style>
    .main {
        padding: 20px;
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

# Streamlit Authentication Setup
usernames = ["admin@rvsolutions.in", "ceo@rvsolutions.in", "manager@rvsolutions.in"]
passwords = ["admin123", "ceo123", "manager123"]
hashed_passwords = stauth.Hasher(passwords).generate()

authenticator = stauth.Authenticate(usernames, usernames, hashed_passwords, 'cookie_name', 'random_key')
name, authentication_status, username = authenticator.login('Login', 'main')

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
        fig.add_trace(go.Scatter(x=branch_trend['Date'], y=branch_trend['Balance'], name=f"{branch} - Balance", mode='lines+markers'))
        fig.add_trace(go.Scatter(x=branch_trend['Date'], y=branch_trend['Pending'], name=f"{branch} - Pending", line=dict(dash='dot')))
    fig.update_layout(title="Balance and Pending Trends", xaxis_title="Date", yaxis_title="Amount (₹)", hovermode='x unified')
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
    trend_data = df.melt(id_vars=['Ageing Category'], value_vars=df.columns[1:], var_name='Date', value_name='Amount')
    fig = px.line(trend_data, x='Date', y='Amount', color='Ageing Category', title="SDR Trends by Ageing Category")
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

    st.metric(f"Total Receivables ({latest_date})", f"₹{latest_total:,.0f}", delta=f"₹{-change:,.0f}")

    # Line Chart
    trend_data = df.melt(id_vars=['Ageing Category'], value_vars=df.columns[1:], var_name='Date', value_name='Amount')
    fig = px.line(trend_data, x='Date', y='Amount', color='Ageing Category', title="Receivables Trend by Ageing Category")
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
    st.metric("High Risk Amount", f"₹{high_risk:.2f} Lakhs", f"{(high_risk/total_outstanding*100 if total_outstanding else 0):.1f}%")

    # Distribution Pie Chart
    dist_data = df[aging_categories].sum()
    fig_pie = px.pie(values=dist_data.values, names=dist_data.index, title="Distribution by Aging Category")
    st.plotly_chart(fig_pie, use_container_width=True)

# Show the Dashboard based on the Selection
def main():
    if authentication_status:
        st.sidebar.title("Department Reports")
        report_type = st.sidebar.radio("Select Report Type", ["Branch Reco Trend", "CSD SDR Trend", "TSG Payment Receivables", "ITSS SDR Analysis"])

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
    elif authentication_status is None:
        st.warning("Please enter your username and password")

if __name__ == "__main__":
    main()