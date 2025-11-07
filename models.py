"""Data model classes for report extraction."""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Relatorio:
    """Represents a report/document."""
    name: str
    id: str
    file_path: str
    datasets: List['DataSet'] = field(default_factory=list)


@dataclass
class DataSet:
    """Represents a dataset (Intelligent Cube or Report)."""
    name: str
    id: str
    file_path: str
    relatorio_id: str
    applicationObject: Optional[str] = None  # "CuboInteligente" or "Report"
    graphic: Optional[str] = None  # Graph type for Report datasets (e.g., "Barra Vertical")
    atributos: List['Atributo'] = field(default_factory=list)
    metricas: List['Metrica'] = field(default_factory=list)


@dataclass
class LogicTable:
    """Represents a logical table (source table)."""
    name: str
    id: str
    file_path: Optional[str] = None
    column_name: Optional[str] = None  # Column name from EXPRESSÃO field


@dataclass
class Formulario:
    """Represents an attribute form."""
    name: str  # Form name (e.g., "ID", "Codigo Agência", "Nome Agência")
    logic_tables: List['LogicTable'] = field(default_factory=list)  # Source tables for this form


@dataclass
class Atributo:
    """Represents an attribute."""
    name: str  # Official name from Atributo.html (with correct accents)
    name_on_dataset: str  # Name as found in the dataset
    id: str
    file_path: str
    dataset_id: str
    applicationSchema: Optional[str] = None  # "Atributo" when found in Atributo.html
    formularios: List[Formulario] = field(default_factory=list)  # Attribute forms with their source tables


@dataclass
class Function:
    """Represents a function."""
    name: str
    file_path: str


@dataclass
class Fact:
    """Represents a fact."""
    name: str
    id: str
    file_path: str
    logic_tables: List[LogicTable] = field(default_factory=list)  # Source tables from EXPRESSÕES section


@dataclass
class Metrica:
    """Represents a metric."""
    name: str
    id: str
    file_path: str
    dataset_id: str
    tipo: str  # 'simples' or 'composto' (from "Tipo de métrica" field)
    applicationObject: Optional[str] = None  # "Metrica" when found in Métrica.html
    formula: Optional[str] = None
    function: Optional[Function] = None  # Function object (when tipo = simples)
    fact: Optional[Fact] = None  # Fact object (when tipo = simples)
    metricas: List['Metrica'] = field(default_factory=list)  # Component metrics (when tipo = composto)


@dataclass
class MetricaRelacao:
    """Represents a relationship between composite and component metrics."""
    parent_metrica_id: str
    child_metrica_id: str


@dataclass
class TabelaFonte:
    """Represents a source table."""
    name: str
    file_path: str

