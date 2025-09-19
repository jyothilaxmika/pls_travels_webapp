# PLS Travels - Testing Infrastructure

## Overview

Comprehensive testing suite for PLS Travels fleet management application covering unit tests, integration tests, security tests, and end-to-end testing.

## Test Categories

### 1. Unit Tests (`tests/unit/`)
- **Models**: Test database models, relationships, and business logic
- **Services**: Test service layer classes and business operations
- **Utilities**: Test helper functions and utilities
- **Validation**: Test input validation and sanitization

### 2. Integration Tests (`tests/integration/`)
- **Database**: Test database operations, transactions, and migrations
- **Service Integration**: Test service layer integration with database
- **API Integration**: Test API endpoints and request/response handling
- **External Services**: Test third-party integrations (Twilio, storage)

### 3. Security Tests (`tests/security/`)
- **Authentication**: Test login, session management, JWT tokens
- **Authorization**: Test role-based access control and permissions
- **Input Validation**: Test XSS, SQL injection, and sanitization
- **Security Headers**: Test security headers and CSRF protection

### 4. End-to-End Tests (`tests/`)
- **Playwright Tests**: Browser-based functional testing
- **User Workflows**: Complete user journeys and business processes
- **Cross-browser Testing**: Testing across different browsers

## Quick Start

### Prerequisites
```bash
pip install pytest pytest-flask pytest-cov pytest-mock factory-boy
```

### Running Tests

#### All Simple Unit Tests (Recommended)
```bash
cd /path/to/project
python tests/simple_unit_tests.py
```

#### Pytest Unit Tests (when database issues resolved)
```bash
pytest tests/unit/ -v
```

#### Integration Tests (requires database)
```bash
pytest tests/integration/ -v --tb=short
```

#### Security Tests
```bash
pytest tests/security/ -v -m security
```

#### End-to-End Tests (requires running application)
```bash
# Start application first
python app.py &

# Run E2E tests
pytest tests/test_authentication.py -v
```

#### Coverage Report
```bash
pytest --cov=app --cov=services --cov=utils --cov-report=html
```

## Test Configuration

### Environment Variables
```bash
export FLASK_ENV=testing
export TESTING=true
export DATABASE_URL=sqlite:///:memory:
export SESSION_SECRET=test_secret_key
export JWT_SECRET_KEY=test_jwt_secret
export TWILIO_ACCOUNT_SID=test_sid
export TWILIO_AUTH_TOKEN=test_token
export TWILIO_PHONE_NUMBER=+1234567890
```

### Pytest Configuration (`pytest.ini`)
- **Coverage**: 80% minimum threshold
- **Markers**: Unit, integration, security, slow, database
- **Test Discovery**: Auto-discovery in tests/ directory
- **Timeout**: 300 seconds maximum per test
- **Environment**: Automated test environment setup

## Test Data and Fixtures

### Factory Classes
- `BranchFactory`: Creates test branches
- `UserFactory`: Creates test users with different roles
- `DriverProfileFactory`: Creates driver profiles
- `VehicleFactory`: Creates test vehicles
- `DutyFactory`: Creates test duties
- `DutySchemeFactory`: Creates duty schemes

### Test Data
- **Mock Users**: Admin, manager, and driver test accounts
- **Sample Files**: Test images for document uploads
- **Test Routes**: Predefined application routes
- **Mock Services**: Mocked external service responses

## Continuous Integration

### GitHub Actions Pipeline
- **Multi-Python Versions**: Testing on Python 3.11
- **Database Testing**: PostgreSQL service for integration tests
- **Security Scanning**: Automated security vulnerability detection
- **Code Quality**: Linting with flake8, black, isort
- **Coverage Reports**: Automated coverage reporting

### Pipeline Stages
1. **Lint**: Code style and quality checks
2. **Unit Tests**: Fast, isolated component testing
3. **Integration Tests**: Database and service integration
4. **Security Tests**: Security vulnerability scanning
5. **E2E Tests**: Full application workflow testing
6. **Performance Tests**: Load and performance validation

