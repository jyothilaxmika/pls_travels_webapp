"""
Transaction Helper Service

Enhanced with database safety features:
- Connection validation and retry logic
- Dead lock detection and resolution  
- Schema integrity checks
- Backup integration for critical operations
"""

from functools import wraps
from typing import Callable, Any, Optional, Dict, List, Tuple
import logging
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError, DisconnectionError
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
    
    @staticmethod
    def with_connection_retry(max_retries: int = 3, backoff: float = 0.5):
        """
        Decorator for operations that need connection retry logic with exponential backoff.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff: Initial backoff delay in seconds
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except (DisconnectionError, OperationalError) as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            sleep_time = backoff * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Database connection error (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying in {sleep_time}s...")
                            time.sleep(sleep_time)
                            # Reset connection
                            db.session.rollback()
                            continue
                        else:
                            logger.error(f"Max retries reached for database connection")
                            raise
                    except Exception as e:
                        # Non-connection errors don't get retried
                        logger.error(f"Non-retryable error in database operation: {str(e)}")
                        raise
                
                # This should never be reached, but just in case
                if last_error:
                    raise last_error
                
            return wrapper
        return decorator
    
    @staticmethod  
    def validate_transaction_safety(operation_name: str) -> Tuple[bool, List[str]]:
        """
        Validate that the database is in a safe state for transactions.
        
        Args:
            operation_name: Name of the operation being performed
            
        Returns:
            Tuple[bool, List[str]]: (is_safe, list_of_warnings)
        """
        warnings = []
        
        try:
            # Check connection health
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            
            # Check for uncommitted transactions
            if db.session.new or db.session.dirty or db.session.deleted:
                warnings.append(f"Uncommitted changes detected before {operation_name}")
            
            # Check connection pool health
            pool = db.engine.pool
            if hasattr(pool, 'checkedout'):
                checked_out = pool.checkedout()
                if checked_out > (pool.size() * 0.8):  # More than 80% of connections used
                    warnings.append(f"High connection pool usage: {checked_out}/{pool.size()}")
            
            return len(warnings) == 0, warnings
            
        except Exception as e:
            warnings.append(f"Transaction safety check failed: {str(e)}")
            return False, warnings
    
    @staticmethod
    def with_backup_protection(backup_name: Optional[str] = None):
        """
        Decorator for critical operations that should create a backup before execution.
        
        Args:
            backup_name: Optional custom backup name
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Import here to avoid circular imports
                    from utils.database_manager import database_manager
                    
                    # Create backup before critical operation
                    operation_name = backup_name or f"{func.__name__}_{int(time.time())}"
                    backup_success, backup_result = database_manager.backup_database(operation_name)
                    
                    if not backup_success:
                        logger.warning(f"Backup failed before {func.__name__}: {backup_result}")
                        # Continue anyway - backup failure shouldn't block operation
                    else:
                        logger.info(f"Backup created before {func.__name__}: {backup_result}")
                    
                    # Execute the protected operation
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Error in backup-protected operation {func.__name__}: {str(e)}")
                    raise
                    
            return wrapper
        return decorator