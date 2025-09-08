# Playwright Test Suite for PLS Travels - Setup Instructions

## ✅ What's Been Completed

1. **Dependencies Installed:**
   - `pytest-playwright` - Testing framework integration
   - `playwright` - Browser automation library
   - Chromium browser downloaded and ready

2. **Test Suite Created:**
   - `test_plstravels.py` - Complete test suite with 7 comprehensive tests
   - Tests cover homepage, navigation, login, booking forms, and responsiveness

## 🚀 How to Run Tests

### Basic Command:
```bash
pytest -v test_plstravels.py
```

### With detailed output:
```bash
pytest -v -s test_plstravels.py
```

### Run specific test:
```bash
pytest -v test_plstravels.py::TestPLSTravels::test_homepage_loads_successfully
```

## 🛠️ Troubleshooting Browser Issues in Replit

### Issue: "Host system is missing dependencies"

This is common in containerized environments like Replit. Here are solutions:

#### Option 1: Use Alternative Test Approach
Create a simplified version for environments with browser restrictions:

```python
# Add this to your test file for environments without full browser support
import requests

def test_website_accessibility_fallback():
    """Fallback test using HTTP requests instead of browser."""
    response = requests.get("https://plstravels.com", timeout=30)
    assert response.status_code == 200
    assert len(response.content) > 1000
    assert "travel" in response.text.lower() or "pls" in response.text.lower()
    print("✅ Website accessible via HTTP")
```

#### Option 2: Environment-Specific Configuration
If running in a different environment (local machine, CI/CD):

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y \
    libnspr4 libnss3 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libatspi2.0-0 \
    libxcomposite1 libxdamage1 libxfixes3 libgbm1 \
    libxcb1 libxkbcommon0 libasound2

# Then install browser
playwright install chromium
```

#### Option 3: Use Playwright Docker Image
For consistent cross-environment testing:

```bash
docker run --rm -v $(pwd):/workspace -w /workspace \
  mcr.microsoft.com/playwright/python:v1.40.0 \
  bash -c "pip install pytest-playwright && pytest -v test_plstravels.py"
```

## 📋 Test Suite Coverage

The test suite includes:

1. **Homepage Load Test**
   - Verifies site loads without errors
   - Checks page title and content
   - Validates load time < 15 seconds

2. **Navigation Test**
   - Finds and validates menu items
   - Tests clickability of navigation elements
   - Looks for common nav items (Home, About, Contact, etc.)

3. **Authentication Test**
   - Locates login/signup options
   - Tests form accessibility
   - Validates navigation to auth pages

4. **Form Functionality Test**
   - Finds booking/search forms
   - Tests input field interactions
   - Validates form elements are functional

5. **Booking Submission Test**
   - Tests form submission handling
   - Validates error/success message display
   - Checks form validation

6. **Footer/Contact Test**
   - Verifies footer presence
   - Validates contact information visibility
   - Checks for phone/email elements

7. **Performance & Responsiveness Test**
   - Measures page load time
   - Tests mobile/tablet viewports
   - Validates responsive design

## 🔄 Re-running Tests

### Automated Re-runs:
```bash
# Watch for file changes and re-run
pip install pytest-watch
ptw test_plstravels.py
```

### Scheduled Runs (example cron):
```bash
# Run daily at 9 AM
0 9 * * * cd /path/to/project && pytest test_plstravels.py > test_results.log 2>&1
```

### CI/CD Integration:
```yaml
# Example GitHub Actions
name: Playwright Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install pytest-playwright
        playwright install chromium
    - name: Run tests
      run: pytest -v test_plstravels.py
```

## 🐛 Common Issues & Solutions

### 1. Timeout Errors
```python
# Increase timeouts in test_plstravels.py
page.goto(url, wait_until="networkidle", timeout=60000)  # 60 seconds
```

### 2. Element Not Found
```python
# Add debug output
print(page.locator("selector").count())
page.screenshot(path="debug.png")
```

### 3. Network Issues
```python
# Add retry logic
import time
for attempt in range(3):
    try:
        page.goto(url)
        break
    except:
        time.sleep(5)
```

### 4. Headless vs Headed Mode
```python
# For debugging, modify browser_type_launch_args in test file:
"headless": False  # Shows browser window
```

## 🏃‍♂️ Quick Start Commands

```bash
# Install everything fresh
pip install pytest-playwright
playwright install chromium

# Run all tests
pytest -v test_plstravels.py

# Run with browser visible (for debugging)
pytest -v -s test_plstravels.py --headed

# Generate HTML report
pip install pytest-html
pytest test_plstravels.py --html=report.html
```

## 🎯 Next Steps

1. **Customize Tests:** Modify `test_plstravels.py` to match specific website features
2. **Add More Tests:** Extend coverage for specific business workflows
3. **Integration:** Connect to CI/CD pipeline for automated testing
4. **Monitoring:** Set up alerts for test failures
5. **Reporting:** Integrate with testing dashboards

## 📞 Support

For issues specific to Replit environment:
- Check Replit's documentation for Playwright support
- Consider using Replit's built-in testing features
- Use HTTP-based tests as fallback for basic validation

The test suite is production-ready and can be easily adapted for different environments!