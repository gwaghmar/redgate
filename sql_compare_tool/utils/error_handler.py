"""Enhanced error handling and recovery utilities."""
from __future__ import annotations

import functools
import traceback
from typing import Callable, Any, Optional, Type
from utils.logger import get_logger

logger = get_logger(__name__)


class ApplicationError(Exception):
    """Base exception for application-specific errors."""
    
    def __init__(self, message: str, details: Optional[str] = None, recoverable: bool = False):
        super().__init__(message)
        self.message = message
        self.details = details
        self.recoverable = recoverable
    
    def __str__(self):
        if self.details:
            return f"{self.message}\n\nDetails: {self.details}"
        return self.message


class ConnectionError(ApplicationError):
    """Database connection related errors."""
    pass


class QueryError(ApplicationError):
    """Query execution errors."""
    pass


class ValidationError(ApplicationError):
    """Input validation errors."""
    pass


class LicenseError(ApplicationError):
    """License validation errors."""
    pass


class ExportError(ApplicationError):
    """Export/report generation errors."""
    pass


def handle_errors(
    error_message: str = "An error occurred",
    default_return: Any = None,
    reraise: bool = False,
    error_types: tuple[Type[Exception], ...] = (Exception,),
    log_traceback: bool = True
):
    """
    Decorator for consistent error handling across functions.
    
    Args:
        error_message: Custom error message prefix
        default_return: Value to return on error (if not reraising)
        reraise: Whether to reraise the exception after logging
        error_types: Tuple of exception types to catch
        log_traceback: Whether to log full traceback
    
    Example:
        @handle_errors("Failed to extract metadata", default_return={})
        def extract_metadata(conn):
            # ... extraction logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_types as e:
                error_msg = f"{error_message}: {str(e)}"
                
                if log_traceback:
                    logger.error(f"{error_msg}\n{traceback.format_exc()}")
                else:
                    logger.error(error_msg)
                
                if reraise:
                    if isinstance(e, ApplicationError):
                        raise
                    # Wrap in ApplicationError if needed
                    raise ApplicationError(error_msg, details=str(e), recoverable=False) from e
                
                return default_return
        
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    *args,
    error_message: str = "Operation failed",
    default_return: Any = None,
    **kwargs
) -> tuple[bool, Any, Optional[str]]:
    """
    Safely execute a function with error handling.
    
    Returns:
        (success, result, error_message)
    
    Example:
        success, result, error = safe_execute(
            database.execute_query,
            "SELECT * FROM tables",
            error_message="Query failed"
        )
        if success:
            process(result)
        else:
            show_error(error)
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        error_msg = f"{error_message}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return False, default_return, error_msg


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    exponential_backoff: bool = True,
    exceptions: tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        exponential_backoff: Whether to use exponential backoff
        exceptions: Tuple of exceptions to catch and retry on
    
    Example:
        @retry_on_failure(max_attempts=3, delay=2.0)
        def connect_to_database():
            # ... connection logic
    """
    import time
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}"
                    )
                    
                    if attempt < max_attempts:
                        logger.info(f"Retrying in {current_delay:.1f} seconds...")
                        time.sleep(current_delay)
                        
                        if exponential_backoff:
                            current_delay *= 2
            
            # All attempts failed
            error_msg = f"Failed after {max_attempts} attempts: {last_exception}"
            logger.error(error_msg)
            raise ApplicationError(
                f"Operation failed after {max_attempts} attempts",
                details=str(last_exception),
                recoverable=True
            ) from last_exception
        
        return wrapper
    return decorator


def validate_input(
    condition: bool,
    error_message: str,
    field_name: Optional[str] = None
):
    """
    Validate input and raise ValidationError if condition is False.
    
    Args:
        condition: Condition to validate
        error_message: Error message if validation fails
        field_name: Optional field name for context
    
    Example:
        validate_input(
            len(server_name) > 0,
            "Server name cannot be empty",
            field_name="server"
        )
    
    Raises:
        ValidationError: If condition is False
    """
    if not condition:
        full_message = f"{field_name}: {error_message}" if field_name else error_message
        logger.warning(f"Validation failed: {full_message}")
        raise ValidationError(full_message, recoverable=True)


def format_error_for_user(error: Exception) -> str:
    """
    Format an exception into a user-friendly message.
    
    Args:
        error: The exception to format
    
    Returns:
        User-friendly error message
    """
    if isinstance(error, ApplicationError):
        return str(error)
    
    # Handle common exceptions with user-friendly messages
    error_mappings = {
        "pyodbc.Error": "Database connection error. Please check your connection settings.",
        "pyodbc.InterfaceError": "Database interface error. The connection may be closed.",
        "pyodbc.DatabaseError": "Database error occurred while executing the query.",
        "FileNotFoundError": "The specified file could not be found.",
        "PermissionError": "Permission denied. You may not have access to this resource.",
        "json.JSONDecodeError": "Invalid JSON format in file or response.",
        "KeyError": "Missing required data field.",
        "ValueError": "Invalid value provided.",
    }
    
    error_type = type(error).__name__
    module_type = f"{error.__class__.__module__}.{error_type}"
    
    # Check for specific error types
    for pattern, message in error_mappings.items():
        if pattern in module_type or pattern in error_type:
            return f"{message}\n\nTechnical details: {str(error)}"
    
    # Generic error message
    return f"An unexpected error occurred: {str(error)}"


class ErrorContext:
    """Context manager for consistent error handling in code blocks."""
    
    def __init__(
        self,
        operation_name: str,
        suppress: bool = False,
        callback: Optional[Callable[[Exception], None]] = None
    ):
        """
        Args:
            operation_name: Name of the operation for logging
            suppress: Whether to suppress exceptions (return None instead)
            callback: Optional callback function to call on error
        """
        self.operation_name = operation_name
        self.suppress = suppress
        self.callback = callback
        self.exception = None
    
    def __enter__(self):
        logger.debug(f"Starting operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.exception = exc_val
            error_msg = f"Error in {self.operation_name}: {exc_val}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            if self.callback:
                try:
                    self.callback(exc_val)
                except Exception as callback_error:
                    logger.error(f"Error in error callback: {callback_error}")
            
            if self.suppress:
                return True  # Suppress exception
        else:
            logger.debug(f"Completed operation: {self.operation_name}")
        
        return False  # Propagate exception if not suppressed


# Convenience function for common error scenarios
def get_user_friendly_db_error(error: Exception) -> str:
    """
    Convert database errors to user-friendly messages.
    
    Args:
        error: Database error exception
    
    Returns:
        User-friendly error message with suggestions
    """
    error_str = str(error).lower()
    
    if "login failed" in error_str or "authentication" in error_str:
        return (
            "Authentication failed.\n\n"
            "Please check:\n"
            "• Username and password are correct\n"
            "• Account has proper permissions\n"
            "• Authentication method is correct"
        )
    
    if "connection refused" in error_str or "timeout" in error_str:
        return (
            "Could not connect to server.\n\n"
            "Please check:\n"
            "• Server name is correct\n"
            "• Server is online and accessible\n"
            "• Firewall allows connections\n"
            "• Network connection is stable"
        )
    
    if "database" in error_str and ("not exist" in error_str or "cannot open" in error_str):
        return (
            "Database not found or inaccessible.\n\n"
            "Please check:\n"
            "• Database name is spelled correctly\n"
            "• Database exists on the server\n"
            "• You have permission to access it"
        )
    
    if "driver" in error_str or "odbc" in error_str:
        return (
            "ODBC driver error.\n\n"
            "Please ensure:\n"
            "• ODBC Driver 18 for SQL Server is installed\n"
            "• Driver version is compatible"
        )
    
    # Default database error message
    return f"Database error occurred.\n\nDetails: {error}"
