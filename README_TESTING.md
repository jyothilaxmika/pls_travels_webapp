# PLS TRAVELS Testing Suite

Complete automated testing infrastructure using Playwright for end-to-end testing of the fleet management application.

## 🧪 Test Suite Overview

### Test Categories

- **Authentication Tests** (`test_authentication.py`)
  - Login/logout functionality
  - Role-based access control
  - Navigation menu visibility

- **Driver Onboarding Tests** (`test_driver_onboarding.py`)
  - Driver registration workflow
  - Document upload functionality
  - Admin approval process

- **Duty Workflow Tests** (`test_duty_workflow.py`)
  - Duty start/end cycles
  - Photo capture validation
  - Odometer reading validation
  - Admin duty approval

- **Storage System Tests** (`test_storage_system.py`)
  - Document management dashboard
  - File gallery navigation
  - Security and access controls
  - File operations (view, download, delete)

- **Financial Workflow Tests** (`test_financial_workflow.py`)
  - Salary calculation after duty approval
  - Earnings display and reporting
  - Penalty and bonus application
  - Payment management

- **Integration Tests** (`test_integration.py`)
  - End-to-end user journeys
  - Multi-user concurrent access
  - Error handling and edge cases

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests
python run_tests.py all

# Run specific test categories
python run_tests.py auth        # Authentication tests
python run_tests.py workflow    # Business workflow tests
python run_tests.py storage     # Storage system tests
python run_tests.py integration # End-to-end tests
python run_tests.py fast        # Skip slow tests
```

### Advanced Usage
```bash
# Run specific test file
python -m pytest tests/test_authentication.py -v

# Run with markers
python -m pytest -m "auth and not slow" -v

# Run in headed mode (see browser)
python -m pytest --headed tests/test_authentication.py

# Generate test report
python -m pytest --html=test_report.html tests/
```

## 📁 Test Structure

```
tests/
├── conftest.py                 # Test configuration and fixtures
├── test_authentication.py     # Login, RBAC, navigation tests
├── test_driver_onboarding.py  # Driver registration and approval
├── test_duty_workflow.py      # Duty start/end, photo capture
├── test_storage_system.py     # Document management, file ops
├── test_financial_workflow.py # Earnings, payments, penalties
├── test_integration.py        # End-to-end integration tests
├── test_data/                 # Test files (images, documents)
├── screenshots/               # Test failure screenshots
└── videos/                    # Test execution recordings
```

## 🔧 Test Configuration

Test users and routes are configured in `tests/conftest.py`:

```python
TEST_USERS = {
    'admin': {'username': 'admin', 'password': 'admin123'},
    'manager': {'username': 'manager', 'password': 'manager123'},
    'driver': {'username': 'driver1', 'password': 'driver123'}
}
```

## 🎯 Test Markers

- `@pytest.mark.auth` - Authentication related tests
- `@pytest.mark.workflow` - Business workflow tests
- `@pytest.mark.storage` - Storage system tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Tests that take longer to run

## 📊 Test Coverage

The test suite covers:

✅ **User Authentication & Authorization**
✅ **Driver Registration & Onboarding**
✅ **Duty Start/End Workflows**
✅ **Document Upload & Management**
✅ **Storage System Operations**
✅ **Financial Calculations & Reporting**
✅ **Admin Approval Workflows**
✅ **Role-based Access Controls**
✅ **Error Handling & Edge Cases**

## 🐛 Debugging Tests

### Test Failures
- Screenshots automatically captured on failure
- Videos recorded for failed test runs
- Detailed error logs in test output

### Manual Debugging
```bash
# Run in headed mode to see browser
python -m pytest --headed --slowmo=1000 tests/test_authentication.py

# Run with debug mode
python -m pytest --pdb tests/test_authentication.py
```

## 🔧 Maintenance

### Adding New Tests
1. Create test file in `tests/` directory
2. Import fixtures from `conftest.py`
3. Use appropriate test markers
4. Follow naming convention: `test_*.py`

### Test Data
- Sample images created automatically in `tests/test_data/`
- Use `test_files` fixture for file uploads
- Use `test_driver_data` fixture for user data

## 💡 Best Practices

1. **Test Independence**: Each test should be independent
2. **Descriptive Names**: Use clear, descriptive test names
3. **Proper Cleanup**: Tests clean up after themselves
4. **Mock External Services**: Don't rely on external APIs
5. **Test Real Scenarios**: Test actual user workflows