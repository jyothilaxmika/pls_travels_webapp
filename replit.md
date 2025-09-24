# Overview

PLS TRAVELS is a multi-city driver and fleet management system designed for transport companies. It offers role-based access for Admin, Manager, and Driver user types, facilitating driver onboarding, vehicle management, duty tracking with flexible compensation, and earnings calculation across multiple city branches. The system aims to streamline operations and provide comprehensive reporting.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## UI/UX Decisions
The system features a professional corporate theme with a navy blue primary color, green accents, and corporate gray secondary colors, ensuring a business-ready appearance. It uses an attractive, all-content-visible theme with enhanced text contrast, improved navigation, and clear visual hierarchy. The design is mobile-first, optimized for driver portal usage, and implements Progressive Web App (PWA) capabilities including an app manifest, service worker for offline functionality, enhanced camera integration, and push notifications for a native app-like experience.

## Technical Implementations
The backend is built with Flask, utilizing a Blueprint pattern for modularity and an application factory for flexible configuration. It uses SQLAlchemy ORM, supporting both SQLite (development) and PostgreSQL (production). Authentication is handled by Flask-Login with role-based access control, and security features include password hashing, CSRF protection, and audit logging. The frontend uses Jinja2 with Bootstrap 5 for responsive design and WTForms for form handling and validation.

## Feature Specifications
- **Role-Based Access Control**: Differentiates access for Admin (global), Manager (branch-specific), and Driver (personal dashboard).
- **Multi-Tenancy**: Supports branch-based data isolation.
- **File Upload System**: Allows camera capture or traditional file uploads for documents (Aadhar, license) and photos, with support for JPG, PNG, PDF formats, file previews, and local filesystem storage.
- **Compensation Engine**: Implements flexible duty schemes (fixed, per-trip, slab-based, mixed) with JSON configuration, Business Minimum Guarantee (BMG) support, and real-time earnings calculation.
- **PWA Features**: Includes advanced service worker for offline caching, background sync, push notification support, and IndexedDB-based offline storage for critical data.
- **CSRF Token Handling**: Extended CSRF token validity to 4 hours with centralized fetchWithCSRF helper that ensures session cookies are sent with all requests, proper CSRF headers, and enhanced error handling for expired tokens.
- **Duty Workflow Enhancements**: Implemented a secondary approval system for scheme templates with dual-control security, database migrations for approval status, and enhanced audit logging.

## System Design Choices
The system is designed with an emphasis on security, scalability, and user experience. It incorporates a comprehensive audit trail for all user actions and manages user, fleet, and duty data effectively. The PWA implementation ensures a robust mobile experience with offline capabilities and push notifications, crucial for drivers. The backend architecture supports a clear separation of concerns and facilitates future integrations.

# External Dependencies

- **Flask**: Web framework for backend development.
- **SQLAlchemy**: Object Relational Mapper (ORM) for database interactions.
- **Bootstrap 5**: Frontend CSS framework for responsive design.
- **Font Awesome**: Icon library for UI elements.
- **Werkzeug**: WSGI utilities and security functions.
- **ProxyFix**: Middleware for handling proxy headers in deployment.
- **PostgreSQL**: Production database, currently using Neon managed service.