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
    migration_stage: Optional[str] = None
    decision: Optional[str] = None
    owner: Optional['Owner'] = None
    access_control: List['AccessControlEntry'] = field(default_factory=list)


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
    migration_stage: Optional[str] = None
    decision: Optional[str] = None


@dataclass
class LogicTable:
    """Represents a logical table (source table)."""
    name: str
    id: str
    file_path: Optional[str] = None
    column_name: Optional[str] = None  # Column name from EXPRESSÃO field
    migration_stage: Optional[str] = None
    decision: Optional[str] = None


@dataclass
class Formulario:
    """Represents an attribute form."""
    id: str  # Generated ID (hash of attribute_id + form_name)
    name: str  # Form name (e.g., "ID", "Codigo Agência", "Nome Agência")
    logic_tables: List['LogicTable'] = field(default_factory=list)  # Source tables for this form
    migration_stage: Optional[str] = None
    decision: Optional[str] = None


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
    migration_stage: Optional[str] = None
    decision: Optional[str] = None


@dataclass
class Function:
    """Represents a function."""
    name: str
    id: str
    file_path: str
    migration_stage: Optional[str] = None
    decision: Optional[str] = None


@dataclass
class Fact:
    """Represents a fact."""
    name: str
    id: str
    file_path: str
    logic_tables: List[LogicTable] = field(default_factory=list)  # Source tables from EXPRESSÕES section
    migration_stage: Optional[str] = None
    decision: Optional[str] = None


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
    migration_stage: Optional[str] = None
    decision: Optional[str] = None


@dataclass
class MetricaRelacao:
    """Represents a relationship between composite and component metrics."""
    parent_metrica_id: str
    child_metrica_id: str


@dataclass
class Owner:
    """Represents an owner (user)."""
    name: str
    id: str
    file_path: str
    fullname: Optional[str] = None
    access: Optional[str] = None
    migration_stage: Optional[str] = None
    decision: Optional[str] = None


@dataclass
class AccessControlEntry:
    """Represents an access control entry."""
    name: str
    access: str
    fullname: Optional[str] = None
    id: Optional[str] = None
    migration_stage: Optional[str] = None
    decision: Optional[str] = None
    file_path: Optional[str] = None


@dataclass
class TabelaFonte:
    """Represents a source table."""
    name: str
    file_path: str

