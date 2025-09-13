# Twilio OTP integration - based on twilio_send_message blueprint
import os
import random
import string
from datetime import datetime, timedelta
from twilio.rest import Client
from models import db
import logging

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def generate_otp(length=6):
    """Generate a random OTP code"""
    return ''.join(random.choices(string.digits, k=length))

def send_twilio_otp(to_phone_number: str, otp_code: str) -> bool:
    """Send OTP via Twilio SMS"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message_body = f"Your PLS TRAVELS verification code is: {otp_code}. This code expires in 5 minutes."
        
        # Sending the SMS message
        message = client.messages.create(
            body=message_body, 
            from_=TWILIO_PHONE_NUMBER, 
            to=to_phone_number
        )
        
        logging.info(f"OTP SMS sent with SID: {message.sid} to {to_phone_number}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send OTP SMS to {to_phone_number}: {str(e)}")
        return False

def format_phone_number(phone_number: str) -> str:
    """Format phone number for Twilio (ensure it starts with country code)"""
    # Remove any non-digit characters
    phone_clean = ''.join(filter(str.isdigit, phone_number))
    
    # If it's an Indian number starting with 91, keep as is
    if phone_clean.startswith('91') and len(phone_clean) == 12:
        return '+' + phone_clean
    
    # If it's a 10-digit Indian number, add +91
    if len(phone_clean) == 10 and phone_clean.startswith(('6', '7', '8', '9')):
        return '+91' + phone_clean
    
    # If it already has a + sign, return as is
    if phone_number.startswith('+'):
        return phone_number
    
    # Default: assume it needs +91 (India)
    return '+91' + phone_clean