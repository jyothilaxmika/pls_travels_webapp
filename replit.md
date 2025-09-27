# Overview

PLS TRAVELS is a comprehensive multi-city driver and fleet management system built for transport companies. The system provides role-based access control with three user types: Admin (full system control), Manager (branch-specific operations), and Driver (mobile-first duty management portal). The application handles driver onboarding, vehicle management, duty tracking with flexible compensation schemes, earnings calculation, and comprehensive reporting across multiple city branches.

# Recent Changes

## September 22, 2025
- **Professional Corporate Theme**: Complete color scheme overhaul for professional appearance
  - **Navy Blue Primary**: Changed from purple to professional navy blue (#1e3a8a) for corporate look
  - **Professional Green Accent**: Replaced orange with professional green (#059669) for business appeal
  - **Status Colors Updated**: All status indicators use professional color palette
  - **Corporate Gray Secondary**: Updated secondary colors to professional grays
  - **Enhanced Professionalism**: All UI elements now use sophisticated, corporate-appropriate colors
  - **Business-Ready Appearance**: Color scheme suitable for enterprise and corporate clients

## September 20, 2025
- **Screen Flickering Resolution**: Complete elimination of page flickering issues
  - **Auto-Refresh Disabled**: Removed 5-minute automatic page refreshes causing flickering
  - **Service Worker Issues Fixed**: Disabled problematic PWA features preventing screen disruption
  - **Navigation Stability**: Fixed week navigation and calendar functions preventing page reloads
  - **Stable User Experience**: Application now provides smooth, uninterrupted interface
- **Attractive All-Content-Visible Theme**: Complete theme overhaul for maximum visibility and attractiveness
  - **Enhanced Text Contrast**: Updated text colors to #374151 for optimal readability on light backgrounds
  - **Improved Navigation**: White text on gradient background with proper hover effects and shadows
  - **Better Cards & Tables**: Clean white backgrounds with subtle borders and enhanced shadows
  - **Enhanced Forms**: Clear borders, proper focus states, and improved visual feedback
  - **Better Buttons**: Improved color contrast with white text on colored backgrounds
  - **Global Typography**: Anti-aliased fonts with proper sizing and spacing throughout
  - **Comprehensive Styling**: All UI elements now have proper contrast and visual hierarchy
  - **Mobile-Responsive**: Consistent visibility across all device sizes

## September 18, 2025
- **Google Play Store Launch Ready**: Complete Play Store deployment infrastructure implemented
  - **Automated CI/CD Pipeline**: GitHub Actions workflow for AAB builds with multi-track deployment support (internal/alpha/beta/production)
  - **App Bundle Optimization**: AAB generation with language, density, and ABI splits for optimal download sizes
  - **Production Signing**: Secure keystore management and automated signing configuration for Play Store submission
  - **Store Metadata**: Comprehensive app descriptions, feature listings, and localized release notes
  - **Deployment Documentation**: Complete setup guide for Google Play Console API integration and service account configuration
  - **Security Hardened**: Certificate pinning, ProGuard obfuscation, and enterprise-grade security for production release

## September 14, 2025
- **Production-Ready Android Driver App**: Complete transformation from Flask web application to enterprise-grade native Android app
  - **Authentication System**: OTP-based login with secure JWT token management and encrypted storage
  - **Complete UI Suite**: Professional Material Design 3 interface with dark theme support and accessibility compliance
  - **Photo/Document Management**: Camera integration with automatic upload, file management, and WorkManager-based synchronization
  - **Location Services**: Enterprise-grade GPS tracking with real-time updates, battery optimization, and comprehensive location statistics
  - **Push Notifications**: FCM integration with interactive action buttons, emergency alerts, and Android 13+ permission handling
  - **Data Architecture**: Comprehensive offline-first architecture with Room database, API integration, and conflict resolution
  - **Error Handling & Monitoring**: Firebase Crashlytics integration with structured logging and comprehensive crash reporting
  - **Production Security**: Complete security framework with R8 obfuscation, certificate pinning, anti-tampering detection, and runtime hardening
  - **Performance Optimization**: Memory management, database optimization, UI performance enhancements, and comprehensive monitoring infrastructure
  - **Enterprise Testing**: 200+ test cases covering unit, integration, UI, performance, and security testing with CI/CD pipeline
  - **Production Build**: Complete signing configuration, security hardening, and deployment readiness for Google Play Store

## September 7, 2025
- **Enhanced File Upload System**: Comprehensive file upload functionality with multiple options
  - Added dual upload methods: camera capture OR traditional file upload
  - Support for multiple file formats: JPG, PNG, PDF for documents
  - File preview functionality shows selected files before upload
  - Added route to serve uploaded files from `/uploads` path to fix photo display
  - Multiple mobile number support (up to 4 phone numbers per driver)
  - Enhanced driver profile with additional phone fields
  - Organized cloud storage infrastructure with fallback to local storage
- **Authentication System**: Reverted to original username/password authentication system
  - Removed Twilio OTP authentication due to service limitations
  - Maintained secure password-based login with role-based access control
  - Yellow-themed login interface with modern styling

## September 6, 2025
- **Database Migration**: Successfully migrated from SQLite to PostgreSQL using Neon managed database service
- **Approval Flow Modification**: Updated driver approval workflow to allow PENDING status drivers to access duty management features
  - Modified `driver_routes.py` to allow both ACTIVE and PENDING status drivers
  - Updated duty management template to only restrict rejected/suspended/terminated drivers
  - Fixed hybrid property issues with `start_time` and `end_time` attributes in models

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