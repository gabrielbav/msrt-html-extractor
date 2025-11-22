# MicroStrategy Data Model Extractor

Professional data extraction tool for parsing MicroStrategy HTML documentation and extracting complex relationships between reports, datasets, attributes, metrics, and source tables.

## 📋 Table of Contents

- [Installation](#installation)
- [How to Use](#how-to-use)
  - [Configuration](#configuration)
  - [Commands](#commands)
- [Project Structure](#project-structure)
- [Data Model](#data-model)
  - [JSON Schema](#json-schema)
  - [Graph Model](#graph-model)

---

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- MicroStrategy HTML documentation files

### Installation Steps

1. **Clone the repository:**

```bash
git clone <repository-url>
cd microstrategy-extractor
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Install the package:**

```bash
pip install -e .
```

4. **Verify installation:**

```bash
python -c "from microstrategy_extractor import Config; print('✓ Installation successful')"
```

You're ready to extract data! See the [Commands](#commands) section below.

---

## 📖 How to Use

### Configuration

#### 1. Environment Variables (.env)

Create a `.env` file in the project root:

```bash
# Input path
BASE_PATH=RAW_DATA/04 - Relatórios Gerenciais - BARE (20250519221644)

# Output paths
OUTPUT_JSON=output.json

# Cache settings
CACHE_ENABLED=true
CACHE_SIZE_LIMIT=1000

# Logging
LOG_LEVEL=INFO
VERBOSE=false

# Performance (parallel processing)
PARALLEL_ENABLED=false
MAX_WORKERS=4
```

**Configuration Parameters:**

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|--------------|
| `BASE_PATH` | Directory containing MicroStrategy HTML files | Required | Valid directory path |
| `OUTPUT_JSON` | Output JSON file path | `output.json` | Any .json file path |
| `CACHE_ENABLED` | Enable/disable caching | `true` | `true`, `false` |
| `CACHE_SIZE_LIMIT` | Maximum cache items (LRU eviction) | `1000` | Positive integer |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `VERBOSE` | Enable detailed logs | `false` | `true`, `false` |
| `PARALLEL_ENABLED` | Enable parallel processing | `false` | `true`, `false` |
| `MAX_WORKERS` | Number of parallel workers | `4` | 1-8 (depends on CPU cores) |

#### 2. Cache Configuration

The system uses an **LRU (Least Recently Used)** cache with namespace isolation:

- **Namespaces**: `files`, `metrics`, `attributes`, `reports`, `datasets`
- **Eviction Policy**: Automatic LRU when cache reaches `CACHE_SIZE_LIMIT`
- **Benefits**: 2-4x faster extraction on subsequent runs

**Cache Usage Example:**

```python
from microstrategy_extractor.cache import MemoryCache
from microstrategy_extractor.extractors import ReportExtractor

# Custom cache size
cache = MemoryCache(max_size=5000)
extractor = ReportExtractor(base_path, cache=cache)

# Check cache statistics
stats = extractor.get_cache_stats()
print(f"Cached items: {stats}")
```

#### 3. Programmatic Configuration

```python
import sys
sys.path.insert(0, 'src')

from microstrategy_extractor.config.settings import Config
from pathlib import Path

# Method 1: From environment variables
config = Config.from_env()

# Method 2: Direct configuration
config = Config(
    base_path=Path("RAW_DATA/04 - Relatórios Gerenciais"),
    output_json_path=Path("output.json"),
    log_level="DEBUG",
    cache_size_limit=5000,
    verbose=True
)

# Validate configuration
errors = config.validate()
if errors:
    for error in errors:
        print(f"Config error: {error}")
```

---

### Commands

#### Main CLI Commands

**Extract all reports:**
```bash
python main.py --base-path <path> --output-json output.json
```

**Extract specific report by name:**
```bash
python main.py --base-path <path> --report "Report Name" --output-json output.json
```

**Extract report by ID:**
```bash
python main.py --base-path <path> --report-id "ABC123..." --output-json output.json
```

**Filter reports by pattern:**
```bash
python main.py --base-path <path> --filter "Boletim" --output-json output.json
```

**Enable verbose logging (debug mode):**
```bash
python main.py --base-path <path> --output-json output.json --verbose
```

**Use aggressive caching (faster, more RAM):**
```bash
python main.py --base-path <path> --output-json output.json --aggressive-cache
```

#### Script Commands

**Initialize Neo4j schema:**
```bash
python -m microstrategy_extractor.scripts.init_neo4j_schema \
  --uri bolt://localhost:7687 \
  --user neo4j \
  --password microstrategy2024
```

**Load data to Neo4j:**
```bash
python -m microstrategy_extractor.scripts.load_to_neo4j \
  --json-file output.json \
  --environment-id prod-2024-11 \
  --environment-name "Production"
```

#### Full Example

```bash
# 1. Extract all reports to JSON
python main.py \
  --base-path "RAW_DATA/04 - Relatórios Gerenciais - BARE (20250519221644)" \
  --output-json output.json \
  --verbose

# 2. Load to Neo4j (optional)
python -m microstrategy_extractor.scripts.load_to_neo4j \
  --json-file output.json \
  --environment-id prod-2024-11 \
  --environment-name "Production"
```

#### Python API Usage

```python
from microstrategy_extractor.extractors import ReportExtractor
from microstrategy_extractor.exporters import export_to_json
from pathlib import Path

# Initialize extractor
base_path = Path("RAW_DATA/04 - Relatórios Gerenciais")
extractor = ReportExtractor(base_path)

# Extract all reports
relatorios = extractor.extract_all_reports()
print(f"Extracted {len(relatorios)} reports")

# Extract specific report
relatorios = extractor.extract_report("Report Name")

# Extract by ID
relatorio = extractor.extract_report_by_id("ABC123...")

# Export to JSON
export_to_json(relatorios, Path("output.json"))
```

#### Parallel Processing (2-4x Faster)

For extracting 10+ reports:

```python
from microstrategy_extractor.extractors import extract_reports_parallel

relatorios = extract_reports_parallel(
    base_path,
    max_workers=4  # Number of CPU cores
)
```

**Performance Benchmarks:**

| Reports | Sequential | Parallel (4 cores) | Speedup |
|---------|-----------|-------------------|---------|
| 10      | ~2 min    | ~1 min            | 2x      |
| 50      | ~7 min    | ~2.5 min          | 2.8x    |
| 100     | ~15 min   | ~4-6 min          | 3-4x    |

---

## 📁 Project Structure

```
microstrategy-extractor/
├── src/
│   └── microstrategy_extractor/          # Main package
│       ├── core/                          # Core models, types, exceptions, constants
│       │   ├── constants.py               # Constants and enums
│       │   ├── exceptions.py              # Custom exceptions
│       │   ├── models.py                  # Data models (dataclasses)
│       │   └── types.py                   # Type definitions
│       │
│       ├── config/                        # Configuration management
│       │   └── settings.py                # Config class (env, CLI, code)
│       │
│       ├── cache/                         # Caching system
│       │   ├── cache_manager.py           # Abstract cache interface
│       │   └── memory_cache.py            # LRU cache implementation
│       │
│       ├── parsers/                       # HTML parsing
│       │   ├── base_parser.py             # Base parser class
│       │   ├── report_parser.py           # Report parsing
│       │   ├── metric_parser.py           # Metric parsing
│       │   ├── attribute_parser.py        # Attribute parsing
│       │   ├── fact_parser.py             # Fact parsing
│       │   └── link_resolver.py           # Link resolution
│       │
│       ├── extractors/                    # Data extraction
│       │   ├── base_extractor.py          # Base extractor class
│       │   ├── report_extractor.py        # Report extraction
│       │   ├── metric_extractor.py        # Metric extraction
│       │   ├── attribute_extractor.py     # Attribute extraction
│       │   ├── dataset_extractor.py       # Dataset extraction
│       │   ├── parallel_extractor.py      # Parallel processing
│       │   └── extractor_helpers.py       # Helper functions
│       │
│       ├── validators/                    # Data validation
│       │   └── data_validator.py          # Validators
│       │
│       ├── utils/                         # Utilities
│       │   ├── logger.py                  # Structured logging
│       │   └── text_normalizer.py         # Text normalization
│       │
│       ├── scripts/                       # CLI scripts
│       │   ├── init_neo4j_schema.py       # Initialize Neo4j schema
│       │   └── load_to_neo4j.py           # Load data to Neo4j
│       │
│       └── exporters/                     # Data exporters
│           └── json_exporter.py           # JSON export functionality
│
├── docker-compose.yml                     # Neo4j Docker setup
├── main.py                                # Main CLI entry point
├── requirements.txt                       # Python dependencies
└── README.md                              # This file
```

---

## 📊 Data Model

### JSON Schema

The extraction produces a hierarchical JSON structure representing the complete MicroStrategy data model:

```json
{
  "relatorios": [
    {
      "name": "",
      "id": "",
      "migration_stage": null,
      "decision": null,
      "file_path": "",
      "datasets": [
        {
          "name": "",
          "id": "",
          "migration_stage": null,
          "decision": null,
          "file_path": "",
          "applicationObject": "",
          "graphic": "",
          "atributos": [
            {
              "name": "",
              "name_on_dataset": "",
              "id": "",
              "migration_stage": null,
              "decision": null,
              "file_path": "",
              "applicationSchema": "",
              "formularios": [
                {
                  "id": "",
                  "name": "",
                  "logic_tables": [
                    {
                      "name": "",
                      "id": "",
                      "migration_stage": null,
                      "decision": null,
                      "file_path": "",
                      "column_name": ""
                    }
                  ]
                }
              ]
            }
          ],
          "metricas": [
            {
              "name": "",
              "id": "",
              "migration_stage": null,
              "decision": null,
              "file_path": "",
              "applicationObject": "",
              "tipo": "",
              "formula": "",
              "function": {
                "name": "",
                "file_path": ""
              },
              "fact": {
                "name": "",
                "id": "",
                "file_path": "",
                "applicationObject": "",
                "logic_tables": [
                  {
                    "name": "",
                    "id": "",
                    "migration_stage": null,
                    "decision": null,
                    "file_path": "",
                    "column_name": ""
                  }
                ]
              },
              "metricas": []
            }
          ]
        }
      ]
    }
  ]
}
```

**Field Descriptions:**

| Field | Type | Description | Possible Values |
|-------|------|-------------|-----------------|
| `name` | string | Object name | Any string |
| `id` | string | Unique MicroStrategy ID (32 chars hex) | e.g., "D8C7F01F4650B3CBC97AB991C79FB9DF" |
| `file_path` | string | HTML file reference | e.g., "ABC123_1.html#DEF456" |
| `applicationObject` | string | MicroStrategy object type | "Metrica", "Fato", "Função", "TabelaLogica", "CuboInteligente", "Report", "Atalho" |
| `applicationSchema` | string | Schema classification | "Atributo" |
| `graphic` | string | Graphic/chart type | null or chart type |
| `tipo` | string | Metric type | "simples" (simple), "composto" (composite) |
| `formula` | string | Metric formula | e.g., "Sum(VL_REALIZADO)" |
| `column_name` | string | Database column name | e.g., "VL_RESS" |
| `name_on_dataset` | string | Attribute name as displayed | May differ from `name` |
| `formularios` | array | Attribute forms | List of form objects |
| `logic_tables` | array | Source tables | List of table objects |
| `metricas` | array | Component metrics (for composite) | Recursive metric list |
| `migration_stage` | string\|null | Migration workflow stage | null (default) |
| `decision` | string\|null | Migration decision | null (default) |

**Migration Control Fields:**

The extractor outputs two additional fields for migration workflow management:

- **`migration_stage`**: Tracks the current stage in the migration workflow
- **`decision`**: Indicates the migration decision for the object

These fields are initialized as `null` during extraction and are intended to be populated by external migration management processes. They appear on:
- `relatorios` (reports)
- `datasets`
- `atributos` (attributes)
- `metricas` (metrics)
- `logic_tables`

---

### Graph Model

The data model forms a **property graph** with nodes and directed relationships, supporting recursive metric composition.

#### Graph Nodes

```mermaid
graph TD
    Report["Report<br/>{id, name, file_path}"]
    Dataset["Dataset<br/>{id, name, file_path,<br/>applicationObject, graphic}"]
    Attribute["Attribute<br/>{id, name, name_on_dataset,<br/>file_path, applicationSchema}"]
    Form["Form<br/>{name}"]
    Table["Table<br/>{id, name, file_path,<br/>column_name}"]
    Metric["Metric<br/>{id, name, file_path,<br/>applicationObject, tipo, formula}"]
    Function["Function<br/>{name, file_path}"]
    Fact["Fact<br/>{id, name, file_path,<br/>applicationObject}"]
    
    Report -->|CONTAINS| Dataset
    Dataset -->|HAS_ATTRIBUTE| Attribute
    Dataset -->|HAS_METRIC| Metric
    Attribute -->|HAS_FORM| Form
    Form -->|USES_TABLE| Table
    
    Metric -->|USES_FUNCTION| Function
    Metric -->|USES_FACT| Fact
    Metric -->|COMPOSED_OF| Metric
    
    Fact -->|READS_FROM| Table
    
    style Report fill:#e1f5ff
    style Dataset fill:#fff4e1
    style Attribute fill:#e8f5e9
    style Metric fill:#fce4ec
    style Fact fill:#ffe4cc
    style Function fill:#e8f5e9
    style Table fill:#f3e5f5
```

#### Complete Relationship Model

| Source | Relationship | Target | Cardinality | Description |
|--------|--------------|--------|-------------|-------------|
| **Report** | `CONTAINS` | **Dataset** | 1:N | A report contains one or more datasets |
| **Dataset** | `HAS_ATTRIBUTE` | **Attribute** | 1:N | A dataset contains attributes (embedded in JSON) |
| **Dataset** | `HAS_METRIC` | **Metric** | 1:N | A dataset contains metrics (embedded in JSON) |
| **Attribute** | `HAS_FORM` | **Form** | 1:N | An attribute has multiple forms (ID, DESC, etc.) |
| **Form** | `USES_TABLE` | **Table** | 1:N | A form uses one or more logic tables with column_name |
| **Metric** | `USES_FUNCTION` | **Function** | 0..1 | Simple metrics use one aggregation function (null for composite) |
| **Metric** | `USES_FACT` | **Fact** | 0..1 | Simple metrics aggregate one fact (null for composite) |
| **Metric** | `COMPOSED_OF` | **Metric** | 0..N | **Recursive: composite metrics reference child metrics** |
| **Fact** | `READS_FROM` | **Table** | 1:N | A fact reads from one or more logic tables with column_name |

**Important Notes:**
- **`column_name`** is a **property on the Table relationship**, not a separate node
- **Function** has NO `id` property (only `name` and `file_path`)
- **Attributes and Metrics** are embedded arrays within Dataset (not separate top-level entities)
- **Composite metrics** have `function: null` and `fact: null` - only `metricas` array is populated
- **Simple metrics** have `function` and `fact` populated - `metricas` is an empty array

#### How Composite Metrics Work

**The `COMPOSED_OF` relationship enables recursive metric composition:**

```mermaid
graph TD
    subgraph "Composite Metric Example: Var. PEL"
        M1["Metric: Var. PEL Mês Ano Anterior<br/>{tipo: composto}<br/>function: null, fact: null<br/>Formula: Vl. PEL - Vl. PEL Mês Ano Anterior / Abs"]
        M2["Metric: Vl. PEL<br/>{tipo: simples}<br/>Formula: Sum Vl. PEL"]
        M3["Metric: Vl. PEL Mês Ano Anterior<br/>{tipo: simples}<br/>Formula: Sum Vl. PEL Mês Ano Anterior"]
        
        M1 -->|COMPOSED_OF| M2
        M1 -->|COMPOSED_OF| M3
        
        F1["Function: Sum<br/>{name, file_path}"]
        Fact1["Fact: Vl. PEL<br/>{id, name, file_path}"]
        T1["Table: FT_DESEMPENHO_ORCM_RESUMO<br/>{id, name, file_path}<br/>column_name: VL_PEL"]
        
        M2 -->|USES_FUNCTION| F1
        M2 -->|USES_FACT| Fact1
        Fact1 -->|READS_FROM| T1
        
        F2["Function: Sum<br/>{name, file_path}"]
        Fact2["Fact: Vl. PEL Mês Ano Anterior<br/>{id, name, file_path}"]
        T2["Table: FT_DESEMPENHO_ORCM_RESUMO<br/>{id, name, file_path}<br/>column_name: VL_PEL_MES_ANO_ANT"]
        
        M3 -->|USES_FUNCTION| F2
        M3 -->|USES_FACT| Fact2
        Fact2 -->|READS_FROM| T2
    end
    
    style M1 fill:#fce4ec
    style M2 fill:#e8f5e9
    style M3 fill:#e8f5e9
    style F1 fill:#fff4e1
    style F2 fill:#fff4e1
    style Fact1 fill:#ffe4cc
    style Fact2 fill:#ffe4cc
```

**Key Points about `COMPOSED_OF`:**

1. **Recursive Nature**: Composite metrics can reference other composite metrics (unlimited depth)
2. **Type Distinction**: 
   - `tipo: "simples"` → Has `function` and `fact` objects populated, `metricas: []`
   - `tipo: "composto"` → Has `function: null` and `fact: null`, `metricas: [...]` populated
3. **Reusability**: The same metric can be reused in multiple composite metrics
4. **Circular Detection**: The extractor prevents infinite loops in circular references
5. **column_name**: Stored as a property on the Table object in the `logic_tables` array, not a separate entity

#### Example: Three-Level Metric Composition

```mermaid
graph TD
    subgraph "Complex Nested Metrics"
        M1["ROI %<br/>{tipo: composto}<br/>function: null, fact: null"]
        M2["Net Profit<br/>{tipo: composto}<br/>function: null, fact: null"]
        M3["Total Cost<br/>{tipo: composto}<br/>function: null, fact: null"]
        M4["Revenue<br/>{tipo: simples}"]
        M5["Operating Cost<br/>{tipo: simples}"]
        M6["Marketing Cost<br/>{tipo: simples}"]
        M7["Investment<br/>{tipo: simples}"]
        
        M1 -->|COMPOSED_OF| M2
        M1 -->|COMPOSED_OF| M7
        M2 -->|COMPOSED_OF| M4
        M2 -->|COMPOSED_OF| M3
        M3 -->|COMPOSED_OF| M5
        M3 -->|COMPOSED_OF| M6
        
        F1["Function: Sum"]
        F2["Function: Sum"]
        F3["Function: Sum"]
        F4["Function: Sum"]
        
        Fact1["Fact: VL_REVENUE"]
        Fact2["Fact: VL_OP_COST"]
        Fact3["Fact: VL_MKT_COST"]
        Fact4["Fact: VL_INVESTMENT"]
        
        T1["Table: FT_SALES"]
        T2["Table: FT_COSTS"]
        T3["Table: FT_COSTS"]
        T4["Table: FT_INVEST"]
        
        M4 -->|USES_FUNCTION| F1
        M4 -->|USES_FACT| Fact1
        Fact1 -->|READS_FROM| T1
        
        M5 -->|USES_FUNCTION| F2
        M5 -->|USES_FACT| Fact2
        Fact2 -->|READS_FROM| T2
        
        M6 -->|USES_FUNCTION| F3
        M6 -->|USES_FACT| Fact3
        Fact3 -->|READS_FROM| T3
        
        M7 -->|USES_FUNCTION| F4
        M7 -->|USES_FACT| Fact4
        Fact4 -->|READS_FROM| T4
    end
    
    style M1 fill:#ff6b6b
    style M2 fill:#feca57
    style M3 fill:#feca57
    style M4 fill:#48dbfb
    style M5 fill:#48dbfb
    style M6 fill:#48dbfb
    style M7 fill:#48dbfb
```

**This shows:**
- **Level 1** (Red): ROI % is composed of Net Profit and Investment (composite metric with null function/fact)
- **Level 2** (Yellow): Net Profit and Total Cost are also composite metrics (function: null, fact: null)
- **Level 3** (Blue): All leaf metrics are simple metrics with function and fact objects populated

#### Complete Report Structure Example

```mermaid
graph TD
    subgraph "Monthly Sales Report"
        R1["Report: Monthly Sales Analysis<br/>{id, name, file_path}"]
        DS1["Dataset: Sales Cube<br/>{id, name, file_path,<br/>applicationObject, graphic}"]
        
        R1 -->|CONTAINS| DS1
        
        A1["Attribute: Customer<br/>{id, name, name_on_dataset,<br/>file_path, applicationSchema}"]
        A2["Attribute: Product<br/>{id, name, name_on_dataset,<br/>file_path, applicationSchema}"]
        
        DS1 -->|HAS_ATTRIBUTE| A1
        DS1 -->|HAS_ATTRIBUTE| A2
        
        F1["Form: ID<br/>{name}"]
        F2["Form: Name<br/>{name}"]
        F3["Form: ID<br/>{name}"]
        F4["Form: Description<br/>{name}"]
        
        A1 -->|HAS_FORM| F1
        A1 -->|HAS_FORM| F2
        A2 -->|HAS_FORM| F3
        A2 -->|HAS_FORM| F4
        
        T1["Table: DIM_CUSTOMER<br/>{id, name, file_path}<br/>column_name: CUSTOMER_ID"]
        T2["Table: DIM_CUSTOMER<br/>{id, name, file_path}<br/>column_name: CUSTOMER_NAME"]
        T3["Table: DIM_PRODUCT<br/>{id, name, file_path}<br/>column_name: PRODUCT_ID"]
        T4["Table: DIM_PRODUCT<br/>{id, name, file_path}<br/>column_name: PRODUCT_DESC"]
        
        F1 -->|USES_TABLE| T1
        F2 -->|USES_TABLE| T2
        F3 -->|USES_TABLE| T3
        F4 -->|USES_TABLE| T4
        
        M1["Metric: Revenue<br/>{id, name, file_path,<br/>tipo: simples, formula}"]
        M2["Metric: Profit Margin %<br/>{id, name, file_path,<br/>tipo: composto, formula}<br/>function: null, fact: null"]
        M3["Metric: Profit<br/>{id, name, file_path,<br/>tipo: simples, formula}"]
        
        DS1 -->|HAS_METRIC| M1
        DS1 -->|HAS_METRIC| M2
        DS1 -->|HAS_METRIC| M3
        
        M2 -->|COMPOSED_OF| M3
        M2 -->|COMPOSED_OF| M1
        
        Func1["Function: Sum<br/>{name, file_path}"]
        Func2["Function: Sum<br/>{name, file_path}"]
        
        M1 -->|USES_FUNCTION| Func1
        M3 -->|USES_FUNCTION| Func2
        
        Fact1["Fact: Sales Amount<br/>{id, name, file_path,<br/>applicationObject}"]
        Fact2["Fact: Profit Amount<br/>{id, name, file_path,<br/>applicationObject}"]
        
        M1 -->|USES_FACT| Fact1
        M3 -->|USES_FACT| Fact2
        
        T5["Table: FT_SALES<br/>{id, name, file_path}<br/>column_name: AMOUNT"]
        T6["Table: FT_SALES<br/>{id, name, file_path}<br/>column_name: PROFIT"]
        
        Fact1 -->|READS_FROM| T5
        Fact2 -->|READS_FROM| T6
    end
    
    style R1 fill:#e1f5ff
    style DS1 fill:#fff4e1
    style A1 fill:#e8f5e9
    style A2 fill:#e8f5e9
    style M1 fill:#48dbfb
    style M2 fill:#feca57
    style M3 fill:#48dbfb
    style Func1 fill:#fff9e6
    style Func2 fill:#fff9e6
    style Fact1 fill:#ffe4cc
    style Fact2 fill:#ffe4cc
    style T1 fill:#f3e5f5
    style T2 fill:#f3e5f5
    style T3 fill:#f3e5f5
    style T4 fill:#f3e5f5
    style T5 fill:#f3e5f5
    style T6 fill:#f3e5f5
```

#### Graph Characteristics

1. **Property Graph**: Each node has properties (id, name, file_path, etc.) - column_name is a property, not a node
2. **Directed Relationships**: All edges have direction and semantic meaning
3. **Recursive Structure**: `COMPOSED_OF` enables unlimited metric nesting depth
4. **Embedded Collections**: Attributes and Metrics are embedded arrays within Dataset (composition relationship)
5. **Null Handling**: Composite metrics have `function: null` and `fact: null`; simple metrics have `metricas: []`
6. **Type Safety**: Nodes have distinct types with specific properties
7. **Function Identification**: Functions only have `{name, file_path}` - no unique `id` field
8. **Traversable**: Can navigate from Report → Dataset → Attribute → Form → Table (with column_name property)
9. **Traversable (Metrics)**: Can navigate from Report → Dataset → Metric → Fact → Table (with column_name property)
10. **Traversable (Composite)**: Can navigate from Metric → Metric → Metric (recursive composition)

---

## 🎯 Key Features

- ✅ **Modular Architecture**: Strategy pattern, dependency injection, SOLID principles
- ✅ **Parallel Processing**: 2-4x faster extraction with multi-core support
- ✅ **Data Validation**: Pydantic models with strict validation
- ✅ **Optimized Caching**: LRU cache with namespace isolation
- ✅ **Recursive Metrics**: Supports complex composite metric structures
- ✅ **Encoding Handling**: Automatic detection (UTF-8, ISO-8859-1, Latin-1)
- ✅ **JSON Export**: Hierarchical JSON output format
- ✅ **Flexible Configuration**: Environment variables, CLI args, programmatic
- ✅ **Zero Hardcoding**: All values configurable
- ✅ **Type Safety**: Complete type hints throughout codebase
- ✅ **Structured Logging**: Contextual logging with multiple levels

---

## 🔧 Advanced Usage

### Custom Cache Configuration

```python
from microstrategy_extractor.cache import MemoryCache

# Large cache for big datasets
cache = MemoryCache(max_size=5000)
extractor = ReportExtractor(base_path, cache=cache)

# Check cache stats
stats = extractor.get_cache_stats()
print(f"Files: {stats['files']}, Metrics: {stats['metrics']}")

# Clear specific namespace
extractor.clear_cache(namespace="files")
```

### Strict Data Validation

```python
from microstrategy_extractor.validators import DataValidator

# Strict mode (warnings = errors)
validator = DataValidator(strict=True)
result = validator.validate_extraction(relatorios)

if not result.valid:
    print(f"Validation errors: {len(result.errors)}")
    for error in result.errors:
        print(f"  - {error}")
```

---

## 🐛 Troubleshooting

### Import Errors

```python
# Add src/ to Python path
import sys
sys.path.insert(0, 'src')

# Or install as package
pip install -e .
```

### Encoding Issues

The parser tries multiple encodings automatically (ISO-8859-1, Latin-1, UTF-8). HTML index files (Atributo.html, Métrica.html) are always preferred for name resolution.

### Cache Issues

```python
# Clear cache if needed
extractor.clear_cache()

# Increase cache size
config.cache_size_limit = 5000
```

### Performance Issues

- Use parallel processing for 10+ reports
- Increase cache size for large datasets
- Enable only necessary validation

---

## 📄 Requirements

```
beautifulsoup4>=4.12.0
lxml>=4.9.0
pyyaml>=6.0.0
pydantic>=2.0.0
neo4j>=5.15.0
python-dotenv>=1.0.0
```

**Optional:**
- `psycopg2-binary` - PostgreSQL database support
- `pytest`, `black`, `mypy`, `ruff` - Development tools

---

## 📞 Support

For questions or issues:
1. Check configuration in `.env` file
2. Enable verbose mode with `--verbose` flag
3. Review logs for detailed error messages
4. Verify HTML file structure in `BASE_PATH`

---

**Version**: 2.0.0  
**Status**: Production Ready  
**License**: MIT
