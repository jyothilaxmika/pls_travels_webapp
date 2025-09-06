# Overview

PLS TRAVELS is a comprehensive multi-city driver and fleet management system built for transport companies. The system provides role-based access control with three user types: Admin (full system control), Manager (branch-specific operations), and Driver (mobile-first duty management portal). The application handles driver onboarding, vehicle management, duty tracking with flexible compensation schemes, earnings calculation, and comprehensive reporting across multiple city branches.

# Recent Changes

## September 6, 2025
- **Database Migration**: Successfully migrated from SQLite to PostgreSQL using Neon managed database service
- **Approval Flow Modification**: Updated driver approval workflow to allow PENDING status drivers to access duty management features
  - Modified `driver_routes.py` to allow both ACTIVE and PENDING status drivers
  - Updated duty management template to only restrict rejected/suspended/terminated drivers
  - Fixed hybrid property issues with `start_time` and `end_time` attributes in models

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **Framework**: Flask with Blueprint pattern for modular route organization
- **Application Factory**: Uses `create_app()` pattern for flexible configuration and testing
- **Database**: SQLAlchemy ORM with support for SQLite (development) and PostgreSQL (production)
- **Authentication**: Flask-Login with role-based access control (admin/manager/driver)
- **Security**: Password hashing with Werkzeug, CSRF protection, audit logging for all actions

## Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 5 for responsive design
- **Mobile-First Design**: Optimized for driver portal usage on mobile devices
- **Static Assets**: CSS/JS organization with custom styling and dashboard functionality
- **Form Handling**: WTForms for validation and CSRF protection

## Database Design
- **Multi-tenancy**: Branch-based data isolation with manager-branch associations
- **User Management**: Single user table with role differentiation and profile relationships
- **Fleet Management**: Vehicle tracking with maintenance schedules and status monitoring
- **Duty System**: Complex duty tracking with flexible compensation schemes (fixed, per-trip, slab-based, mixed)
- **Audit Trail**: Comprehensive logging of all user actions with IP and user agent tracking

## Role-Based Access Control
- **Admin**: Global access across all branches, full CRUD operations, system configuration
- **Manager**: Branch-restricted access via `manager_branches` association table, approval workflows
- **Driver**: Personal dashboard with duty management, earnings tracking, profile maintenance

## File Upload System
- **Document Management**: Aadhar, license, and profile photo uploads with validation
- **Security**: File type restrictions, size limits (16MB max), secure filename handling
- **Storage**: Local filesystem with provisions for cloud storage integration

## Compensation Engine
- **Flexible Schemes**: Multiple duty scheme types with JSON configuration storage
- **BMG Support**: Business Minimum Guarantee calculations
- **Real-time Calculation**: Dynamic earnings computation based on revenue and trip data

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web framework with SQLAlchemy, Login, and WTF extensions
- **SQLAlchemy**: Database ORM with relationship management
- **Bootstrap 5**: Frontend CSS framework with dark theme support
- **Font Awesome**: Icon library for UI enhancement

## Development Tools
- **Werkzeug**: WSGI utilities and security functions
- **ProxyFix**: Deployment middleware for proper header handling

## Deployment Considerations
- **Database**: Currently configured for SQLite with PostgreSQL production readiness
- **Session Management**: Environment-based secret key configuration
- **File Storage**: Local upload handling with cloud migration capability
- **Connection Pooling**: Configured for production database connections

## Missing Integrations (Potential Additions)
- **Payment Gateway**: For driver payment processing
- **SMS/Email Service**: For notifications and alerts
- **GPS Tracking**: For real-time vehicle location
- **Cloud Storage**: For document and photo storage
- **Analytics Platform**: For advanced reporting and insights