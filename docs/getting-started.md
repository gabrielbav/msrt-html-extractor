# Getting Started - MicroStrategy Extractor

Guia rápido para começar a usar o MicroStrategy HTML Documentation Extractor.

## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Arquivos HTML exportados do MicroStrategy

## 🚀 Instalação

### 1. Instalar Dependências

```bash
cd /caminho/para/BlankProject
pip install -r requirements.txt
```

### 2. (Opcional) Instalar como Package

```bash
# Modo desenvolvimento (editable install)
pip install -e .
```

**Benefícios**:
- Import sem precisar manipular `sys.path`
- Comandos CLI disponíveis globalmente
- Pode usar de qualquer diretório

### 3. Verificar Instalação

```bash
# Se instalou como package
python -c "from microstrategy_extractor import Config; print('✓ OK')"

# Se não instalou
python -c "import sys; sys.path.insert(0, 'src'); from microstrategy_extractor import Config; print('✓ OK')"
```

## 🎯 Primeiro Uso

### Exemplo 1: Extrair Um Relatório

```bash
python main.py \
  --base-path "RAW_DATA/04 - Relatórios Gerenciais - BARE (20250519221644)" \
  --report "04.10.043 - Resultado Comercial - Líderes" \
  --output-json output.json
```

**Output**: Arquivo `output.json` com estrutura hierárquica do relatório.

### Exemplo 2: Extrair Todos os Relatórios

```bash
python main.py \
  --base-path "RAW_DATA/04 - Relatórios Gerenciais - BARE (20250519221644)" \
  --output-json output.json \
  --output-csv-dir output_csv
```

**Output**: 
- `output.json` com todos os relatórios
- `output_csv/` com 16 arquivos CSV normalizados

### Exemplo 3: Modo Verbose (Debug)

```bash
python main.py \
  --base-path "RAW_DATA/04 - Relatórios Gerenciais - BARE (20250519221644)" \
  --report "04.10.043 - Resultado Comercial - Líderes" \
  --output-json output.json \
  --verbose
```

**Output**: Logs detalhados de cada etapa da extração.

## 📝 Uso Programático

### Método 1: Sem Instalar Package

```python
import sys
sys.path.insert(0, 'src')

from microstrategy_extractor.extractors import ReportExtractor
from pathlib import Path

extractor = ReportExtractor(Path("RAW_DATA/04 - Relatórios..."))
relatorios = extractor.extract_all_reports()

print(f"Extraídos {len(relatorios)} relatórios")
```

### Método 2: Com Package Instalado

```python
from microstrategy_extractor.extractors import ReportExtractor
from microstrategy_extractor.config.settings import Config
from pathlib import Path

config = Config.from_env()
extractor = ReportExtractor(config.base_path, config)
relatorios = extractor.extract_all_reports()
```

### Método 3: Com Configuração Completa

```python
import sys
sys.path.insert(0, 'src')

from microstrategy_extractor.config.settings import Config
from microstrategy_extractor.utils.logger import setup_logging, get_logger
from microstrategy_extractor.extractors import ReportExtractor
from microstrategy_extractor.exporters import CSVExporter
from microstrategy_extractor.validators import DataValidator

# Setup
config = Config.from_env()
setup_logging(config.log_level)
logger = get_logger(__name__)

# Extract
extractor = ReportExtractor(config.base_path, config)
relatorios = extractor.extract_all_reports()
logger.info(f"Extracted {len(relatorios)} reports")

# Validate
validator = DataValidator()
result = validator.validate_extraction(relatorios)

if result.valid:
    # Export
    exporter = CSVExporter(config.output_csv_dir)
    exporter.export(relatorios)
    logger.info("Export complete")
else:
    logger.error(f"Validation failed: {len(result.errors)} errors")
```

## 🔧 Configuração

### Via Environment Variables

Crie arquivo `.env` na raiz do projeto:

```bash
BASE_PATH=RAW_DATA/04 - Relatórios Gerenciais - BARE (20250519221644)
OUTPUT_JSON=output.json
OUTPUT_CSV_DIR=output_csv
LOG_LEVEL=INFO
CACHE_SIZE_LIMIT=1000
```

Depois use:

```python
from microstrategy_extractor.config.settings import Config

config = Config.from_env()
```

### Via Código

```python
from microstrategy_extractor.config.settings import Config
from pathlib import Path

config = Config(
    base_path=Path("RAW_DATA/..."),
    output_json_path=Path("output.json"),
    output_csv_dir=Path("output_csv"),
    log_level="DEBUG",
    cache_size_limit=5000
)

# Validate config
errors = config.validate()
if errors:
    for error in errors:
        print(f"Config error: {error}")
```

## 📊 Entendendo os Outputs

### Summary Console

Ao executar, você verá um resumo:

```
EXTRACTION SUMMARY (UNIQUE IDs)
============================================================
Total Reports: 1
Total DataSets: 2
Total Attributes: 41
Total Metrics: 85
  - Simples: 51
  - Compostas: 33

Relationships:
  Report -> DataSets: 2
  DataSet -> Attributes: 82
  DataSet -> Metrics: 168
```

**Entenda**:
- **Total**: Objetos únicos (por ID)
- **Relationships**: Todas as referências (com reuso)

### CSV Files

Os arquivos CSV podem ser importados em:
- Excel / Google Sheets
- Banco de dados (use `scripts/import_to_database.py`)
- Power BI / Tableau
- Análise com pandas

### JSON File

Use para:
- Análise hierárquica
- APIs / integrações
- Navegação de composição de métricas

## 🔍 Troubleshooting

### Erro: "File not found: Documento.html"

**Solução**: Verifique se o `--base-path` aponta para um diretório contendo `Documento.html`.

### Erro: "Module not found: microstrategy_extractor"

**Solução**:
```python
# Adicione ao início do seu script
import sys
sys.path.insert(0, 'src')

# Ou instale o package
pip install -e .
```

### Warning: "Circular reference detected"

**Solução**: Normal para métricas compostas complexas. O sistema detecta e previne loops infinitos automaticamente.

### Encoding Problems

O sistema tenta múltiplos encodings automaticamente. Se ainda houver problemas, os nomes dos índices HTML (Atributo.html, Métrica.html) são sempre preferidos.

## 📚 Próximos Passos

1. **Leia**: `docs/user-guide.md` para guia completo
2. **Explore**: `docs/api-reference.md` para referência da API
3. **Avançado**: `docs/advanced.md` para features avançados

## ✨ Features Principais

- ⚡ **Processamento Paralelo**: Extraction 2-4x mais rápida
- ✓ **Validação de Dados**: Pydantic validators
- 💾 **Cache Otimizado**: LRU com namespaces
- 🔧 **Configuração Flexível**: Environment vars, CLI, código
- 📊 **Múltiplos Outputs**: JSON hierárquico + CSV normalizados
- 🛡️ **Type-Safe**: Type hints completos
- 📝 **Bem Documentado**: Docstrings em todo código

---

**Próximo**: Leia `docs/user-guide.md` para aprender todos os recursos!

