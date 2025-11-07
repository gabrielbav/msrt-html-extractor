"""Structured logging utilities for the MicroStrategy extractor."""

import logging
import sys
from typing import Optional, Dict, Any
from microstrategy_extractor.core.constants import LogLevels


class StructuredLogger:
    """Factory for creating structured loggers with context."""
    
    _initialized = False
    _loggers: Dict[str, logging.Logger] = {}
    
    @classmethod
    def setup_logging(cls, level: str = LogLevels.INFO, 
                     format_string: Optional[str] = None,
                     date_format: Optional[str] = None):
        """
        Setup global logging configuration.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_string: Custom format string for log messages
            date_format: Custom date format string
        """
        if cls._initialized:
            return
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        if format_string is None:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        if date_format is None:
            date_format = '%Y-%m-%d %H:%M:%S'
        
        logging.basicConfig(
            level=log_level,
            format=format_string,
            datefmt=date_format,
            stream=sys.stdout
        )
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str, context: Optional[Dict[str, Any]] = None) -> 'ContextLogger':
        """
        Get or create a logger with optional context.
        
        Args:
            name: Logger name (typically __name__ of the module)
            context: Optional context dictionary to include in all log messages
            
        Returns:
            ContextLogger instance
        """
        if name not in cls._loggers:
            base_logger = logging.getLogger(name)
            cls._loggers[name] = base_logger
        
        return ContextLogger(cls._loggers[name], context or {})
    
    @classmethod
    def reset(cls):
        """Reset logging configuration (mainly for testing)."""
        cls._initialized = False
        cls._loggers.clear()
        logging.root.handlers.clear()


class ContextLogger:
    """Logger wrapper that includes context in all log messages."""
    
    def __init__(self, logger: logging.Logger, context: Dict[str, Any]):
        """
        Initialize context logger.
        
        Args:
            logger: Base logging.Logger instance
            context: Context dictionary
        """
        self.logger = logger
        self.context = context
    
    def _format_message(self, msg: str) -> str:
        """
        Format message with context.
        
        Args:
            msg: Original message
            
        Returns:
            Message with context appended
        """
        if not self.context:
            return msg
        
        context_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
        return f"{msg} [{context_str}]"
    
    def with_context(self, **kwargs) -> 'ContextLogger':
        """
        Create a new logger with additional context.
        
        Args:
            **kwargs: Additional context key-value pairs
            
        Returns:
            New ContextLogger with merged context
        """
        new_context = {**self.context, **kwargs}
        return ContextLogger(self.logger, new_context)
    
    def debug(self, msg: str, *args, **kwargs):
        """Log debug message with context."""
        self.logger.debug(self._format_message(msg), *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """Log info message with context."""
        self.logger.info(self._format_message(msg), *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Log warning message with context."""
        self.logger.warning(self._format_message(msg), *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Log error message with context."""
        self.logger.error(self._format_message(msg), *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """Log critical message with context."""
        self.logger.critical(self._format_message(msg), *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        """Log exception with context."""
        self.logger.exception(self._format_message(msg), *args, **kwargs)


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> ContextLogger:
    """
    Convenience function to get a logger.
    
    Args:
        name: Logger name (typically __name__)
        context: Optional context dictionary
        
    Returns:
        ContextLogger instance
    """
    return StructuredLogger.get_logger(name, context)


def setup_logging(level: str = LogLevels.INFO, 
                 format_string: Optional[str] = None,
                 date_format: Optional[str] = None):
    """
    Convenience function to setup logging.
    
    Args:
        level: Logging level
        format_string: Custom format string
        date_format: Custom date format
    """
    StructuredLogger.setup_logging(level, format_string, date_format)

