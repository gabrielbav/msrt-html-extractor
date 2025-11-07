"""Custom exception hierarchy for the MicroStrategy extractor."""

from typing import Optional, List
from pathlib import Path


class ExtractorError(Exception):
    """Base exception for all extraction errors."""
    pass


class ParsingError(ExtractorError):
    """HTML parsing failed or produced unexpected results."""
    
    def __init__(self, message: str, file_path: Optional[Path] = None, 
                 section: Optional[str] = None):
        """
        Initialize parsing error.
        
        Args:
            message: Error message
            file_path: Path to file being parsed
            section: Section name where error occurred
        """
        self.file_path = file_path
        self.section = section
        
        full_message = message
        if file_path:
            full_message = f"{message} (file: {file_path})"
        if section:
            full_message = f"{full_message} (section: {section})"
        
        super().__init__(full_message)


class MissingFileError(ExtractorError):
    """Required file not found."""
    
    def __init__(self, file_path: Path, context: str = ""):
        """
        Initialize missing file error.
        
        Args:
            file_path: Path to missing file
            context: Additional context about why file is needed
        """
        self.file_path = file_path
        self.context = context
        
        message = f"File not found: {file_path}"
        if context:
            message = f"{message}. {context}"
        
        super().__init__(message)


class MissingSectionError(ParsingError):
    """Expected HTML section not found."""
    
    def __init__(self, section_name: str, file_path: Optional[Path] = None, 
                 object_name: Optional[str] = None):
        """
        Initialize missing section error.
        
        Args:
            section_name: Name of missing section
            file_path: Path to file
            object_name: Name of object being parsed
        """
        self.section_name = section_name
        self.object_name = object_name
        
        message = f"Section '{section_name}' not found"
        if object_name:
            message = f"{message} for object '{object_name}'"
        
        super().__init__(message, file_path, section_name)


class CircularReferenceError(ExtractorError):
    """Circular reference detected in metrics."""
    
    def __init__(self, metric_id: str, chain: Optional[List[str]] = None):
        """
        Initialize circular reference error.
        
        Args:
            metric_id: ID of metric causing circular reference
            chain: List of metric IDs in the reference chain
        """
        self.metric_id = metric_id
        self.chain = chain or []
        
        message = f"Circular reference detected for metric {metric_id}"
        if chain:
            chain_str = " -> ".join(chain)
            message = f"{message} in chain: {chain_str}"
        
        super().__init__(message)


class LinkResolutionError(ExtractorError):
    """Failed to resolve object link."""
    
    def __init__(self, object_type: str, object_id: Optional[str] = None, 
                 object_name: Optional[str] = None, index_file: Optional[Path] = None):
        """
        Initialize link resolution error.
        
        Args:
            object_type: Type of object (e.g., "Metric", "Attribute", "Fact")
            object_id: ID of object to resolve
            object_name: Name of object to resolve
            index_file: Path to index file used for resolution
        """
        self.object_type = object_type
        self.object_id = object_id
        self.object_name = object_name
        self.index_file = index_file
        
        identifier = object_id if object_id else object_name
        message = f"Failed to resolve {object_type} link: {identifier}"
        if index_file:
            message = f"{message} (index: {index_file})"
        
        super().__init__(message)


class InvalidDataError(ExtractorError):
    """Extracted data is invalid or incomplete."""
    
    def __init__(self, message: str, data_type: Optional[str] = None, 
                 object_id: Optional[str] = None):
        """
        Initialize invalid data error.
        
        Args:
            message: Error message
            data_type: Type of data that is invalid
            object_id: ID of object with invalid data
        """
        self.data_type = data_type
        self.object_id = object_id
        
        full_message = message
        if data_type:
            full_message = f"{data_type}: {message}"
        if object_id:
            full_message = f"{full_message} (ID: {object_id})"
        
        super().__init__(full_message)


class ConfigurationError(ExtractorError):
    """Configuration is invalid or incomplete."""
    
    def __init__(self, message: str, setting: Optional[str] = None):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            setting: Name of problematic setting
        """
        self.setting = setting
        
        full_message = message
        if setting:
            full_message = f"Configuration error for '{setting}': {message}"
        
        super().__init__(full_message)


class CacheError(ExtractorError):
    """Cache operation failed."""
    
    def __init__(self, message: str, operation: Optional[str] = None, 
                 key: Optional[str] = None):
        """
        Initialize cache error.
        
        Args:
            message: Error message
            operation: Cache operation that failed (e.g., "get", "set")
            key: Cache key involved
        """
        self.operation = operation
        self.key = key
        
        full_message = message
        if operation:
            full_message = f"Cache {operation} failed: {message}"
        if key:
            full_message = f"{full_message} (key: {key})"
        
        super().__init__(full_message)


class ExportError(ExtractorError):
    """Export operation failed."""
    
    def __init__(self, message: str, output_path: Optional[Path] = None, 
                 format_type: Optional[str] = None):
        """
        Initialize export error.
        
        Args:
            message: Error message
            output_path: Path where export was attempted
            format_type: Format being exported (e.g., "JSON", "CSV")
        """
        self.output_path = output_path
        self.format_type = format_type
        
        full_message = message
        if format_type:
            full_message = f"{format_type} export failed: {message}"
        if output_path:
            full_message = f"{full_message} (path: {output_path})"
        
        super().__init__(full_message)


class ValidationError(ExtractorError):
    """Data validation failed."""
    
    def __init__(self, message: str, object_type: Optional[str] = None, 
                 object_id: Optional[str] = None, errors: Optional[List[str]] = None):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            object_type: Type of object that failed validation
            object_id: ID of object that failed validation
            errors: List of specific validation errors
        """
        self.object_type = object_type
        self.object_id = object_id
        self.errors = errors or []
        
        full_message = message
        if object_type:
            full_message = f"{object_type} validation failed: {message}"
        if object_id:
            full_message = f"{full_message} (ID: {object_id})"
        if errors:
            error_list = "\n  - ".join(errors)
            full_message = f"{full_message}\n  Errors:\n  - {error_list}"
        
        super().__init__(full_message)

