from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, time, timedelta
from passlib.context import CryptContext
import mysql.connector
from mysql.connector import Error
import os
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI app
app = FastAPI(title="Lunch Management System", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'lunch_management'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
        )
        return connection
    except Error as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# Pydantic models
class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str

class AttendanceRequest(BaseModel):
    date: str
    status: str

class AttendanceResponse(BaseModel):
    id: int
    date: str
    status: str
    marked_at: str

# Authentication helpers
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# Database operations
def get_user_by_email(email: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s AND is_active = 1", (email,))
        user = cursor.fetchone()
        return user
    finally:
        cursor.close()
        connection.close()

def get_user_by_id(user_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE id = %s AND is_active = 1", (user_id,))
        user = cursor.fetchone()
        return user
    finally:
        cursor.close()
        connection.close()

def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return False
    if not verify_password(password, user['password_hash']):
        return False
    return user

def is_weekend(check_date):
    """Check if date is weekend (Saturday=5, Sunday=6)"""
    return check_date.weekday() >= 5

def is_after_cutoff_time():
    """Check if current time is after 9:30 AM"""
    now = datetime.now()
    cutoff = now.replace(hour=21, minute=30, second=0, microsecond=0)
    return now > cutoff

# API Routes

@app.post("/login")
async def login(user_data: UserLogin):
    user = authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "message": "Login successful",
        "user": {
            "id": user['id'],
            "email": user['email'],
            "name": user['name'],
            "role": user['role']
        }
    }

@app.post("/register")
async def register(email: str = Form(...), password: str = Form(...), name: str = Form(...), role: str = Form("employee")):
    # Check if user exists
    existing_user = get_user_by_email(email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = get_password_hash(password)
    
    # Insert user
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, role) VALUES (%s, %s, %s, %s)",
            (email, hashed_password, name, role)
        )
        connection.commit()
        user_id = cursor.lastrowid
        
        return {
            "message": "User registered successfully",
            "user_id": user_id
        }
    except Error as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    finally:
        cursor.close()
        connection.close()

@app.post("/attendance")
async def mark_attendance(attendance: AttendanceRequest, user_id: int):
    # Parse date
    try:
        attendance_date = datetime.strptime(attendance.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Check if weekend
    if is_weekend(attendance_date):
        raise HTTPException(status_code=400, detail="Cannot mark attendance on weekends")
    
    # Check cutoff time for today's attendance
    today = date.today()
    if attendance_date == today and is_after_cutoff_time():
        # Set for tomorrow
        attendance_date = today + timedelta(days=1)
        message = "Cutoff time passed. Attendance marked for tomorrow."
    else:
        message = "Attendance marked successfully."
    
    # Insert/Update attendance
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """INSERT INTO attendance (user_id, date, status) VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE status = %s, marked_at = CURRENT_TIMESTAMP""",
            (user_id, attendance_date, attendance.status, attendance.status)
        )
        connection.commit()
        
        return {"message": message, "date": str(attendance_date)}
    except Error as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to mark attendance: {str(e)}")
    finally:
        cursor.close()
        connection.close()

@app.get("/attendance/{user_id}")
async def get_user_attendance(user_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        query = "SELECT * FROM attendance WHERE user_id = %s"
        params = [user_id]
        
        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)
        
        query += " ORDER BY date DESC"
        
        cursor.execute(query, params)
        attendance_records = cursor.fetchall()
        
        return {"attendance": attendance_records}
    finally:
        cursor.close()
        connection.close()

@app.get("/chef/daily-count")
async def get_daily_office_count(date_str: Optional[str] = None):
    if date_str:
        try:
            check_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        check_date = date.today()
    
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) as office_count FROM attendance WHERE date = %s AND status = 'office'",
            (check_date,)
        )
        result = cursor.fetchone()
        office_count = result[0] if result else 0
        
        return {
            "date": str(check_date),
            "office_count": office_count,
            "message": f"{office_count} employees will be in office today"
        }
    finally:
        cursor.close()
        connection.close()

