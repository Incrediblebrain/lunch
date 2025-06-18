## 6. Setup Instructions

### Step 1: Install Requirements
```bash
pip install -r requirements.txt
```

### Step 2: Setup MySQL Database
```bash
# Login to MySQL
mysql -u root -p

# Run the database setup script
source database_setup.sql
```

### Step 3: Configure Environment
Create `.env` file with your MySQL credentials:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=lunch_management
```

### Step 4: Run Backend Server
```bash
python backend_server.py
```

### Step 5: Run Frontend
```bash
streamlit run streamlit_app.py
```

## 7. Usage Guide

### Default Login Credentials:
- **Admin:** admin@company.com / admin123
- **Chef:** chef@company.com / chef123  
- **Employee:** john@company.com / admin123

### Features:

#### Employee Features:
- ✅ Mark daily attendance before 9:30 AM
- ✅ Choose: Office, Home, or Leave
- ✅ View attendance history and statistics
- ✅ Calendar interface with date selection
- ✅ Automatic tomorrow assignment after cutoff

#### Chef Features:
- ✅ Receive office count at 9:30 AM daily
- ✅ View counts for any specific date
- ✅ Weekly attendance trends
- ✅ Email notifications (if configured)

#### Admin Features:
- ✅ Complete attendance reports and analytics
- ✅ User management and role assignment
- ✅ Add new users to the system
- ✅ View attendance trends and statistics

### Automated Features:
- ✅ Daily email notifications to chef at 9:30 AM
- ✅ Weekend exclusion (no notifications on Sat/Sun)
- ✅ Automatic cutoff time enforcement
- ✅ Database logging of all notifications

## 8. API Endpoints

- `POST /login` - User authentication
- `POST /register` - Register new user
- `POST /attendance` - Mark attendance
- `GET /attendance/{user_id}` - Get user attendance
- `GET /chef/daily-count` - Get office count for chef
- `GET /admin/reports` - Admin reports and analytics
- `GET /admin/users` - Get all users

## 9. Database Schema

### Tables:
- **users** - User accounts with roles
- **attendance** - Daily attendance records
- **notifications** - Email notification logs

### Relationships:
- attendance.user_id → users.id (Foreign Key)
- Unique constraint on (user_id, date) for attendance

## 10. Scheduling

The system uses APScheduler to automatically send notifications:
- **Trigger:** Every weekday at 9:30 AM
- **Action:** Send email to chef with office count
- **Exclusions:** Weekends (Saturday & Sunday)

The system is now complete and ready to use! 🚀