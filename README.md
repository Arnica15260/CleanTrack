# CleanTrack

## Overview

CleanTrack is a web-based waste management platform designed to streamline the process of waste collection, complaint management, and service monitoring. The system enables citizens to report waste-related issues, track complaint status, and communicate with municipal authorities through a centralized platform.

The project aims to improve urban cleanliness by providing an efficient digital solution for waste management while enhancing communication between citizens and service providers.

---

## Features

- User Registration and Authentication
- Complaint Submission
- Waste Collection Request
- Complaint Status Tracking
- Admin Dashboard
- User Profile Management
- Secure Database Management
- Responsive User Interface

---

## Objectives

- Digitize the waste management process.
- Simplify complaint submission and tracking.
- Improve communication between citizens and municipal authorities.
- Enhance transparency in waste collection services.
- Reduce response time for waste-related complaints.

---

## Technologies Used

### Frontend

- HTML5
- CSS3
- Bootstrap
- JavaScript

### Backend

- PHP

### Database

- MySQL

### Development Tools

- Visual Studio Code
- XAMPP
- Git
- GitHub

---

## System Architecture

```
                    +------------------+
                    |      Users       |
                    +--------+---------+
                             |
                             v
                   Web User Interface
                             |
                             v
                    PHP Application
                             |
        ----------------------------------------
        |                  |                   |
        v                  v                   v
 Authentication      Complaint Module     User Module
        |                  |                   |
        ----------------------------------------
                             |
                             v
                        MySQL Database
                             |
                             v
                      Admin Dashboard
```

---

## Project Structure

```
CleanTrack/
│
├── assets/
│   ├── css/
│   ├── js/
│   └── images/
│
├── database/
│   └── cleantrack.sql
│
├── includes/
│   ├── config.php
│   ├── header.php
│   ├── footer.php
│   └── functions.php
│
├── admin/
│   ├── dashboard.php
│   ├── complaints.php
│   ├── users.php
│   └── login.php
│
├── user/
│   ├── login.php
│   ├── register.php
│   ├── profile.php
│   ├── submit_complaint.php
│   └── complaint_history.php
│
├── index.php
├── README.md
└── LICENSE
```

---

## Working Process

### Step 1

Users create an account and log in to the system.

### Step 2

Users submit waste-related complaints or collection requests.

### Step 3

The complaint information is securely stored in the database.

### Step 4

Administrators review submitted complaints through the dashboard.

### Step 5

The complaint status is updated after verification and assignment.

### Step 6

Users can monitor the progress of their complaints through their dashboard.

### Step 7

The complaint is marked as resolved after successful completion of the service.

---

## Installation

1. Clone the repository.

```bash
git clone https://github.com/Arnica15260/CleanTrack.git
```

2. Move the project folder into the XAMPP `htdocs` directory.

3. Start Apache and MySQL from the XAMPP Control Panel.

4. Import the database into phpMyAdmin.

5. Configure the database connection in `config.php`.

6. Open your browser and visit:

```
http://localhost/CleanTrack
```

---

## User Roles

### User

- Register an account
- Log in securely
- Submit complaints
- Track complaint status
- Manage profile

### Administrator

- Manage user accounts
- Review complaints
- Update complaint status
- Monitor overall system activities

---

## Database

The system uses MySQL as the relational database management system.

Main entities include:

- Users
- Complaints
- Waste Collection Requests
- Administrators
- Complaint Status

---

## Applications

- Smart City Services
- Municipal Waste Management
- Public Complaint Management
- Urban Sanitation Monitoring
- Community Service Platforms

---

## Future Improvements

- Mobile application support
- Real-time notifications
- GIS-based waste location tracking
- AI-assisted complaint categorization
- QR code integration
- Email and SMS notifications
- Analytics dashboard
- Cloud deployment

---

## Learning Outcomes

This project strengthened practical knowledge in:

- Full-Stack Web Development
- Database Design
- Authentication and Authorization
- CRUD Operations
- Responsive Web Design
- Software Engineering Principles
- Version Control using Git and GitHub

---

## License

This project was developed for academic purposes as part of the Software Engineering course at the University of Asia Pacific.
