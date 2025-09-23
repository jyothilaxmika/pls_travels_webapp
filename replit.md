# Overview

PLS TRAVELS is a comprehensive multi-city driver and fleet management system built for transport companies. The system provides role-based access control with three user types: Admin (full system control), Manager (branch-specific operations), and Driver (mobile-first duty management portal). The application handles driver onboarding, vehicle management, duty tracking with flexible compensation schemes, earnings calculation, and comprehensive reporting across multiple city branches.

# Recent Changes

## September 23, 2025 (Latest)
- **Advanced Desktop Responsive Design**: Complete enhancement of admin portal for superior desktop experience
  - **Desktop-First Optimization**: Enhanced breakpoints for large screens (1920px+, 1440px+, 1200px+) with proper screen utilization
  - **Collapsible Sidebar System**: Desktop sidebar toggle with smooth animations and intelligent icon-only collapsed state
  - **Enhanced Header Design**: Three-section header layout with breadcrumb navigation, user avatar, and professional gradients
  - **Advanced Grid System**: Flexible CSS Grid implementation with desktop-specific layouts (2/3/4-column options)
  - **Smart Content Adaptation**: Fixed positioning for desktop with proper padding and margin calculations for all screen sizes
  - **Professional Animations**: Cubic-bezier transitions, hover effects, and smooth state changes throughout interface
  - **Typography Scaling**: Responsive font sizing optimized for desktop readability and mobile accessibility
  - **Enhanced Collapsible Menus**: Animated chevron indicators, smooth expand/collapse with height transitions
  - **Desktop Performance**: Fixed sidebar with proper z-index layering and scroll optimization for large content areas

## September 23, 2025 (Earlier)
- **Complete Layout Transformation**: Successfully implemented cleaner gradient theme layout for PLS TRAVELS admin portal
  - **Simplified Architecture**: Replaced complex Bootstrap layout with clean, organized structure (500 lines vs thousands)
  - **Beautiful Gradient Design**: Applied `linear-gradient(135deg, #2ecc71, #8e44ad)` to sidebar creating stunning visual appeal
  - **Responsive Excellence**: Desktop fixed sidebar, tablet adaptive width, mobile slide-out overlay with hamburger toggle
  - **Security Hardened**: XSS-safe JavaScript implementation using createElement instead of innerHTML
  - **Template Reliability**: Added default filters for all count variables preventing Jinja2 template errors
  - **Component Consistency**: Unified design system with cards, tables, forms, buttons, and alerts
  - **Performance Optimized**: Removed Bootstrap dependency while maintaining professional appearance
  - **Professional Polish**: Clean header, collapsible menus, smooth transitions, and modern hover effects

## September 23, 2025 (Earlier)
- **Complete Admin Portal Responsive Design**: Comprehensive mobile-first implementation for optimal cross-device experience
  - **Mobile Navigation**: Enhanced navbar with navbar-expand-xl breakpoint and fully functional offcanvas sidebar for mobile access
  - **Responsive Grid System**: Dashboard metric cards using col-6 col-lg-3 for perfect 2x2 mobile → 4x1 desktop stacking
  - **Chart Responsiveness**: Chart.js v3 compatible configuration with proper .chart-container wrappers for dynamic sizing
  - **Mobile-First CSS**: Comprehensive media queries at 1199.98px, 767.98px, and 575.98px with typography scaling and spacing optimization
  - **Table Optimization**: Horizontal scrolling tables with .table-responsive wrappers for mobile viewing
  - **Container Layout**: Container-fluid implementation with responsive padding for all screen sizes
  - **Professional Implementation**: Maintains vibrant growth-focused color theme while ensuring accessibility across all devices
- **Offcanvas Navigation Fix**: Resolved layout collapse issue with sidebar menu
  - **Responsive Width Control**: Optimized offcanvas width (85% max 320px) to prevent full screen coverage
  - **Smart JavaScript Behavior**: Auto-close on navigation clicks and responsive screen size changes
  - **Enhanced CSS Controls**: Proper hiding/showing states with transform and visibility management
  - **Smooth User Experience**: Professional slide-in/out behavior across all device sizes

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