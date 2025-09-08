#!/usr/bin/env python3
"""
Test runner for PLS TRAVELS Playwright tests
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Run the Playwright test suite"""
    
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    
    print("🚀 Starting PLS TRAVELS Test Suite")
    print("=" * 50)
    
    # Basic test run command
    cmd = [
        "python", "-m", "pytest", 
        "tests/",
        "-v",
        "--tb=short",
        "--strict-config"
    ]
    
    # Add markers based on arguments
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "auth":
            cmd.extend(["-m", "auth"])
            print("🔐 Running Authentication Tests")
            
        elif test_type == "workflow":
            cmd.extend(["-m", "workflow"])  
            print("⚙️ Running Workflow Tests")
            
        elif test_type == "storage":
            cmd.extend(["-m", "storage"])
            print("💾 Running Storage Tests")
            
        elif test_type == "integration":
            cmd.extend(["-m", "integration"])
            print("🔗 Running Integration Tests")
            
        elif test_type == "e2e":
            cmd.extend(["-m", "e2e"])
            print("🎯 Running End-to-End Tests")
            
        elif test_type == "fast":
            cmd.extend(["-m", "not slow"])
            print("⚡ Running Fast Tests Only")
            
        elif test_type == "all":
            print("🎭 Running All Tests")
            
        else:
            print(f"❓ Unknown test type: {test_type}")
            print("Available options: auth, workflow, storage, integration, e2e, fast, all")
            return 1
    else:
        print("🎭 Running All Tests")
    
    # Add headless option for CI
    if os.getenv("CI") or "--headless" in sys.argv:
        os.environ["PLAYWRIGHT_HEADLESS"] = "true"
        print("🤖 Running in headless mode")
    
    # Run the tests
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        return 130
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())