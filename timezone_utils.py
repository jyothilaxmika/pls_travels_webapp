from datetime import datetime
import pytz

def get_ist_time_naive():
    """Get current IST time as naive datetime for database storage"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)