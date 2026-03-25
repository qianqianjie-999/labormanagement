# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

劳动用工管理系统 (Labor Management System) - A Flask-based web application for managing labor applications and approvals in construction projects.

## Architecture

- **Framework**: Flask 2.3.3 with application factory pattern (`create_app()`)
- **Database**: MySQL/MariaDB via SQLAlchemy 2.0 + Flask-SQLAlchemy
- **Authentication**: Flask-Login with role-based access (admin/user)
- **Production Deployment**: Apache + mod_wsgi on CentOS Stream
- **Key Components**:
  - `app.py` - Main application with all routes and business logic
  - `models.py` - SQLAlchemy models (User, WorkItem, ApplicationItem, LaborApplication)
  - `config.py` - Configuration class with database URI and upload settings
  - `init_tables.py` - Database initialization script for production

## Commands

### Development
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Run development server
python app.py
# Or with Flask CLI
flask run

# Initialize/reinitialize database (development only)
python init_tables.py
```

### Production (CentOS Stream with Apache + mod_wsgi)
```bash
# Project location: /var/www/html/labormanagement
# Virtual environment: /var/www/html/labormanagement/venv

# Initialize production database (run as apache user)
sudo -u apache /var/www/html/labormanagement/venv/bin/python /var/www/html/labormanagement/init_tables.py

# Restart application
sudo systemctl restart httpd

# View logs
sudo tail -f /var/log/httpd/labormanagement_error.log
sudo tail -f /var/log/httpd/labormanagement_access.log
```

## Configuration

### Database
- Production URI uses IPv6 localhost `[::1]` - ensure MySQL user has grants for both `@'localhost'` and `@'::1'`
- Alternative: use `127.0.0.1` in config to avoid IPv6 issues
- Default database: `labor_application_db`
- Default user: `labor_app_user`

### Reference Coefficient
- Stored in `logs/config.json` (not tracked in git)
- Controls labor calculation baseline (default: 0.85)
- Admin users can update via UI

## Key Business Logic

### Labor Calculation
```
required_labor = quantity * work_item.labor_coefficient
```

### Season Coefficients (applied to totals)
- Spring (Mar-May): 1.0
- Summer (Jun-Aug): 1.01
- Autumn (Sep-Nov): 1.0
- Winter (Dec-Feb): 1.02

### User Roles
- **Admin**: Full access, can see labor coefficients, approve/reject applications
- **User**: Can create/modify own applications, coefficients hidden (shown as `***`)

### Application States
- `pending` → `approved` or `rejected`
- Once `approved`, applications cannot be modified
- Modifying a pending application resets status to `pending`

## Data Models

- **User**: Authentication with password hashing, role flag (`is_admin`)
- **WorkItem**: Master data for labor items (code, name, coefficient, unit, category)
- **ApplicationItem**: Join table with snapshot of WorkItem data at application time
- **LaborApplication**: Main application entity with department, project info, approval workflow

## Production Notes

### Common Issues
1. **Database "Access denied" for `::1`**: MySQL treats IPv6 localhost separately from IPv4
2. **Missing tables in production**: Run `init_tables.py` as `apache` user with production venv
3. **ModuleNotFoundError**: Verify Apache `WSGIDaemonProcess` points to correct venv path

### File Permissions
```bash
sudo chown -R apache:apache /var/www/html/labormanagement
```

### SELinux
```bash
sudo setsebool -P httpd_can_network_connect 1
```

### Firewall
```bash
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```
