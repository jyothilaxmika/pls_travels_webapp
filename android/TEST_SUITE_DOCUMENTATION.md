# Android Testing Suite Documentation

## Overview
This comprehensive testing suite provides complete validation for the PLS Travels Driver Android application, ensuring production readiness through multiple layers of testing.

## Test Architecture

### 1. Unit Tests (`src/test/`)
- **Location**: `android/app/src/test/java/com/plstravels/driver/`
- **Framework**: JUnit 4, MockK, Truth assertions
- **Coverage**: Repositories, ViewModels, Services, Business Logic
- **Execution**: `./gradlew testDebugUnitTest`

#### Key Test Classes:
- `AuthRepositoryTest` - OTP authentication flow
- `DutyRepositoryTest` - Duty lifecycle management
- `AuthViewModelTest` - UI state management
- `LocationTrackingServiceTest` - Background location tracking

### 2. Integration Tests (`src/androidTest/`)
- **Framework**: AndroidX Test, Room Testing, MockWebServer
- **Coverage**: Database operations, API integration, Data flow
- **Execution**: Requires Android device/emulator

#### Key Test Classes:
- `DutyDaoIntegrationTest` - Database operations with real Room DB
- `ApiIntegrationTest` - Network layer with mock server
- Real database operations with constraints and transactions

### 3. UI Tests (`src/androidTest/ui/`)
- **Framework**: Compose Testing, Espresso
- **Coverage**: All screens, user interactions, UI state changes
- **Execution**: Automated UI testing on device

#### Key Features:
- `AuthScreenComposeTest` - Complete authentication flow
- State transitions and error handling
- Accessibility testing and keyboard navigation
- Multi-state UI validation

### 4. Instrumentation Tests (`src/androidTest/ui/`)
- **Framework**: Espresso, UI Automator
- **Coverage**: Device-specific functionality, system integration
- **Execution**: Real device interactions

#### Key Features:
- `MainActivityInstrumentedTest` - End-to-end workflows
- Permission handling (Location, Camera, Notifications)
- System integration (Network, Rotation, Background)
- Battery optimization and multi-window support

### 5. Performance Tests (`src/androidTest/performance/`)
- **Framework**: AndroidX Benchmark
- **Coverage**: Critical operations performance measurement
- **Execution**: Performance profiling on device

#### Benchmarked Operations:
- Location point insertion (batch and single)
- Database queries and complex operations
- Distance calculations and geofencing
- Data processing and filtering algorithms

### 6. Security Tests (`src/androidTest/security/`)
- **Framework**: AndroidX Security, Custom security validators
- **Coverage**: Authentication, encryption, security controls
- **Execution**: Security validation on device

#### Security Validations:
- Token encryption and secure storage
- Biometric authentication availability
- Root/debugging detection
- Certificate pinning validation
- Data encryption at rest and in transit
- Input sanitization and validation

## Test Infrastructure

### Test Data Factories (`testutils/factories/`)
- `TestDataFactory` - Comprehensive test data generation
- Realistic data with proper relationships
- Error scenarios and edge cases
- Performance test data sets

### Mock Providers (`testutils/mocks/`)
- `MockProviders` - Centralized mock configurations
- Repository, DAO, and API service mocks
- Network error simulation
- Offline/sync scenario mocking

### Test Rules and Base Classes
- `TestCoroutineRule` - Coroutine testing setup
- `DatabaseRule` - In-memory database setup
- `BaseUnitTest` - Common unit test setup
- `BaseRepositoryTest` - Repository-specific base class

### Custom Matchers and Assertions
- `TestMatchers` - Domain-specific assertions
- Truth subjects for complex object validation
- Hamcrest matchers for advanced matching
- Result and Flow testing utilities

## CI/CD Integration

### GitHub Actions Workflow (`github/workflows/android-ci.yml`)
- **Multi-API Level Testing**: API 28, 29, 30, 31
- **Parallel Execution**: Unit, Integration, UI tests
- **Security Scanning**: OWASP dependency check
- **Performance Benchmarking**: Automated performance regression testing
- **Code Coverage**: Codecov integration
- **Quality Gates**: SonarCloud analysis

### Pipeline Stages:
1. **Unit Tests** - Fast feedback on Ubuntu
2. **Instrumentation Tests** - Device testing on macOS with emulator
3. **Security Scan** - Security validation and dependency check
4. **Performance Test** - Benchmark execution and comparison
5. **Build & Deploy** - APK/AAB generation and Play Store deployment
6. **Code Quality** - Coverage reporting and quality analysis

### Deployment:
- **Staging**: Develop branch → Internal testing track
- **Production**: Main branch → Production track
- **Notifications**: Slack integration for build status

## Test Configuration

### Build Configuration (`build.gradle`)
- Comprehensive test dependencies
- Test orchestrator for isolation
- Multiple build variants (debug, staging, release)
- ProGuard testing configurations

### Test Properties (`test-config.properties`)
- Environment-specific settings
- Performance test parameters
- Security test configurations
- CI/CD optimization settings

## Running Tests

### Local Development
```bash
# Unit tests
./gradlew testDebugUnitTest

# Integration tests (requires device/emulator)
./gradlew connectedDebugAndroidTest

# Specific test class
./gradlew testDebugUnitTest --tests "AuthRepositoryTest"

# Performance tests
./gradlew connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.plstravels.driver.performance.LocationTrackingPerformanceTest

# Security tests
./gradlew connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.plstravels.driver.security.SecurityValidationTest
```

### Test Reports
- **Unit Test Reports**: `app/build/reports/tests/testDebugUnitTest/index.html`
- **Coverage Reports**: `app/build/reports/jacoco/testDebugUnitTestCoverage/html/index.html`
- **Lint Reports**: `app/build/reports/lint-results-debug.html`
- **Performance Reports**: `app/build/outputs/connected_android_test_additional_output/`

## Test Coverage Goals
- **Overall Coverage**: 80%+ line coverage
- **Repository Layer**: 90%+ coverage
- **ViewModel Layer**: 85%+ coverage
- **Service Layer**: 80%+ coverage
- **UI Layer**: 70%+ interaction coverage

## Best Practices Implemented

### 1. Test Organization
- Clear separation of unit, integration, and UI tests
- Consistent naming conventions
- Proper test categorization and tagging

### 2. Test Data Management
- Centralized test data factories
- Realistic test scenarios
- Proper test data cleanup

### 3. Mock Management
- Centralized mock providers
- Consistent mock configurations
- Scenario-based mock setups

### 4. Performance Testing
- Baseline measurements
- Regression detection
- Resource usage monitoring

### 5. Security Testing
- Comprehensive security validations
- Encryption verification
- Authentication testing
- Input validation testing

### 6. CI/CD Integration
- Automated test execution
- Quality gates and deployment controls
- Performance regression detection
- Security scanning integration

## Maintenance and Updates
- Regular test dependency updates
- Test flakiness monitoring and fixes
- Performance baseline updates
- Security test enhancement as new threats emerge
- CI/CD pipeline optimization

This testing suite provides comprehensive validation for production readiness, ensuring code quality, security, performance, and reliability of the Android driver application.