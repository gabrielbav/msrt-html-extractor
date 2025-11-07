# Advanced Features - MicroStrategy Extractor

Guia de features avançados e casos de uso complexos.

## 📋 Índice

- [Parallel Processing](#parallel-processing)
- [Custom Cache Strategies](#custom-cache-strategies)
- [Data Validation](#data-validation)
- [Custom Parsers](#custom-parsers)
- [Database Integration](#database-integration)
- [Performance Tuning](#performance-tuning)

---

## ⚡ Parallel Processing

### Basic Parallel Extraction

```python
from microstrategy_extractor.extractors import extract_reports_parallel

# Simple parallel extraction
relatorios = extract_reports_parallel(
    base_path,
    max_workers=4  # Number of CPU cores
)
```

### Advanced Parallel Control

```python
from microstrategy_extractor.extractors import ParallelReportExtractor

parallel_extractor = ParallelReportExtractor(base_path, max_workers=4)

# Control parallelization
relatorios = parallel_extractor.extract_all_reports(
    parallel=True  # Set to False for sequential
)
```

### Performance Comparison

| Reports | Sequential | Parallel (4 cores) | Speedup |
|---------|-----------|-------------------|---------|
| 10 | ~2 min | ~1 min | 2x |
| 50 | ~7 min | ~2.5 min | 2.8x |
| 100 | ~15 min | ~4-6 min | 3-4x |

**Tip**: Parallel processing é mais eficiente para 10+ relatórios.

---

## 💾 Custom Cache Strategies

### Custom Cache Size

```python
from microstrategy_extractor.cache import MemoryCache
from microstrategy_extractor.extractors import ReportExtractor

# Large cache for big datasets
cache = MemoryCache(max_size=5000)
extractor = ReportExtractor(base_path, cache=cache)
```

### Multiple Cache Namespaces

```python
cache = MemoryCache(max_size=1000)

# Different namespaces
cache.set("key1", value1, namespace="files")
cache.set("key2", value2, namespace="metrics")
cache.set("key3", value3, namespace="attributes")

# Get specific namespace
value = cache.get("key1", namespace="files")

# Clear specific namespace
cache.clear(namespace="metrics")

# Stats per namespace
stats = cache.get_stats()
# {'files': 100, 'metrics': 50, 'attributes': 30}
```

### Lazy Computation

```python
# Compute only if not cached
value = cache.get_or_compute(
    key="expensive_key",
    compute_fn=lambda: expensive_operation(),
    namespace="computed"
)
```

### Cache Monitoring

```python
extractor = ReportExtractor(base_path)
# ... extract data ...

# Check cache efficiency
stats = extractor.get_cache_stats()
print(f"Files cached: {stats['files']}")
print(f"Metrics cached: {stats['metrics']}")
print(f"Attributes cached: {stats['attributes']}")
print(f"Total cached: {stats.get('total', sum(stats.values()))}")
```

---

## ✓ Data Validation

### Basic Validation

```python
from microstrategy_extractor.validators import DataValidator

validator = DataValidator(strict=False)
result = validator.validate_extraction(relatorios)

if not result.valid:
    print(f"Errors: {len(result.errors)}")
    for error in result.errors:
        print(f"  - {error}")

print(f"Warnings: {len(result.warnings)}")
for warning in result.warnings:
    print(f"  - {warning}")
```

### Strict Mode

```python
# Warnings treated as errors
validator = DataValidator(strict=True)
result = validator.validate_extraction(relatorios)

# Will fail on warnings too
if not result.valid:
    print("Validation failed (strict mode)")
```

### Validate Single Report

```python
for relatorio in relatorios:
    result = validator.validate_relatorio(relatorio)
    if not result.valid:
        print(f"Report {relatorio.name} has errors:")
        for error in result.errors:
            print(f"  - {error}")
```

---

## 🔍 Custom Parsers

### Using LinkResolver

```python
from microstrategy_extractor.parsers.link_resolver import LinkResolver
from pathlib import Path

# Create resolver
resolver = LinkResolver(
    index_path=Path("RAW_DATA/.../Métrica.html"),
    object_type="Metric"
)

# Find by ID (most accurate)
result = resolver.find_by_id("ABC123...")

# Find by name (with fuzzy matching)
result = resolver.find_by_name("Nome da Métrica")

# Try both (ID first, fallback to name)
result = resolver.find_link(
    object_id="ABC123...",
    object_name="Nome da Métrica"
)

# Result structure
if result:
    print(f"Name: {result['name']}")
    print(f"File: {result['file']}")
    print(f"Anchor: {result['anchor']}")
    print(f"ID: {result['id']}")
```

### Custom Text Normalization

```python
from microstrategy_extractor.utils.text_normalizer import TextNormalizer

# Custom normalization function
def my_normalize(text):
    return text.lower().replace('-', '').strip()

# Use with resolver
result = resolver.find_by_name("Métrica-X", normalize_fn=my_normalize)

# Or use built-in
from microstrategy_extractor.parsers.link_resolver import LinkResolver

result = resolver.find_by_name(
    "Métrica X",
    normalize_fn=TextNormalizer.normalize_for_matching
)
```

---

## 🗄️ Database Integration

### Load Schema Configuration

```python
from microstrategy_extractor.db import SchemaLoader
from pathlib import Path

schema = SchemaLoader(Path("config/db_schema.yaml"))
schema.load()

# Get import order (respects foreign keys)
import_order = schema.get_import_order()
# ['reports', 'datasets', 'attributes', ...]

# Get table definition
table = schema.get_table("reports")
print(f"Table: {table.name}")
print(f"CSV: {table.csv_file}")
for col in table.columns:
    print(f"  - {col.name}: {col.type}")
```

### Generate SQL Schema

```python
# Generate PostgreSQL schema
sql = schema.generate_create_sql(dialect='postgresql')

# Save to file
with open('create_schema.sql', 'w') as f:
    f.write(sql)
```

### Import to Database

```bash
# Using provided script
cd scripts
python import_to_database.py \
  --connection-string "host=localhost dbname=mydb user=user password=pass" \
  --csv-dir ../output_csv
```

---

## 🎯 Performance Tuning

### 1. Adjust Cache Size

```python
from microstrategy_extractor.config.settings import Config

# For large datasets
config = Config(
    base_path=base_path,
    cache_size_limit=5000  # Default is 1000
)

extractor = ReportExtractor(config.base_path, config)
```

### 2. Use Parallel Processing

```python
# For 10+ reports
from microstrategy_extractor.extractors import extract_reports_parallel

relatorios = extract_reports_parallel(base_path, max_workers=4)
```

### 3. Clear Cache Periodically

```python
# After processing batch
extractor.clear_cache(namespace="files")
```

### 4. Monitor Cache Efficiency

```python
stats = extractor.get_cache_stats()
total_items = sum(stats.values())

if total_items > config.cache_size_limit * 0.9:
    logger.warning("Cache is 90% full, consider increasing size")
```

---

## 🔧 Custom Extractors

### Extend BaseExtractor

```python
from microstrategy_extractor.extractors.base_extractor import BaseExtractor
from microstrategy_extractor.core.models import MyCustomModel

class MyCustomExtractor(BaseExtractor):
    def extract_custom(self, custom_info: dict):
        # Use inherited methods
        soup = self.get_parsed_file("file.html")
        path = self.get_html_file_path('custom')
        
        # Your extraction logic
        result = MyCustomModel(...)
        
        # Cache result
        self.cache.set("key", result, namespace="custom")
        
        return result
```

### Use Custom Extractor

```python
from microstrategy_extractor.cache import MemoryCache

cache = MemoryCache(max_size=1000)
custom_extractor = MyCustomExtractor(base_path, cache=cache)

result = custom_extractor.extract_custom(info)
```

---

## 📊 Advanced Data Analysis

### Analyzing Metric Composition

```python
def analyze_metric_depth(metrica, level=0):
    """Recursively analyze metric composition depth."""
    print("  " * level + f"- {metrica.name} ({metrica.tipo})")
    
    for child in metrica.metricas:
        analyze_metric_depth(child, level + 1)

# Use
for relatorio in relatorios:
    for dataset in relatorio.datasets:
        for metrica in dataset.metricas:
            if metrica.tipo == 'composto':
                analyze_metric_depth(metrica)
```

### Finding All Source Tables

```python
def get_all_source_tables(relatorio):
    """Get all unique source tables used in a report."""
    tables = set()
    
    for dataset in relatorio.datasets:
        # From attributes
        for attr in dataset.atributos:
            for form in attr.formularios:
                for table in form.logic_tables:
                    tables.add(table.name)
        
        # From metrics
        for metric in dataset.metricas:
            tables.update(get_tables_from_metric(metric))
    
    return sorted(tables)

def get_tables_from_metric(metric):
    """Recursively get tables from metric."""
    tables = set()
    
    if metric.fact:
        for table in metric.fact.logic_tables:
            tables.add(table.name)
    
    for child in metric.metricas:
        tables.update(get_tables_from_metric(child))
    
    return tables
```

---

## 🔐 Environment Configuration

### Complete .env Example

```bash
# Base paths
BASE_PATH=RAW_DATA/04 - Relatórios Gerenciais - BARE (20250519221644)

# Output paths
OUTPUT_JSON=output.json
OUTPUT_CSV_DIR=output_csv

# Cache settings
CACHE_ENABLED=true
CACHE_SIZE_LIMIT=1000

# Logging
LOG_LEVEL=INFO
VERBOSE=false

# Performance
PARALLEL_ENABLED=false
MAX_WORKERS=4
```

### Load from Environment

```python
from microstrategy_extractor.config.settings import Config
import os

# Ensure .env is loaded (optional, using python-decouple)
from dotenv import load_dotenv
load_dotenv()

# Load config
config = Config.from_env()
```

---

## 🎓 Best Practices

### 1. Always Validate Configuration

```python
config = Config.from_env()
errors = config.validate()
if errors:
    for error in errors:
        logger.error(error)
    sys.exit(1)
```

### 2. Use Structured Logging

```python
logger = get_logger(__name__, context={'report_id': report.id})
logger.info("Processing dataset", dataset_id=dataset.id)
```

### 3. Handle Exceptions Gracefully

```python
from microstrategy_extractor.core.exceptions import MissingFileError, ParsingError

try:
    relatorios = extractor.extract_all_reports()
except MissingFileError as e:
    logger.error(f"File not found: {e.file_path}")
except ParsingError as e:
    logger.error(f"Parsing failed: {e}")
```

### 4. Validate Before Export

```python
validator = DataValidator()
result = validator.validate_extraction(relatorios)

if result.valid:
    exporter.export(relatorios)
else:
    logger.error("Validation failed, skipping export")
```

---

## 📚 More Resources

- **API Reference**: Complete API documentation in `api-reference.md`
- **User Guide**: Complete usage guide in `user-guide.md`
- **Getting Started**: Quick start in `getting-started.md`

---

**Advanced features ready for professional use!**

