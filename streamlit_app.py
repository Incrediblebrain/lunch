import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import json

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="Lunch Management System",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if 'user' not in st.session_state:
    st.session_state.user = None
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Helper functions
def make_request(method, endpoint, data=None, params=None):
    """Make API request"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: {str(e)}")
        return None

def login_user(email, password):
    """Login user"""
    data = {"email": email, "password": password}
    result = make_request("POST", "/login", data=data)
    if result:
        st.session_state.user = result['user']
        st.session_state.logged_in = True
        return True
    return False

def logout_user():
    """Logout user"""
    st.session_state.user = None
    st.session_state.logged_in = False
    st.rerun()

# Authentication
def show_login():
    """Show login form"""
    st.title("🍽️ Lunch Management System")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("Login")
        
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        if st.button("Login", use_container_width=True):
            if email and password:
                if login_user(email, password):
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
            else:
                st.error("Please enter both email and password")
        
        st.markdown("---")
        st.markdown("**Default Accounts:**")
        st.markdown("- Admin: admin@company.com / admin123")
        st.markdown("- Chef: chef@company.com / chef123")
        st.markdown("- Employee: john@company.com / admin123")

# Employee Dashboard
def show_employee_dashboard():
    """Employee dashboard"""
    st.title(f"👋 Welcome, {st.session_state.user['name']}")
    st.markdown("---")
    
    # Today's status
    today = date.today()
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📅 Mark Today's Attendance")
        
        # Check if weekend
        if today.weekday() >= 5:  # Saturday or Sunday
            st.warning("⚠️ Weekend detected. Attendance marking is disabled on weekends.")
        else:
            status = st.selectbox(
                "Select your status for today:",
                ["office", "home", "leave"],
                format_func=lambda x: {
                    "office": "🏢 Working from Office",
                    "home": "🏠 Working from Home", 
                    "leave": "🚫 On Leave"
                }[x]
            )
            
            if st.button("Mark Attendance", use_container_width=True):
                data = {
                    "date": today.strftime("%Y-%m-%d"),
                    "status": status
                }
                result = make_request("POST", f"/attendance?user_id={st.session_state.user['id']}", data=data)
                if result:
                    st.success(f"✅ {result['message']}")
                    st.rerun()
    
    with col2:
        # Current time and status
        now = datetime.now()
        st.subheader("🕘 Current Time")
        st.write(f"**{now.strftime('%I:%M %p')}**")
        st.write(f"Date: {today.strftime('%B %d, %Y')}")
        
        # Cutoff warning
        cutoff_time = now.replace(hour=18, minute=40, second=0, microsecond=0)
        if now > cutoff_time:
            st.warning("⏰ After 9:30 AM cutoff")
        else:
            remaining = cutoff_time - now
            minutes_left = int(remaining.total_seconds() / 60)
            st.info(f"⏱️ {minutes_left} minutes until cutoff")
    
    st.markdown("---")
    
    # Calendar view
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Your Attendance History")
        
        # Get attendance data
        end_date = today
        start_date = today - timedelta(days=30)
        
        attendance_data = make_request(
            "GET", 
            f"/attendance/{st.session_state.user['id']}", 
            params={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }
        )
        
        if attendance_data and attendance_data['attendance']:
            df = pd.DataFrame(attendance_data['attendance'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)
            
            # Display recent attendance
            st.dataframe(
                df[['date', 'status', 'marked_at']].head(10),
                use_container_width=True,
                column_config={
                    "date": "Date",
                    "status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["office", "home", "leave"]
                    ),
                    "marked_at": "Marked At"
                }
            )
        else:
            st.info("No attendance records found.")
    
    with col2:
        st.subheader("📈 Your Attendance Summary")
        
        if 'df' in locals() and not df.empty:
            # Status counts
            status_counts = df['status'].value_counts()
            
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Attendance Distribution (Last 30 Days)",
                color_discrete_map={
                    'office': '#1f77b4',
                    'home': '#ff7f0e', 
                    'leave': '#d62728'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Statistics
            total_days = len(df)
            office_days = len(df[df['status'] == 'office'])
            st.metric("Office Days", office_days, f"out of {total_days}")
        else:
            st.info("No data to display statistics.")

# Chef Dashboard
def show_chef_dashboard():
    """Chef dashboard"""
    st.title(f"👨‍🍳 Chef Dashboard - {st.session_state.user['name']}")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🍽️ Today's Lunch Count")
        
        # Get today's count
        today_data = make_request("GET", "/chef/daily-count")
        
        if today_data:
            count = today_data['office_count']
            st.metric(
                "Employees in Office Today",
                count,
                help="Number of employees who marked 'Working from Office' for today"
            )
            
            if count > 0:
                st.success(f"✅ Prepare lunch for {count} employees")
            else:
                st.info("ℹ️ No employees in office today")
        
        # Date selector for other dates
        st.subheader("📅 Check Other Dates")
        selected_date = st.date_input("Select Date", value=date.today())
        
        if st.button("Get Count for Selected Date"):
            date_data = make_request("GET", f"/chef/daily-count?date_str={selected_date}")
            if date_data:
                st.info(f"Office count for {selected_date}: **{date_data['office_count']}** employees")
    
    with col2:
        st.subheader("📈 Weekly Trend")
        
        # Get data for last 7 days
        dates = []
        counts = []
        
        for i in range(7):
            check_date = date.today() - timedelta(days=i)
            if check_date.weekday() < 5:  # Weekdays only
                date_data = make_request("GET", f"/chef/daily-count?date_str={check_date}")
                if date_data:
                    dates.append(check_date.strftime("%m/%d"))
                    counts.append(date_data['office_count'])
        
        if dates and counts:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates[::-1], 
                y=counts[::-1],
                mode='lines+markers',
                name='Office Count',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8)
            ))
            fig.update_layout(
                title="Office Attendance - Last 7 Days",
                xaxis_title="Date",
                yaxis_title="Employee Count",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

# Admin Dashboard
def show_admin_dashboard():
    """Admin dashboard"""
    st.title(f"👨‍💼 Admin Dashboard - {st.session_state.user['name']}")
    st.markdown("---")
    
    # Tabs for different admin functions
    tab1, tab2, tab3 = st.tabs(["📊 Reports", "👥 User Management", "📝 Add User"])
    
    with tab1:
        st.subheader("📊 Attendance Reports")
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", value=date.today())
        
        if st.button("Generate Report"):
            # Get admin reports
            reports = make_request("GET", "/admin/reports", params={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            })
            
            if reports:
                # Status overview
                col1, col2, col3 = st.columns(3)
                
                status_counts = {item['status']: item['count'] for item in reports['status_counts']}
                
                with col1:
                    st.metric("🏢 Office Days", status_counts.get('office', 0))
                with col2:
                    st.metric("🏠 Home Days", status_counts.get('home', 0))
                with col3:
                    st.metric("🚫 Leave Days", status_counts.get('leave', 0))
                
                # Charts
                col1, col2 = st.columns(2)
                
                with col1:
                    # Status distribution pie chart
                    if reports['status_counts']:
                        fig = px.pie(
                            values=[item['count'] for item in reports['status_counts']],
                            names=[item['status'].title() for item in reports['status_counts']],
                            title="Attendance Distribution"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Daily trend
                    if reports['daily_counts']:
                        df_daily = pd.DataFrame(reports['daily_counts'])
                        df_daily['date'] = pd.to_datetime(df_daily['date'])
                        
                        fig = px.line(
                            df_daily, 
                            x='date', 
                            y='count', 
                            color='status',
                            title="Daily Attendance Trend"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                # User summary table
                st.subheader("👥 Employee Summary")
                if reports['user_summary']:
                    df_users = pd.DataFrame(reports['user_summary'])
                    st.dataframe(df_users, use_container_width=True)
    
    with tab2:
        st.subheader("👥 User Management")
        
        # Get all users
        users_data = make_request("GET", "/admin/users")
        
        if users_data and users_data['users']:
            df_users = pd.DataFrame(users_data['users'])
            df_users['created_at'] = pd.to_datetime(df_users['created_at'])
            
            st.dataframe(
                df_users[['name', 'email', 'role', 'is_active', 'created_at']],
                use_container_width=True,
                column_config={
                    "name": "Name",
                    "email": "Email",
                    "role": "Role",
                    "is_active": st.column_config.CheckboxColumn("Active"),
                    "created_at": "Created At"
                }
            )
        else:
            st.info("No users found.")
    
    with tab3:
        st.subheader("➕ Add New User")
        
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Full Name")
                new_email = st.text_input("Email")
            
            with col2:
                new_password = st.text_input("Password", type="password")
                new_role = st.selectbox("Role", ["employee", "chef", "admin"])
            
            submitted = st.form_submit_button("Add User")
            
            if submitted:
                if new_name and new_email and new_password:
                    # Make API call to register user
                    register_data = {
                        "email": new_email,
                        "password": new_password,
                        "name": new_name,
                        "role": new_role
                    }
                    
                    # Using form data for registration
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/register",
                            data=register_data
                        )
                        
                        if response.status_code == 200:
                            st.success(f"✅ User {new_name} added successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to add user: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                else:
                    st.error("Please fill all fields")

# Main app logic
def main():
    """Main application"""
    
    # Sidebar
    with st.sidebar:
        st.title("🍽️ Lunch Management")
        
        if st.session_state.logged_in:
            st.success(f"Logged in as: {st.session_state.user['name']}")
            st.write(f"Role: {st.session_state.user['role'].title()}")
            
            if st.button("Logout", use_container_width=True):
                logout_user()
        else:
            st.info("Please login to continue")
    
    # Main content
    if not st.session_state.logged_in:
        show_login()
    else:
        user_role = st.session_state.user['role']
        
        if user_role == 'employee':
            show_employee_dashboard()
        elif user_role == 'chef':
            show_chef_dashboard()
        elif user_role == 'admin':
            show_admin_dashboard()
        else:
            st.error("Invalid user role")

if __name__ == "__main__":
    main()
