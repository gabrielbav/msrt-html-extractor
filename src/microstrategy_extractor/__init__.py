"""MicroStrategy HTML Documentation Extractor.

A comprehensive tool for extracting report data models from MicroStrategy HTML documentation.
"""

__version__ = "2.0.0"
__author__ = "MicroStrategy Extractor Team"

# Re-export commonly used classes and functions for convenience
from microstrategy_extractor.core.constants import (
    HTMLSections, HTMLClasses, ApplicationObjects, MetricTypes,
    HTMLFiles, TableHeaders, RegexPatterns, CSVFiles
)
from microstrategy_extractor.core.exceptions import (
    ExtractorError, ParsingError, MissingFileError, CircularReferenceError,
    LinkResolutionError, ConfigurationError, ExportError, ValidationError
)
from microstrategy_extractor.config.settings import Config

__all__ = [
    # Version
    '__version__',
    # Config
    'Config',
    # Constants
    'HTMLSections', 'HTMLClasses', 'ApplicationObjects', 'MetricTypes',
    'HTMLFiles', 'TableHeaders', 'RegexPatterns', 'CSVFiles',
    # Exceptions
    'ExtractorError', 'ParsingError', 'MissingFileError', 'CircularReferenceError',
    'LinkResolutionError', 'ConfigurationError', 'ExportError', 'ValidationError',
]

