# Collections & Outstanding Dashboard

A Streamlit-based dashboard for monitoring and analyzing collections and outstanding data.

![Dashboard Preview](assets/dashboard_preview.png)

## 🎯 Features

- **Real-time Analytics Dashboard**
  - Collections tracking
  - Outstanding analysis
  - Branch performance metrics
  - Comparative trend analysis

- **Advanced Filtering**
  - Date range selection
  - Branch/Region filters
  - Amount range filters

- **Secure Access**
  - Role-based authentication
  - Multiple user levels (Admin, CEO, Manager)

- **Interactive Visualizations**
  - Trend charts
  - Performance comparisons
  - Branch-wise analytics

## 🚀 Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/collections-dashboard.git
cd collections-dashboard
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the app locally:
```bash
streamlit run app.py
```

## 📁 Project Structure
```
collections-dashboard/
├── app.py                  # Main application file
├── requirements.txt        # Project dependencies
├── config.yaml            # Configuration settings
├── .streamlit/
│   └── config.toml        # Streamlit configuration
├── assets/                # Images and static files
│   ├── logo.png
│   └── dashboard_preview.png
└── README.md             # Project documentation
```

## 🔧 Configuration

1. Create a `.streamlit/config.toml` file:
```toml
[theme]
primaryColor="#2ecc71"
backgroundColor="#ffffff"
secondaryBackgroundColor="#f8f9fa"
textColor="#262730"
font="sans serif"
```

2. Set up authentication in `config.yaml`:
```yaml
credentials:
  usernames:
    admin:
      email: "admin@company.com"
      name: "Admin User"
      password: "xxx"  # Replace with hashed password
```

## 🖥️ Local Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

## 🚀 Deployment

1. Fork this repository

2. Sign up for [Streamlit Cloud](https://streamlit.io/cloud)

3. Deploy from Streamlit Cloud:
   - Connect your GitHub account
   - Select this repository
   - Select app.py as the main file
   - Click "Deploy"

## 🔐 Security

- Passwords are hashed and stored securely
- Authentication required for all pages
- Role-based access control
- Secure session management

## 📊 Data Management

The dashboard expects data in the following format:
```python
{
    'Branch Name': ['Kota', 'Guwahati', ...],
    'Invoice': [1000, 2000, ...],
    'Collection': [800, 1600, ...],
    'Outstanding': [200, 400, ...],
    'Region': ['North', 'East', ...]
}
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Support

For support, email [your-email@domain.com](mailto:your-email@domain.com)