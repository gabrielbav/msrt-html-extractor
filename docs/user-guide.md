# User Guide - MicroStrategy Extractor

Guia completo de uso do MicroStrategy HTML Documentation Extractor.

## 📋 Índice

- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Configuration](#configuration)
- [Output Formats](#output-formats)
- [Examples](#examples)

---

## Installation

### Standard Installation

```bash
pip install -r requirements.txt
```

### Package Installation (Recommended)

```bash
pip install -e .
```

Após instalação como package, você pode importar de qualquer lugar:

```python
from microstrategy_extractor.extractors import ReportExtractor
```

---

## Basic Usage

### Via Command Line

#### Extrair Relatório Específico

```bash
python main.py \
  --base-path "RAW_DATA/04 - Relatórios Gerenciais" \
  --report "Nome do Relatório" \
  --output-json output.json
```

#### Extrair por ID

```bash
python main.py \
  --base-path "RAW_DATA/04 - Relatórios Gerenciais" \
  --report-id "D8C7F01F4650B3CBC97AB991C79FB9DF" \
  --output-json output.json
```

#### Extrair Todos os Relatórios

```bash
python main.py \
  --base-path "RAW_DATA/04 - Relatórios Gerenciais" \
  --output-json output.json \
  --output-csv-dir output_csv
```

### Via Python API

#### Simple Extraction

```python
import sys
sys.path.insert(0, 'src')

from microstrategy_extractor.extractors import ReportExtractor
from pathlib import Path

extractor = ReportExtractor(Path("RAW_DATA/..."))
relatorios = extractor.extract_report("Nome do Relatório")

for rel in relatorios:
    print(f"Report: {rel.name}")
    print(f"  Datasets: {len(rel.datasets)}")
```

#### Extract All Reports

```python
extractor = ReportExtractor(base_path)
all_relatorios = extractor.extract_all_reports()
print(f"Extracted {len(all_relatorios)} reports")
```

#### Extract by ID

```python
relatorio = extractor.extract_report_by_id("D8C7F01F...")
if relatorio:
    print(f"Found: {relatorio.name}")
```

---

## Advanced Features

### 1. Parallel Processing (2-4x Faster)

Para extrair múltiplos relatórios em paralelo:

```python
from microstrategy_extractor.extractors import extract_reports_parallel

relatorios = extract_reports_parallel(
    base_path,
    max_workers=4  # Number of CPU cores to use
)
```

**Benchmark**:
- Sequential: ~15 min for 100 reports
- Parallel (4 cores): ~4-6 min for 100 reports

### 2. Data Validation

Valide dados extraídos com Pydantic:

```python
from microstrategy_extractor.validators import DataValidator

validator = DataValidator(strict=False)
result = validator.validate_extraction(relatorios)

print(f"Valid: {result.valid}")
print(f"Errors: {len(result.errors)}")
print(f"Warnings: {len(result.warnings)}")

# Show errors
for error in result.errors:
    print(f"✗ {error}")
```

### 3. Custom Cache Configuration

```python
from microstrategy_extractor.cache import MemoryCache
from microstrategy_extractor.extractors import ReportExtractor

# Create custom cache
cache = MemoryCache(max_size=5000)

# Use with extractor
extractor = ReportExtractor(base_path, cache=cache)

# Check cache stats
stats = extractor.get_cache_stats()
print(f"Cache: {stats}")
```

### 4. Structured Logging

```python
from microstrategy_extractor.utils.logger import setup_logging, get_logger

# Setup global logging
setup_logging(level="DEBUG")

# Get logger with context
logger = get_logger(__name__, context={'report_id': report.id})
logger.info("Processing dataset", dataset_id=dataset.id)
```

---

## Configuration

### Environment Variables

Crie `.env` file:

```bash
BASE_PATH=RAW_DATA/04 - Relatórios Gerenciais
OUTPUT_JSON=output.json
OUTPUT_CSV_DIR=output_csv
LOG_LEVEL=INFO
CACHE_SIZE_LIMIT=1000
PARALLEL_ENABLED=false
MAX_WORKERS=4
```

Use com:

```python
from microstrategy_extractor.config.settings import Config

config = Config.from_env()
errors = config.validate()

if not errors:
    extractor = ReportExtractor(config.base_path, config)
```

### Via Code

```python
from microstrategy_extractor.config.settings import Config
from pathlib import Path

config = Config(
    base_path=Path("RAW_DATA/..."),
    output_json_path=Path("output.json"),
    output_csv_dir=Path("output_csv"),
    log_level="DEBUG",
    cache_size_limit=5000,
    verbose=True
)

# Validate
errors = config.validate()
if errors:
    for error in errors:
        print(f"Config error: {error}")
```

### Via CLI Arguments

```python
from microstrategy_extractor.config.settings import Config
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--base-path', required=True)
parser.add_argument('--output-json')
args = parser.parse_args()

config = Config.from_args(args)
```

---

## Output Formats

### JSON Output

**Estrutura**: Hierárquica completa

```json
{
  "relatorios": [{
    "name": "Relatório X",
    "id": "ABC123...",
    "datasets": [{
      "name": "Dataset Y",
      "atributos": [{
        "name": "Agência",
        "formularios": [{
          "name": "ID",
          "logic_tables": [...]
        }]
      }],
      "metricas": [{
        "name": "Vl. Ressarcimento",
        "tipo": "simples",
        "function": {...},
        "fact": {...}
      }]
    }]
  }]
}
```

### CSV Outputs (16 arquivos)

**Entidades** (8):
- Reports.csv - Relatórios
- DataSets.csv - Datasets (cubos/reports)
- Attributes.csv - Atributos
- Metrics.csv - Métricas
- Facts.csv - Fatos
- Functions.csv - Funções de agregação
- Tables.csv - Tabelas lógicas
- AttributesForm.csv - Formulários de atributos

**Relacionamentos** (8):
- Report_DataSet.csv - Report → Dataset
- DataSet_Attribute.csv - Dataset → Attribute
- DataSet_Metric.csv - Dataset → Metric
- AttributeForm_Table.csv - Form → Table
- Metric_Function.csv - Metric → Function
- Metric_Fact.csv - Metric → Fact
- Fact_Table.csv - Fact → Table
- Metric_Metric.csv - Composite → Component Metrics

---

## Examples

### Extract and Export

```python
import sys
sys.path.insert(0, 'src')

from microstrategy_extractor.extractors import ReportExtractor
from microstrategy_extractor.exporters import CSVExporter
from pathlib import Path

# Extract
extractor = ReportExtractor(Path("RAW_DATA/..."))
relatorios = extractor.extract_all_reports()

# Export to CSV
exporter = CSVExporter(Path("output_csv"))
exporter.export(relatorios)

print("✓ Export complete")
```

### Extract with Validation

```python
from microstrategy_extractor.extractors import ReportExtractor
from microstrategy_extractor.validators import DataValidator

extractor = ReportExtractor(base_path)
relatorios = extractor.extract_all_reports()

validator = DataValidator()
result = validator.validate_extraction(relatorios)

if result.valid:
    print("✓ All data validated")
    # Proceed with export
else:
    print(f"⚠ Found {len(result.errors)} errors")
    for error in result.errors:
        print(f"  - {error}")
```

### Parallel Processing

```python
from microstrategy_extractor.extractors import ParallelReportExtractor

parallel = ParallelReportExtractor(base_path, max_workers=4)
relatorios = parallel.extract_all_reports(parallel=True)

print(f"Extracted {len(relatorios)} reports in parallel")
```

---

## 🔍 Data Model

### Relatorio (Report)
- name, id, file_path
- datasets: List[DataSet]

### DataSet
- name, id, file_path
- applicationObject: "CuboInteligente" | "Report" | "Shortcut"
- atributos: List[Atributo]
- metricas: List[Metrica]

### Atributo (Attribute)
- name, id, file_path
- formularios: List[Formulario]

### Formulario (Attribute Form)
- name
- logic_tables: List[LogicTable]

### Metrica (Metric)
- name, id, file_path
- tipo: "simples" | "composto"
- function: Function (for simple metrics)
- fact: Fact (for simple metrics)
- metricas: List[Metrica] (for composite metrics)

### Fact
- name, id, file_path
- logic_tables: List[LogicTable]

### LogicTable (Source Table)
- name, id, file_path
- column_name: SQL column name

---

## 💡 Tips & Best Practices

### 1. Use Specific Extraction When Possible

```python
# Faster
relatorio = extractor.extract_report("Specific Report Name")

# vs slower
all_relatorios = extractor.extract_all_reports()
```

### 2. Enable Caching

```python
# Cache is enabled by default
config = Config(cache_enabled=True, cache_size_limit=1000)
```

### 3. Use Parallel for Large Batches

Se você tem 10+ relatórios, use parallel processing:

```python
from microstrategy_extractor.extractors import extract_reports_parallel

relatorios = extract_reports_parallel(base_path, max_workers=4)
```

### 4. Validate Before Export

```python
from microstrategy_extractor.validators import DataValidator

validator = DataValidator()
result = validator.validate_extraction(relatorios)

if result.valid:
    exporter.export(relatorios)
```

---

## 📞 Next Steps

- **Advanced Features**: Read `docs/advanced.md`
- **API Reference**: Read `docs/api-reference.md`
- **Examples**: See example code in this guide

---

**Questions?** Check `docs/advanced.md` for more complex scenarios.