@app.get("/admin/reports")
async def get_admin_reports(start_date: Optional[str] = None, end_date: Optional[str] = None):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Get date range
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = date.today().strftime("%Y-%m-%d")
        
        # Total attendance by status
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM attendance 
            WHERE date BETWEEN %s AND %s 
            GROUP BY status
        """, (start_date, end_date))
        status_counts = cursor.fetchall()
        
        # Daily attendance counts
        cursor.execute("""
            SELECT date, status, COUNT(*) as count 
            FROM attendance 
            WHERE date BETWEEN %s AND %s 
            GROUP BY date, status 
            ORDER BY date DESC
        """, (start_date, end_date))
        daily_counts = cursor.fetchall()
        
        # User attendance summary
        cursor.execute("""
            SELECT u.name, u.email, 
                   COUNT(a.id) as total_days,
                   SUM(CASE WHEN a.status = 'office' THEN 1 ELSE 0 END) as office_days,
                   SUM(CASE WHEN a.status = 'home' THEN 1 ELSE 0 END) as home_days,
                   SUM(CASE WHEN a.status = 'leave' THEN 1 ELSE 0 END) as leave_days
            FROM users u
            LEFT JOIN attendance a ON u.id = a.user_id AND a.date BETWEEN %s AND %s
            WHERE u.role = 'employee'
            GROUP BY u.id
        """, (start_date, end_date))
        user_summary = cursor.fetchall()
        
        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "status_counts": status_counts,
            "daily_counts": daily_counts,
            "user_summary": user_summary
        }
    finally:
        cursor.close()
        connection.close()

@app.get("/admin/users")
async def get_all_users():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, email, name, role, is_active, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        return {"users": users}
    finally:
        cursor.close()
        connection.close()

def send_email_notification(recipient_email: str, subject: str, body: str) -> bool:
    """Send email using Brevo (Sendinblue) API"""
    try:
        api_key = os.getenv("BREVO_API_KEY")
        if not api_key:
            logger.warning("Brevo API key not configured")
            return False

        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json"
            },
            json={
                "sender": {"name": "Lunch Manager", "email": "vrashabhpatil048@gmail.com"},
                "to": [{"email": recipient_email}],
                "subject": subject,
                "textContent": body
            }
        )

        if response.status_code in [200, 201, 202]:
            logger.info(f"Email sent to {recipient_email}")
            return True
        else:
            logger.error(f"Failed to send email to {recipient_email}: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error in Brevo email send: {e}")
        return False

# --- Send Notification to All Chefs ---
def send_chef_notification():
    """Send daily office count to all active chefs"""
    today = date.today()

    if is_weekend(today):
        logger.info("Skipping chef notification - weekend")
        return

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) as count FROM attendance WHERE date = %s AND status = 'office'",
            (today,)
        )
        result = cursor.fetchone()
        office_count = result[0] if result else 0

        cursor.execute("SELECT email FROM users WHERE role = 'chef' AND is_active = 1")
        chef_results = cursor.fetchall()

        if chef_results:
            subject = f"Daily Lunch Count - {today.strftime('%B %d, %Y')}"
            body_template = f"""
Dear Chef,

Today's office attendance count: {office_count} employees

Please prepare lunch accordingly.

Date: {today.strftime('%B %d, %Y')}
Time: {datetime.now().strftime('%I:%M %p')}

Best regards,
Lunch Management System
"""

            for chef in chef_results:
                chef_email = chef[0]
                email_sent = send_email_notification(chef_email, subject, body_template)

                # Log each notification
                cursor.execute(
                    "INSERT INTO notifications (type, recipient_email, content, office_count, status) VALUES (%s, %s, %s, %s, %s)",
                    ("daily_count", chef_email, body_template, office_count, "sent" if email_sent else "failed")
                )

            connection.commit()
            logger.info(f"Chef notifications sent to {len(chef_results)} chef(s)")

        else:
            logger.warning("No active chefs found for notification")

    except Exception as e:
        logger.error(f"Failed to send chef notifications: {e}")
    finally:
        cursor.close()
        connection.close()

# Scheduler setup
scheduler = BackgroundScheduler()

def start_scheduler():
    """Start the background scheduler"""
    # Schedule chef notification at 9:30 AM every weekday
    scheduler.add_job(
        send_chef_notification,
        CronTrigger(hour=18, minute=57, day_of_week='mon-fri'),
        id='chef_notification',
        name='Daily Chef Notification'
    )
    scheduler.start()
    logger.info("Scheduler started - Chef notifications scheduled for 9:30 AM weekdays")

def stop_scheduler():
    """Stop the background scheduler"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")

# Start scheduler when app starts
@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()

@app.get("/")
async def root():
    return {
        "message": "Lunch Management System API",
        "version": "1.0.0",
        "status": "active"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
