# API Reference - MicroStrategy Extractor

Referência completa da API do MicroStrategy HTML Documentation Extractor.

## 📦 Main Package

### Import

```python
import sys
sys.path.insert(0, 'src')  # If not installed as package

from microstrategy_extractor import Config, HTMLSections, ExtractorError
```

---

## 🔧 Configuration (`config.settings`)

### Config Class

```python
from microstrategy_extractor.config.settings import Config

# Create from environment
config = Config.from_env()

# Create from CLI args
config = Config.from_args(args)

# Create manually
config = Config(
    base_path=Path("RAW_DATA/..."),
    output_json_path=Path("output.json"),
    output_csv_dir=Path("output_csv"),
    cache_enabled=True,
    cache_size_limit=1000,
    log_level="INFO",
    verbose=False
)

# Validate
errors = config.validate()  # Returns list of error strings

# Get HTML file paths
path = config.get_html_file_path('metrica')  # Path to Métrica.html
```

---

## 🔍 Extractors (`extractors`)

### ReportExtractor

Main extraction class.

```python
from microstrategy_extractor.extractors import ReportExtractor

extractor = ReportExtractor(
    base_path: Path,
    config: Optional[Config] = None
)

# Extract specific report by name
relatorios = extractor.extract_report(report_name: str) -> List[Relatorio]

# Extract by ID
relatorio = extractor.extract_report_by_id(report_id: str) -> Optional[Relatorio]

# Extract all reports
all_relatorios = extractor.extract_all_reports() -> List[Relatorio]

# Cache management
extractor.clear_cache(namespace: Optional[str] = None)
stats = extractor.get_cache_stats() -> dict
```

### ParallelReportExtractor

Parallel processing support.

```python
from microstrategy_extractor.extractors import ParallelReportExtractor

parallel = ParallelReportExtractor(
    base_path: Path,
    max_workers: int = 4
)

relatorios = parallel.extract_all_reports(parallel: bool = True) -> List[Relatorio]
```

### Convenience Function

```python
from microstrategy_extractor.extractors import extract_reports_parallel

relatorios = extract_reports_parallel(
    base_path: Path,
    max_workers: int = 4
) -> List[Relatorio]
```

---

## 📤 Exporters (`exporters`)

### CSVExporter

Export to normalized CSV files.

```python
from microstrategy_extractor.exporters import CSVExporter

exporter = CSVExporter(output_dir: Path)

exporter.export(relatorios: List[Relatorio])
# Generates 16 CSV files in output_dir
```

---

## ✓ Validators (`validators`)

### DataValidator

Validate extracted data with Pydantic.

```python
from microstrategy_extractor.validators import DataValidator, ValidationResult

validator = DataValidator(strict: bool = False)

# Validate single report
result = validator.validate_relatorio(relatorio: Relatorio) -> ValidationResult

# Validate all
overall = validator.validate_extraction(relatorios: List[Relatorio]) -> ValidationResult

# Check results
if overall.valid:
    print("All valid")
else:
    for error in overall.errors:
        print(error)
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]
    validated_count: int
```

---

## 💾 Cache (`cache`)

### MemoryCache

LRU cache with namespace support.

```python
from microstrategy_extractor.cache import MemoryCache

cache = MemoryCache(max_size: int = 1000)

# Basic operations
cache.set(key: str, value: Any, namespace: str = "default")
value = cache.get(key: str, namespace: str = "default") -> Optional[Any]
exists = cache.has(key: str, namespace: str = "default") -> bool

# Lazy computation
value = cache.get_or_compute(
    key: str,
    compute_fn: callable,
    namespace: str = "default"
) -> Any

# Management
cache.clear(namespace: Optional[str] = None)
size = cache.get_size(namespace: Optional[str] = None) -> int
stats = cache.get_stats() -> Dict[str, int]
```

---

## 📝 Parsers (`parsers`)

### Report Parser

```python
from microstrategy_extractor.parsers.report_parser import (
    extract_report_links,
    find_report_by_name,
    find_report_by_id,
    extract_datasets_from_report,
    resolve_dataset_link,
    is_report_dataset,
    extract_graphic_type
)
```

### Link Resolver

```python
from microstrategy_extractor.parsers.link_resolver import LinkResolver

resolver = LinkResolver(index_path: Path, object_type: str)

# Find by ID
result = resolver.find_by_id(object_id: str) -> Optional[LinkResult]

# Find by name
result = resolver.find_by_name(
    object_name: str,
    normalize_fn: Optional[Callable] = None
) -> Optional[LinkResult]

# Try both
result = resolver.find_link(
    object_id: Optional[str] = None,
    object_name: Optional[str] = None
) -> Optional[LinkResult]

# Get all
all_results = resolver.find_all() -> List[LinkResult]
```

---

## 🛠️ Utils (`utils`)

### Logger

