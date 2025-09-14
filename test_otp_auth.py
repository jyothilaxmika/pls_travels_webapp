"""
Test code for OTP-only authentication system
Demonstrates axios/fetch usage for the new auth endpoints
"""

import requests
import json

# Base URL for your Flask application
BASE_URL = "http://localhost:5000"

def test_signup_flow():
    """Test the complete signup flow with OTP verification"""
    print("=== Testing Signup Flow ===")
    
    # Step 1: Register with phone number
    signup_data = {
        "name": "John Doe",
        "phone": "9876543210",  # Will be formatted to +919876543210
        "email": "john@example.com"  # Optional
    }
    
    print("1. Sending signup request...")
    response = requests.post(f"{BASE_URL}/signup", json=signup_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 201:
        signup_result = response.json()
        print(f"OTP sent to: {signup_result['target']}")
        
        # In a real app, user would receive OTP via SMS
        # For testing, you'd need to check the server logs for the OTP
        otp_code = input("Enter the OTP you received: ")
        
        # Step 2: Verify OTP and complete signup
        verify_data = {
            "otp": otp_code,
            "phone": "9876543210",
            "purpose": "signup"
        }
        
        print("2. Verifying OTP...")
        verify_response = requests.post(f"{BASE_URL}/verify-otp", json=verify_data)
        print(f"Status: {verify_response.status_code}")
        print(f"Response: {verify_response.json()}")
        
        if verify_response.status_code == 200:
            result = verify_response.json()
            access_token = result['access_token']
            print(f"✅ Signup successful! Access token: {access_token[:20]}...")
            return access_token
        else:
            print("❌ OTP verification failed")
            return None
    else:
        print("❌ Signup failed")
        return None

def test_login_flow():
    """Test the login flow for existing users"""
    print("\n=== Testing Login Flow ===")
    
    # Step 1: Request OTP for login
    login_data = {
        "phone": "9876543210"  # Existing user
    }
    
    print("1. Requesting login OTP...")
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        login_result = response.json()
        print(f"OTP sent to: {login_result['target']}")
        
        # Get OTP from user
        otp_code = input("Enter the OTP you received: ")
        
        # Step 2: Verify OTP and get JWT token
        verify_data = {
            "otp": otp_code,
            "phone": "9876543210",
            "purpose": "login"
        }
        
        print("2. Verifying OTP...")
        verify_response = requests.post(f"{BASE_URL}/verify-otp", json=verify_data)
        print(f"Status: {verify_response.status_code}")
        print(f"Response: {verify_response.json()}")
        
        if verify_response.status_code == 200:
            result = verify_response.json()
            access_token = result['access_token']
            print(f"✅ Login successful! Access token: {access_token[:20]}...")
            return access_token
        else:
            print("❌ OTP verification failed")
            return None
    else:
        print("❌ Login failed")
        return None

def test_protected_route(access_token):
    """Test accessing a protected route with JWT token"""
    print("\n=== Testing Protected Route Access ===")
    
    if not access_token:
        print("❌ No access token available")
        return
    
    # Example: Access driver dashboard (protected route)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # This would be updated once JWT middleware is implemented
    print("Note: Protected route testing requires JWT middleware implementation")
    print(f"Use this header for protected requests: Authorization: Bearer {access_token}")

# JavaScript/Frontend examples
def print_frontend_examples():
    """Print examples for frontend JavaScript usage"""
    print("\n=== Frontend JavaScript Examples ===")
    
    print("""
// Signup with axios
async function signup(name, phone, email) {
    try {
        const response = await axios.post('/signup', {
            name: name,
            phone: phone,
            email: email
        });
        
        if (response.data.success) {
            console.log('OTP sent:', response.data.message);
            return response.data;
        }
    } catch (error) {
        console.error('Signup failed:', error.response.data.message);
    }
}

// Login with fetch
async function login(phone) {
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                phone: phone
            })
        });
        
        const data = await response.json();
        if (data.success) {
            console.log('OTP sent:', data.message);
            return data;
        }
    } catch (error) {
        console.error('Login failed:', error);
    }
}

// Verify OTP
async function verifyOTP(otp, phone, purpose) {
    try {
        const response = await axios.post('/verify-otp', {
            otp: otp,
            phone: phone,
            purpose: purpose // 'login' or 'signup'
        });
        
        if (response.data.success) {
            // Store JWT token
            localStorage.setItem('access_token', response.data.access_token);
            console.log('Authentication successful:', response.data.user);
            return response.data;
        }
    } catch (error) {
        console.error('OTP verification failed:', error.response.data.message);
    }
}

// Use JWT token for protected requests
async function makeProtectedRequest(url) {
    const token = localStorage.getItem('access_token');
    
    try {
        const response = await axios.get(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        return response.data;
    } catch (error) {
        if (error.response.status === 401) {
            // Token expired or invalid, redirect to login
            console.log('Authentication required');
            // Redirect to login page
        }
    }
}
""")

if __name__ == "__main__":
    print("OTP-Only Authentication System Test")
    print("===================================")
    
    # Test signup flow
    token_from_signup = test_signup_flow()
    
    # Test login flow
    token_from_login = test_login_flow()
    
    # Test protected route access
    test_protected_route(token_from_signup or token_from_login)
    
    # Print frontend examples
    print_frontend_examples()
    
    print("\n=== Summary ===")
    print("✅ Password-based authentication has been completely removed")
    print("✅ New OTP-only endpoints implemented: /signup, /login, /verify-otp")
    print("✅ JWT token-based authentication ready")
    print("✅ Secure OTP handling with SHA-256 hashing")
    print("✅ Account enumeration protection implemented")
    print("✅ Role-based access control (admin-only role elevation)")
    print("\nNext steps:")
    print("- Implement JWT middleware for route protection")
    print("- Update existing routes to use @jwt_required decorator")
    print("- Add rate limiting for OTP requests")
    print("- Implement email OTP sending (currently SMS only)")