"""
Production-ready rate limiting for OTP system
Implements per-phone, per-IP throttling and daily SMS caps
"""
import time
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class OTPRateLimiter:
    """
    Production-grade rate limiter and brute-force protection for OTP system:
    - Per-phone cooldown (prevents spam to same number)
    - Per-IP cooldown (prevents abuse from same source)
    - Daily SMS caps per phone (cost control)
    - Verification attempt tracking with lockouts (prevents brute-force)
    - Exponential backoff for repeated failures
    - Automatic cleanup of expired entries
    """
    
    def __init__(self):
        self._lock = Lock()
        
        # Per-phone rate limiting (phone -> timestamp)
        self._phone_cooldowns = {}
        self._phone_cooldown_seconds = 60  # 1 minute between sends to same phone
        
        # Per-IP rate limiting (ip -> timestamp)
        self._ip_cooldowns = {}
        self._ip_cooldown_seconds = 30  # 30 seconds between sends from same IP
        
        # Daily SMS caps (phone -> {date: count})
        self._daily_sms_counts = defaultdict(dict)
        self._max_sms_per_day = 10  # Maximum SMS per phone per day
        
        # Verification attempt tracking (phone -> {session_id: attempts, lockout_until: timestamp})
        self._verification_attempts = defaultdict(dict)
        self._max_verification_attempts_per_session = 5  # Max attempts per OTP session
        self._max_verification_attempts_per_phone_hourly = 15  # Max attempts per phone per hour
        self._verification_lockout_base_seconds = 60  # Base lockout duration (1 minute)
        self._verification_lockout_max_seconds = 3600  # Max lockout duration (1 hour)
        
        # IP-based verification tracking (ip -> {attempts: count, lockout_until: timestamp})
        self._ip_verification_attempts = {}
        self._max_verification_attempts_per_ip_hourly = 50  # Max attempts per IP per hour
        
        # Session-based tracking (session_id -> {phone: str, attempts: int, created_at: timestamp})
        self._session_verification_tracking = {}
        
        # Last cleanup time
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Cleanup every 5 minutes
    
    def can_send_otp(self, phone_number, client_ip):
        """
        Check if OTP can be sent based on all rate limiting rules.
        
        Args:
            phone_number (str): Target phone number
            client_ip (str): Client IP address
            
        Returns:
            tuple: (can_send: bool, reason: str, retry_after: int)
        """
        with self._lock:
            self._cleanup_expired_entries()
            
            current_time = time.time()
            today = datetime.now().date()
            
            # Check per-phone cooldown
            if phone_number in self._phone_cooldowns:
                phone_last_sent = self._phone_cooldowns[phone_number]
                phone_time_remaining = self._phone_cooldown_seconds - (current_time - phone_last_sent)
                if phone_time_remaining > 0:
                    return False, f"Rate limited for phone number", int(phone_time_remaining)
            
            # Check per-IP cooldown
            if client_ip in self._ip_cooldowns:
                ip_last_sent = self._ip_cooldowns[client_ip]
                ip_time_remaining = self._ip_cooldown_seconds - (current_time - ip_last_sent)
                if ip_time_remaining > 0:
                    return False, f"Rate limited for IP address", int(ip_time_remaining)
            
            # Check daily SMS cap
            phone_today_count = self._daily_sms_counts[phone_number].get(today, 0)
            if phone_today_count >= self._max_sms_per_day:
                # Calculate seconds until midnight
                tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                seconds_until_reset = int((tomorrow - datetime.now()).total_seconds())
                return False, f"Daily SMS limit reached", seconds_until_reset
            
            return True, "OK", 0
    
    def can_verify_otp(self, phone_number, client_ip, session_id):
        """
        Check if OTP verification is allowed based on brute-force protection rules.
        
        Args:
            phone_number (str): Target phone number
            client_ip (str): Client IP address
            session_id (str): OTP session identifier
            
        Returns:
            tuple: (can_verify: bool, reason: str, lockout_seconds: int)
        """
        with self._lock:
            self._cleanup_expired_entries()
            
            current_time = time.time()
            current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
            
            # Check session-based attempts
            session_data = self._session_verification_tracking.get(session_id, {})
            session_attempts = session_data.get('attempts', 0)
            
            if session_attempts >= self._max_verification_attempts_per_session:
                return False, "Too many attempts for this OTP session", self._verification_lockout_base_seconds
            
            # Check phone-based hourly limits
            phone_attempts = self._verification_attempts[phone_number]
            phone_hourly_key = f"{current_hour.isoformat()}_attempts"
            phone_hourly_count = phone_attempts.get(phone_hourly_key, 0)
            
            if phone_hourly_count >= self._max_verification_attempts_per_phone_hourly:
                lockout_until = phone_attempts.get('lockout_until', 0)
                if current_time < lockout_until:
                    return False, "Phone number temporarily locked due to too many failed attempts", int(lockout_until - current_time)
            
            # Check IP-based hourly limits
            ip_data = self._ip_verification_attempts.get(client_ip, {})
            ip_hourly_key = f"{current_hour.isoformat()}_attempts"
            ip_hourly_count = ip_data.get(ip_hourly_key, 0)
            
            if ip_hourly_count >= self._max_verification_attempts_per_ip_hourly:
                ip_lockout_until = ip_data.get('lockout_until', 0)
                if current_time < ip_lockout_until:
                    return False, "IP address temporarily locked due to too many failed attempts", int(ip_lockout_until - current_time)
            
            # Check if phone is currently locked
            phone_lockout_until = phone_attempts.get('lockout_until', 0)
            if current_time < phone_lockout_until:
                return False, "Phone number temporarily locked", int(phone_lockout_until - current_time)
            
            return True, "OK", 0
    
    def record_otp_sent(self, phone_number, client_ip):
        """
        Record that an OTP was sent, updating all rate limiting counters.
        
        Args:
            phone_number (str): Target phone number
            client_ip (str): Client IP address
        """
        with self._lock:
            current_time = time.time()
            today = datetime.now().date()
            
            # Update phone cooldown
            self._phone_cooldowns[phone_number] = current_time
            
            # Update IP cooldown
            self._ip_cooldowns[client_ip] = current_time
            
            # Update daily SMS count
            self._daily_sms_counts[phone_number][today] = \
                self._daily_sms_counts[phone_number].get(today, 0) + 1
            
            logger.info(f"OTP_RATE_LIMIT: Recorded send - Phone: {phone_number[-4:].rjust(4, '*')} "
                       f"IP: {client_ip} Daily count: {self._daily_sms_counts[phone_number][today]}")
    
    def record_verification_attempt(self, phone_number, client_ip, session_id, success=False):
        """
        Record a verification attempt and apply lockouts for failed attempts.
        
        Args:
            phone_number (str): Target phone number
            client_ip (str): Client IP address
            session_id (str): OTP session identifier
            success (bool): Whether the verification was successful
        """
        with self._lock:
            current_time = time.time()
            current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
            
            # Initialize session tracking if not exists
            if session_id not in self._session_verification_tracking:
                self._session_verification_tracking[session_id] = {
                    'phone': phone_number,
                    'attempts': 0,
                    'created_at': current_time
                }
            
            # Record session attempt
            session_data = self._session_verification_tracking[session_id]
            session_data['attempts'] += 1
            
            # Record phone-based attempts
            phone_attempts = self._verification_attempts[phone_number]
            phone_hourly_key = f"{current_hour.isoformat()}_attempts"
            phone_attempts[phone_hourly_key] = phone_attempts.get(phone_hourly_key, 0) + 1
            
            # Record IP-based attempts
            if client_ip not in self._ip_verification_attempts:
                self._ip_verification_attempts[client_ip] = {}
            ip_data = self._ip_verification_attempts[client_ip]
            ip_hourly_key = f"{current_hour.isoformat()}_attempts"
            ip_data[ip_hourly_key] = ip_data.get(ip_hourly_key, 0) + 1
            
            if success:
                # Clear lockouts on successful verification
                phone_attempts.pop('lockout_until', None)
                ip_data.pop('lockout_until', None)
                # Clear session tracking on success
                self._session_verification_tracking.pop(session_id, None)
                
                logger.info(f"OTP_VERIFY_SUCCESS: Phone: {phone_number[-4:].rjust(4, '*')} "
                           f"IP: {client_ip} Session: {session_id[:8]}")
            else:
                # Apply lockouts for failed attempts
                self._apply_verification_lockouts(phone_number, client_ip, session_data['attempts'], 
                                                 phone_attempts.get(phone_hourly_key, 0))
                
                logger.warning(f"OTP_VERIFY_FAILED: Phone: {phone_number[-4:].rjust(4, '*')} "
                              f"IP: {client_ip} Session: {session_id[:8]} "
                              f"SessionAttempts: {session_data['attempts']} "
                              f"HourlyAttempts: {phone_attempts.get(phone_hourly_key, 0)}")
    
    def _apply_verification_lockouts(self, phone_number, client_ip, session_attempts, hourly_attempts):
        """
        Apply exponential backoff lockouts based on failed verification attempts.
        
        Args:
            phone_number (str): Target phone number
            client_ip (str): Client IP address
            session_attempts (int): Number of attempts in current session
            hourly_attempts (int): Number of attempts in current hour
        """
        current_time = time.time()
        
        # Calculate lockout duration with exponential backoff
        lockout_seconds = min(
            self._verification_lockout_base_seconds * (2 ** (session_attempts - 3)),
            self._verification_lockout_max_seconds
        )
        
        # Apply phone lockout if session attempts exceed threshold
        if session_attempts >= self._max_verification_attempts_per_session:
            lockout_until = current_time + lockout_seconds
            self._verification_attempts[phone_number]['lockout_until'] = lockout_until
            
            logger.warning(f"OTP_PHONE_LOCKOUT: Phone: {phone_number[-4:].rjust(4, '*')} "
                          f"locked for {lockout_seconds}s after {session_attempts} session attempts")
        
        # Apply IP lockout if hourly attempts exceed threshold
        if hourly_attempts >= self._max_verification_attempts_per_ip_hourly:
            ip_lockout_seconds = min(lockout_seconds * 2, self._verification_lockout_max_seconds)
            ip_lockout_until = current_time + ip_lockout_seconds
            self._ip_verification_attempts[client_ip]['lockout_until'] = ip_lockout_until
            
            logger.warning(f"OTP_IP_LOCKOUT: IP: {client_ip} "
                          f"locked for {ip_lockout_seconds}s after {hourly_attempts} hourly attempts")
    
    def clear_session_verification(self, session_id):
        """
        Clear verification tracking for a specific session.
        
        Args:
            session_id (str): OTP session identifier to clear
        """
        with self._lock:
            self._session_verification_tracking.pop(session_id, None)
            logger.debug(f"OTP_SESSION_CLEARED: Session {session_id[:8]} verification tracking cleared")
    
    def _cleanup_expired_entries(self):
        """Remove expired entries to prevent memory leaks"""
        if time.time() - self._last_cleanup < self._cleanup_interval:
            return
        
        current_time = time.time()
        
        # Clean up phone cooldowns
        expired_phones = [
            phone for phone, timestamp in self._phone_cooldowns.items()
            if current_time - timestamp > self._phone_cooldown_seconds
        ]
        for phone in expired_phones:
            del self._phone_cooldowns[phone]
        
        # Clean up IP cooldowns
        expired_ips = [
            ip for ip, timestamp in self._ip_cooldowns.items()
            if current_time - timestamp > self._ip_cooldown_seconds
        ]
        for ip in expired_ips:
            del self._ip_cooldowns[ip]
        
        # Clean up old daily counts (keep last 7 days)
        cutoff_date = datetime.now().date() - timedelta(days=7)
        for phone in list(self._daily_sms_counts.keys()):
            expired_dates = [
                date for date in self._daily_sms_counts[phone]
                if date < cutoff_date
            ]
            for date in expired_dates:
                del self._daily_sms_counts[phone][date]
            
            # Remove empty phone entries
            if not self._daily_sms_counts[phone]:
                del self._daily_sms_counts[phone]
        
        # Clean up verification attempt tracking
        cutoff_hour = datetime.now() - timedelta(hours=2)  # Keep last 2 hours
        cutoff_timestamp = current_time - 7200  # 2 hours in seconds
        
        # Clean up phone verification attempts
        for phone in list(self._verification_attempts.keys()):
            phone_data = self._verification_attempts[phone]
            
            # Remove old hourly counters
            expired_keys = [
                key for key in phone_data.keys()
                if key.endswith('_attempts') and key < cutoff_hour.replace(minute=0, second=0, microsecond=0).isoformat()
            ]
            for key in expired_keys:
                del phone_data[key]
            
            # Remove expired lockouts
            if 'lockout_until' in phone_data and phone_data['lockout_until'] < current_time:
                del phone_data['lockout_until']
            
            # Remove empty phone entries
            if not phone_data:
                del self._verification_attempts[phone]
        
        # Clean up IP verification attempts
        for ip in list(self._ip_verification_attempts.keys()):
            ip_data = self._ip_verification_attempts[ip]
            
            # Remove old hourly counters
            expired_keys = [
                key for key in ip_data.keys()
                if key.endswith('_attempts') and key < cutoff_hour.replace(minute=0, second=0, microsecond=0).isoformat()
            ]
            for key in expired_keys:
                del ip_data[key]
            
            # Remove expired lockouts
            if 'lockout_until' in ip_data and ip_data['lockout_until'] < current_time:
                del ip_data['lockout_until']
            
            # Remove empty IP entries
            if not ip_data:
                del self._ip_verification_attempts[ip]
        
        # Clean up session verification tracking (remove sessions older than 1 hour)
        expired_sessions = [
            session_id for session_id, data in self._session_verification_tracking.items()
            if current_time - data.get('created_at', 0) > 3600
        ]
        for session_id in expired_sessions:
            del self._session_verification_tracking[session_id]
        
        self._last_cleanup = current_time
        
        cleanup_summary = []
        if expired_phones:
            cleanup_summary.append(f"{len(expired_phones)} phone cooldowns")
        if expired_ips:
            cleanup_summary.append(f"{len(expired_ips)} IP cooldowns")
        if expired_sessions:
            cleanup_summary.append(f"{len(expired_sessions)} verification sessions")
        
        if cleanup_summary:
            logger.debug(f"OTP_RATE_LIMIT: Cleanup completed - Removed {', '.join(cleanup_summary)}")
    
    def get_stats(self):
        """Get current rate limiter statistics for monitoring"""
        with self._lock:
            today = datetime.now().date()
            total_daily_sms = sum(
                counts.get(today, 0) 
                for counts in self._daily_sms_counts.values()
            )
            
            # Count active verification lockouts
            active_phone_lockouts = sum(
                1 for data in self._verification_attempts.values()
                if 'lockout_until' in data and data['lockout_until'] > time.time()
            )
            active_ip_lockouts = sum(
                1 for data in self._ip_verification_attempts.values()
                if 'lockout_until' in data and data['lockout_until'] > time.time()
            )
            
            return {
                'active_phone_cooldowns': len(self._phone_cooldowns),
                'active_ip_cooldowns': len(self._ip_cooldowns),
                'total_phones_with_daily_counts': len(self._daily_sms_counts),
                'total_sms_sent_today': total_daily_sms,
                'max_sms_per_day': self._max_sms_per_day,
                'phone_cooldown_seconds': self._phone_cooldown_seconds,
                'ip_cooldown_seconds': self._ip_cooldown_seconds,
                'active_verification_sessions': len(self._session_verification_tracking),
                'active_phone_lockouts': active_phone_lockouts,
                'active_ip_lockouts': active_ip_lockouts,
                'max_verification_attempts_per_session': self._max_verification_attempts_per_session,
                'max_verification_attempts_per_phone_hourly': self._max_verification_attempts_per_phone_hourly,
                'max_verification_attempts_per_ip_hourly': self._max_verification_attempts_per_ip_hourly
            }

# Global rate limiter instance
otp_rate_limiter = OTPRateLimiter()