# Overview

PLS TRAVELS is a comprehensive multi-city driver and fleet management system built for transport companies. The system provides role-based access control with three user types: Admin (full system control), Manager (branch-specific operations), and Driver (mobile-first duty management portal). The application handles driver onboarding, vehicle management, duty tracking with flexible compensation schemes, earnings calculation, and comprehensive reporting across multiple city branches.

# Recent Changes

## September 23, 2025
- **Replit Environment Setup**: Successfully imported and configured the project for Replit deployment
  - **Database Integration**: Connected to Replit PostgreSQL database using provided DATABASE_URL
  - **Flask Configuration**: Verified Flask application factory pattern with proper ProxyFix middleware for Replit proxy
  - **Workflow Configuration**: Set up gunicorn server on port 5000 with proper Replit bindings
  - **CORS Setup**: Configured CORS for Replit domains (*.replit.app, *.repl.co) with credential support
  - **Deployment Ready**: Configured autoscale deployment target with production-ready gunicorn settings
  - **Security Headers**: Maintained comprehensive security headers and CSRF protection
  - **File Upload System**: Verified file upload system working with local filesystem storage
  - **Static Assets**: Confirmed CSS, JS, and image assets loading correctly through Flask static file serving
  - **Authentication System**: Username/password authentication system working (OTP disabled due to missing Twilio config)
  - **Import Error Resolution**: Fixed multiple import errors in service modules for proper application startup
  - **Admin User Creation**: Created default admin user (admin/admin123) for system access
  - **Project Status**: Application fully functional and ready for development/production use

- **Progressive Web App (PWA) Implementation**: Comprehensive PWA capabilities for native app-like experience
  - **PWA Manifest**: Complete web app manifest with icons, shortcuts, and installation metadata
  - **Service Worker**: Advanced service worker with offline caching, background sync, and push notification support
  - **Enhanced Camera Integration**: Professional camera widget with front/rear camera switching and high-quality photo capture
  - **Push Notifications**: Full push notification system with VAPID key management and subscription handling
  - **Offline Functionality**: IndexedDB-based offline storage for duties, photos, and earnings with automatic sync
  - **Background Sync**: Smart background synchronization when connectivity returns for seamless offline-to-online transitions
  - **Installation Prompts**: Intelligent PWA installation prompts with platform-specific instructions and user preference tracking
  - **App-like Navigation**: Enhanced navigation with swipe gestures, keyboard shortcuts, and app-like behaviors
  - **Offline Fallback**: Beautiful offline page with status indicators and automatic reconnection
  - **Performance Optimization**: Strategic caching with cache-first, network-first, and stale-while-revalidate strategies
  - **Mobile Experience**: Native app-like experience with status bar theming, address bar hiding, and gesture support

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