"""Legacy code - deprecated, use new extractors/ and parsers/ instead.

⚠️ DEPRECATED: This module contains the old implementation and will be removed in version 3.0.0

Please migrate to:
- microstrategy_extractor.extractors for extraction logic
- microstrategy_extractor.parsers for HTML parsing
- microstrategy_extractor.exporters for data export
"""

import warnings

warnings.warn(
    "Legacy modules are deprecated and will be removed in version 3.0.0. "
    "Please migrate to microstrategy_extractor.extractors and parsers.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['extractor', 'html_parser', 'output', 'json_to_csv']

