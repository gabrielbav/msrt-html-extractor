"""Type definitions for commonly used dict structures."""

from typing import TypedDict, Optional, List


class LinkResult(TypedDict):
    """Result from link resolution in HTML index files."""
    name: str
    file: str
    anchor: str
    href: str
    id: Optional[str]


class ReportInfo(TypedDict):
    """Report information extracted from Documento.html."""
    name: str
    file: str
    anchor: str
    href: str


class DatasetInfo(TypedDict):
    """Dataset information from DOCUMENT DEFINITION section."""
    name: str
    id: Optional[str]
    href: str


class AttributeInfo(TypedDict):
    """Attribute information from template objects."""
    name_on_dataset: str
    href: str
    id: Optional[str]


class MetricInfo(TypedDict):
    """Metric information from template objects."""
    name_on_dataset: str
    href: str
    id: Optional[str]


class MetricDefinition(TypedDict):
    """Metric definition extracted from DEFINIÇÃO section."""
    tipo: str  # 'simples' or 'composto'
    formula: Optional[str]
    function_id: Optional[str]
    fact_id: Optional[str]
    child_metric_ids: List[str]


class ExpressionInfo(TypedDict):
    """Expression information from EXPRESSÕES table."""
    expressao: str
    tabela_fonte: str


class LogicTableInfo(TypedDict):
    """Logic table information."""
    name: str
    id: str
    file_path: Optional[str]
    column_name: Optional[str]


class FormularioInfo(TypedDict):
    """Formulario information with logic tables."""
    name: str
    logic_tables: List[LogicTableInfo]


class CacheStats(TypedDict):
    """Cache statistics."""
    files: int
    metrics: int
    attributes: int
    facts: int
    functions: int
    tables: int
    total: int