## Test Writing Guidelines

### Unit Tests
```python
def test_user_creation():
    """Test user model creation with proper validation"""
    user = UserFactory()
    assert user.username is not None
    assert user.email is not None
    assert user.password_hash is not None
```

### Integration Tests
```python
def test_driver_service_integration(db_session, branch):
    """Test driver service with database integration"""
    service = DriverService()
    result = service.create_driver({
        'username': 'testdriver',
        'branch_id': branch.id
    })
    assert result['success'] is True
```

### Security Tests
```python
def test_xss_prevention():
    """Test XSS attack prevention"""
    malicious_input = "<script>alert('XSS')</script>"
    sanitized = service.sanitize_input(malicious_input)
    assert '<script>' not in sanitized
```

### Mocking External Services
```python
@patch('services.notification_service.NotificationService._send_sms')
def test_otp_sending(mock_send_sms):
    mock_send_sms.return_value = {'success': True}
    service = NotificationService()
    result = service.send_otp('9999999999')
    assert result['success'] is True
```

## Test Database Management

### In-Memory SQLite (Default)
- Fast test execution
- No persistent data
- Automatic cleanup
- Ideal for unit tests

### PostgreSQL Test Database
- Production-like environment
- Full feature testing
- Migration testing
- Used in CI/CD pipeline

### Test Data Cleanup
- Automatic rollback after each test
- Transaction-based isolation
- Factory-generated test data
- No test data pollution

## Performance Testing

### Load Testing
```python
def test_bulk_operations_performance():
    """Test bulk database operations performance"""
    start_time = datetime.now()
    # Bulk operation
    end_time = datetime.now()
    execution_time = (end_time - start_time).total_seconds()
    assert execution_time < 5.0  # Should complete within 5 seconds
```

### Concurrency Testing
```python
def test_concurrent_duty_prevention():
    """Test that drivers can't start multiple duties"""
    # Test concurrent operation prevention
    assert second_duty_result['success'] is False
```

## Debugging Tests

### Verbose Output
```bash
pytest -v -s tests/
```

### Debug Specific Test
```bash
pytest tests/unit/test_models.py::TestUserModel::test_create_user -v -s
```

### Coverage Analysis
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Test Profiling
```bash
pytest --profile tests/
```

## Test Markers

Use markers to categorize and run specific test types:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests  
pytest -m integration

# Run only security tests
pytest -m security

# Skip slow tests
pytest -m "not slow"

# Run database tests only
pytest -m database
```

## Known Issues and Workarounds

### 1. psycopg2 Binary Issue
**Issue**: `ModuleNotFoundError: No module named 'psycopg2._psycopg'`
**Workaround**: Use simple unit tests with SQLite for development
**Solution**: Proper psycopg2-binary installation in deployment environment

### 2. Playwright Dependencies
**Issue**: Playwright requires additional browser binaries
**Workaround**: Use simple unit tests for CI/CD, Playwright for local E2E testing
**Solution**: Separate E2E testing pipeline with proper browser setup

### 3. Test Isolation
**Issue**: Tests affecting each other due to shared state
**Solution**: Use database transactions and proper fixture cleanup

## Contributing to Tests

### Adding New Tests
1. Choose appropriate test category (unit/integration/security)
2. Use existing factories for test data
3. Follow naming convention: `test_<functionality>`
4. Add appropriate markers
5. Include docstrings explaining test purpose

### Test Maintenance
1. Keep tests simple and focused
2. Update tests when changing business logic
3. Maintain high test coverage (>80%)
4. Regular cleanup of obsolete tests
5. Performance optimization for slow tests

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/latest/testing/)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [Playwright Testing](https://playwright.dev/python/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Testing Philosophy**: Every feature should have comprehensive test coverage including happy path, edge cases, and error conditions. Tests should be fast, reliable, and maintainable.