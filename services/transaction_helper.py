"""
Transaction Helper Service

Provides atomic database operations with proper rollback handling,
retry logic, and centralized error management for all services.
"""

from functools import wraps
from typing import Callable, Any, Optional
import logging
from app import db
import time

logger = logging.getLogger(__name__)

class TransactionHelper:
    """Helper class for managing database transactions safely"""
    
    @staticmethod
    def with_transaction(func: Callable) -> Callable:
        """
        Decorator that wraps a function in a database transaction.
        Automatically handles commit/rollback and provides retry logic for connection issues.
        
        Usage:
            @TransactionHelper.with_transaction
            def update_driver_status(driver_id, status):
                # Your database operations here
                pass
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    
                    # Handle service result pattern: (success: bool, error_msg: str, ...)
                    if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[0], bool):
                        if result[0]:  # success = True
                            db.session.commit()
                            return result
                        else:  # success = False
                            db.session.rollback()
                            return result
                    else:
                        # Non-service pattern, commit normally
                        db.session.commit()
                        return result
                        
                except Exception as e:
                    db.session.rollback()
                    
                    # Log the error with attempt information
                    logger.error(f"Transaction error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    
                    if attempt < max_retries - 1:
                        # Wait before retry to handle temporary connection issues
                        time.sleep(0.5)
                        continue
                    else:
                        # Final attempt failed, re-raise the exception
                        logger.error(f"Transaction failed after {max_retries} attempts: {str(e)}")
                        raise
            return None
        return wrapper
    
    @staticmethod
    def execute_with_rollback(operation: Callable, *args, **kwargs) -> tuple[bool, Optional[Any], Optional[str]]:
        """
        Execute a database operation with automatic rollback on failure.
        
        Args:
            operation: Function to execute
            *args, **kwargs: Arguments to pass to the operation
            
        Returns:
            tuple: (success: bool, result: Any, error_message: str)
        """
        try:
            result = operation(*args, **kwargs)
            db.session.commit()
            return True, result, None
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            logger.error(f"Database operation failed: {error_msg}")
            return False, None, error_msg
    
    @staticmethod
    def batch_operation(operations: list, batch_size: int = 100) -> tuple[bool, list, Optional[str]]:
        """
        Execute multiple operations in batches with transaction management.
        
        Args:
            operations: List of (operation_func, args, kwargs) tuples
            batch_size: Number of operations per batch
            
        Returns:
            tuple: (success: bool, results: list, error_message: str)
        """
        results = []
        
        try:
            for i in range(0, len(operations), batch_size):
                batch = operations[i:i + batch_size]
                
                for operation_func, args, kwargs in batch:
                    result = operation_func(*args, **kwargs)
                    results.append(result)
                
                # Commit each batch
                db.session.commit()
                
            return True, results, None
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Batch operation failed at item {len(results)}: {str(e)}"
            logger.error(error_msg)
            return False, results, error_msg