```python
from microstrategy_extractor.utils.logger import setup_logging, get_logger

# Global setup
setup_logging(level: str = "INFO")

# Get logger
logger = get_logger(name: str, context: Optional[Dict] = None)

# Use
logger.info("Message", extra_key=value)
logger.error("Error message")
logger.debug("Debug info")
```

### Text Normalizer

```python
from microstrategy_extractor.utils.text_normalizer import TextNormalizer

# Remove accents, uppercase
norm = TextNormalizer.for_comparison(text: str) -> str

# Lowercase, no accents
match = TextNormalizer.normalize_for_matching(text: str) -> str

# Fix common issues
fixed = TextNormalizer.fix_common_accents(text: str) -> str

# Compare
equal = TextNormalizer.compare_texts(
    text1: str,
    text2: str,
    case_sensitive: bool = False,
    accent_sensitive: bool = False
) -> bool

# Find best match
best = TextNormalizer.find_best_match(
    target: str,
    candidates: List[str],
    threshold: float = 0.8
) -> Optional[str]
```

---

## 🗄️ Database (`db`)

### SchemaLoader

Load and manage database schema configuration.

```python
from microstrategy_extractor.db import SchemaLoader
from pathlib import Path

schema = SchemaLoader(Path("config/db_schema.yaml"))
schema.load()

# Get information
entities = schema.get_entities() -> List[Table]
relationships = schema.get_relationships() -> List[Table]
import_order = schema.get_import_order() -> List[str]

# Generate SQL
sql = schema.generate_create_sql(dialect: str = 'postgresql') -> str

# Get CSV mapping
mapping = schema.get_csv_file_mapping() -> Dict[str, str]
```

---

## 🎯 Core Components (`core`)

### Constants

```python
from microstrategy_extractor.core.constants import (
    HTMLSections,      # DEFINICAO, EXPRESSOES, etc.
    HTMLClasses,       # MAINBODY, SECTIONHEADER
    ApplicationObjects, # CUBO_INTELIGENTE, REPORT, etc.
    MetricTypes,       # SIMPLES, COMPOSTO
    HTMLFiles,         # File names
    RegexPatterns,     # Regex patterns
    CSVFiles,          # CSV file names
    TableHeaders,      # Table headers
)
```

### Exceptions

```python
from microstrategy_extractor.core.exceptions import (
    ExtractorError,         # Base exception
    ParsingError,           # HTML parsing errors
    MissingFileError,       # File not found
    CircularReferenceError, # Metric circular refs
    LinkResolutionError,    # Link not resolved
    ConfigurationError,     # Config issues
    ExportError,            # Export failures
    ValidationError,        # Validation errors
)
```

### Models

```python
from microstrategy_extractor.core.models import (
    Relatorio,    # Report
    DataSet,      # Dataset
    Atributo,     # Attribute
    Formulario,   # Form
    Metrica,      # Metric
    Function,     # Aggregation function
    Fact,         # Fact
    LogicTable,   # Source table
)
```

### Types

```python
from microstrategy_extractor.core.types import (
    LinkResult,         # Link resolution result
    ReportInfo,         # Report information
    DatasetInfo,        # Dataset information
    MetricDefinition,   # Metric definition
    # ... and more
)
```

---

## 🎨 Complete Example

```python
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from microstrategy_extractor.config.settings import Config
from microstrategy_extractor.utils.logger import setup_logging, get_logger
from microstrategy_extractor.extractors import ReportExtractor
from microstrategy_extractor.exporters import CSVExporter
from microstrategy_extractor.validators import DataValidator
from microstrategy_extractor.core.exceptions import ExportError

# 1. Configuration
config = Config(
    base_path=Path("RAW_DATA/04 - Relatórios Gerenciais"),
    output_csv_dir=Path("output_csv"),
    log_level="INFO",
    cache_size_limit=1000
)

# Validate config
errors = config.validate()
if errors:
    for error in errors:
        print(f"Config error: {error}")
    sys.exit(1)

# 2. Setup logging
setup_logging(config.log_level)
logger = get_logger(__name__)

# 3. Extract
logger.info("Starting extraction")
extractor = ReportExtractor(config.base_path, config)
relatorios = extractor.extract_all_reports()
logger.info(f"Extracted {len(relatorios)} reports")

# 4. Validate
validator = DataValidator()
result = validator.validate_extraction(relatorios)

if result.valid:
    logger.info("Validation passed")
else:
    logger.warning(f"Found {len(result.errors)} errors")

# 5. Export
try:
    exporter = CSVExporter(config.output_csv_dir)
    exporter.export(relatorios)
    logger.info("Export complete")
except ExportError as e:
    logger.error(f"Export failed: {e}")
    sys.exit(1)

# 6. Cache stats
stats = extractor.get_cache_stats()
logger.info(f"Cache stats: {stats}")
```

---

## 📚 More Information

- **Getting Started**: `docs/getting-started.md`
- **Advanced Features**: `docs/advanced.md`
- **Original README**: `MAIN.md` (if exists)

---

**Version**: 2.0.0  
**Python**: >=3.8

