CREATE DATABASE IF NOT EXISTS lunch_management;
USE lunch_management;

-- Users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role ENUM('admin', 'employee', 'chef') NOT NULL DEFAULT 'employee',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Attendance table
CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    date DATE NOT NULL,
    status ENUM('office', 'home', 'leave') NOT NULL,
    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_date (user_id, date)
);

-- Notifications log
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    office_count INT DEFAULT 0,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('sent', 'failed') DEFAULT 'sent'
);

-- Insert default users with bcrypt hashed passwords

-- Admin user (email: admin@company.com, password: admin123)
INSERT INTO users (email, password_hash, name, role) VALUES 
('admin@company.com', '$2b$12$KXppz6mYyyuFKD6tnAVumepc5vOFejSIXTrY.Mp3oyMHd.VOsF8au', 'System Admin', 'admin');

-- Chef user (email: chef@company.com, password: chef123)
INSERT INTO users (email, password_hash, name, role) VALUES 
('vrashabhpatil047@gmail.com', '$2b$12$n1WiyJ3yDymz7LSN6x93Ieu1BTxyyWZ36Vrb5vJYDw3JpNRHKY95S', 'Head Chef', 'chef');

-- Sample employees
INSERT INTO users (email, password_hash, name, role) VALUES 
('john@company.com', '$2b$12$EFQvJdoJQq5JfeMOfsGltuQZgAjBnAazI8cA3kw5UAgSDaITbwQ4S', 'John Doe', 'employee'),
('jane@company.com', '$2b$12$tItSM6v9RI3lKKExjjk8ru.lR4o6S7quLh2t.N9fpzVOgx8KJGKR.', 'Jane Smith', 'employee');


-- Create indexes
CREATE INDEX idx_attendance_date ON attendance(date);
CREATE INDEX idx_attendance_user_date ON attendance(user_id, date);
