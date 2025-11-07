"""Data validation using Pydantic models."""

from typing import List, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator, ValidationError as PydanticValidationError

from models import Relatorio, DataSet, Atributo, Metrica, Fact, Function, LogicTable, Formulario
from utils.logger import get_logger
from exceptions import ValidationError

logger = get_logger(__name__)


# ============================================================================
# Pydantic Models for Validation
# ============================================================================

class ValidatedLogicTable(BaseModel):
    """Validated LogicTable model."""
    name: str = Field(..., min_length=1)
    id: str = Field(..., pattern=r'^[A-F0-9]{32}$')
    file_path: Optional[str] = None
    column_name: Optional[str] = None


class ValidatedFunction(BaseModel):
    """Validated Function model."""
    name: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)


class ValidatedFact(BaseModel):
    """Validated Fact model."""
    name: str = Field(..., min_length=1)
    id: str = Field(..., pattern=r'^[A-F0-9]{32}$')
    file_path: str = Field(..., min_length=1)
    logic_tables: List[ValidatedLogicTable] = Field(default_factory=list)
    
    @validator('logic_tables')
    def check_has_logic_tables(cls, v):
        """Warn if fact has no logic tables."""
        if not v:
            logger.warning("Fact has no logic tables")
        return v


class ValidatedMetrica(BaseModel):
    """Validated Metrica model."""
    name: str = Field(..., min_length=1)
    id: str = Field(..., pattern=r'^[A-F0-9]{32}$')
    file_path: str = Field(..., min_length=1)
    tipo: str = Field(..., pattern=r'^(simples|composto)$')
    applicationObject: Optional[str] = None
    formula: Optional[str] = None
    
    # For simple metrics
    function: Optional[ValidatedFunction] = None
    fact: Optional[ValidatedFact] = None
    
    # For composite metrics
    metricas: List['ValidatedMetrica'] = Field(default_factory=list)
    
    @validator('fact')
    def check_simple_has_fact(cls, v, values):
        """Check that simple metrics have a fact."""
        if values.get('tipo') == 'simples' and not v:
            logger.warning(f"Simple metric missing fact: {values.get('name')}")
        return v
    
    @validator('metricas')
    def check_composite_has_components(cls, v, values):
        """Check that composite metrics have component metrics."""
        if values.get('tipo') == 'composto' and not v:
            logger.warning(f"Composite metric has no components: {values.get('name')}")
        return v


class ValidatedFormulario(BaseModel):
    """Validated Formulario model."""
    name: str = Field(..., min_length=1)
    logic_tables: List[ValidatedLogicTable] = Field(default_factory=list)
    
    @validator('logic_tables')
    def check_has_tables(cls, v):
        """Check that form has at least one logic table."""
        if not v:
            logger.warning("Form has no logic tables")
        return v


class ValidatedAtributo(BaseModel):
    """Validated Atributo model."""
    name: str = Field(..., min_length=1)
    name_on_dataset: str = Field(..., min_length=1)
    id: str = Field(..., pattern=r'^[A-F0-9]{32}$')
    file_path: str = Field(..., min_length=1)
    applicationSchema: Optional[str] = None
    formularios: List[ValidatedFormulario] = Field(default_factory=list)
    
    @validator('formularios')
    def check_has_formularios(cls, v):
        """Warn if attribute has no forms."""
        if not v:
            logger.warning("Attribute has no forms")
        return v


class ValidatedDataSet(BaseModel):
    """Validated DataSet model."""
    name: str = Field(..., min_length=1)
    id: str = Field(..., pattern=r'^[A-F0-9a-f-]{32,36}$')  # Allow UUID format too
    file_path: str
    applicationObject: Optional[str] = None
    graphic: Optional[str] = None
    atributos: List[ValidatedAtributo] = Field(default_factory=list)
    metricas: List[ValidatedMetrica] = Field(default_factory=list)
    
    @validator('atributos', 'metricas')
    def check_has_content(cls, v, field):
        """Warn if dataset has no attributes or metrics."""
        if not v:
            logger.warning(f"Dataset has no {field.name}")
        return v


class ValidatedRelatorio(BaseModel):
    """Validated Relatorio model."""
    name: str = Field(..., min_length=1)
    id: str = Field(..., pattern=r'^[A-F0-9]{32}$')
    file_path: str = Field(..., min_length=1)
    datasets: List[ValidatedDataSet] = Field(default_factory=list)
    
    @validator('datasets')
    def check_has_datasets(cls, v):
        """Check that report has at least one dataset."""
        if not v:
            raise ValueError('Report must have at least one dataset')
        return v


# ============================================================================
# Validation Results
# ============================================================================

@dataclass
class ValidationResult:
    """Results from data validation."""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_count: int = 0
    
    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.validated_count += other.validated_count
        if not other.valid:
            self.valid = False


# ============================================================================
# Data Validator
# ============================================================================

class DataValidator:
    """Validator for extracted data using Pydantic models."""
    
    def __init__(self, strict: bool = False):
        """
        Initialize validator.
        
        Args:
            strict: If True, warnings are treated as errors
        """
        self.strict = strict
    
    def validate_relatorio(self, relatorio: Relatorio) -> ValidationResult:
        """
        Validate a single report.
        
        Args:
            relatorio: Relatorio object to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        result.validated_count = 1
        
        try:
            # Convert to dict for Pydantic
            rel_dict = self._relatorio_to_dict(relatorio)
            
            # Validate with Pydantic
            ValidatedRelatorio(**rel_dict)
            
            logger.debug(f"Validation passed for report: {relatorio.name}")
            
        except PydanticValidationError as e:
            for error in e.errors():
                error_msg = f"Report '{relatorio.name}' ({relatorio.id}): {error['msg']} at {error['loc']}"
                result.add_error(error_msg)
                logger.error(error_msg)
        except Exception as e:
            error_msg = f"Unexpected validation error for report '{relatorio.name}': {e}"
            result.add_error(error_msg)
            logger.error(error_msg)
        
        return result
    
    def validate_extraction(self, relatorios: List[Relatorio]) -> ValidationResult:
        """
        Validate complete extraction results.
        
        Args:
            relatorios: List of Relatorio objects
            
        Returns:
            ValidationResult with aggregated errors and warnings
        """
        overall_result = ValidationResult()
        
        logger.info(f"Validating {len(relatorios)} reports")
        
        for i, relatorio in enumerate(relatorios, 1):
            logger.debug(f"Validating report {i}/{len(relatorios)}: {relatorio.name}")
            
            result = self.validate_relatorio(relatorio)
            overall_result.merge(result)
        
        # Summary
        logger.info(f"Validation complete: {overall_result.validated_count} reports")
        if overall_result.errors:
            logger.warning(f"Found {len(overall_result.errors)} errors")
        if overall_result.warnings:
            logger.info(f"Found {len(overall_result.warnings)} warnings")
        
        return overall_result
    
    def _relatorio_to_dict(self, relatorio: Relatorio) -> dict:
        """Convert Relatorio to dict for Pydantic validation."""
        return {
            'name': relatorio.name,
            'id': relatorio.id,
            'file_path': relatorio.file_path,
            'datasets': [self._dataset_to_dict(ds) for ds in relatorio.datasets]
        }
    
    def _dataset_to_dict(self, dataset: DataSet) -> dict:
        """Convert DataSet to dict."""
        return {
            'name': dataset.name,
            'id': dataset.id,
            'file_path': dataset.file_path,
            'applicationObject': dataset.applicationObject,
            'graphic': dataset.graphic,
            'atributos': [self._atributo_to_dict(attr) for attr in dataset.atributos],
            'metricas': [self._metrica_to_dict(m) for m in dataset.metricas]
        }
    
    def _atributo_to_dict(self, atributo: Atributo) -> dict:
        """Convert Atributo to dict."""
        return {
            'name': atributo.name,
            'name_on_dataset': atributo.name_on_dataset,
            'id': atributo.id,
            'file_path': atributo.file_path,
            'applicationSchema': atributo.applicationSchema,
            'formularios': [self._formulario_to_dict(f) for f in atributo.formularios]
        }
    
    def _formulario_to_dict(self, formulario: Formulario) -> dict:
        """Convert Formulario to dict."""
        return {
            'name': formulario.name,
            'logic_tables': [self._logic_table_to_dict(lt) for lt in formulario.logic_tables]
        }
    
    def _metrica_to_dict(self, metrica: Metrica) -> dict:
        """Convert Metrica to dict."""
        return {
            'name': metrica.name,
            'id': metrica.id,
            'file_path': metrica.file_path,
            'tipo': metrica.tipo,
            'applicationObject': metrica.applicationObject,
            'formula': metrica.formula,
            'function': self._function_to_dict(metrica.function) if metrica.function else None,
            'fact': self._fact_to_dict(metrica.fact) if metrica.fact else None,
            'metricas': [self._metrica_to_dict(m) for m in metrica.metricas]
        }
    
    def _function_to_dict(self, function: Function) -> dict:
        """Convert Function to dict."""
        return {
            'name': function.name,
            'file_path': function.file_path
        }
    
    def _fact_to_dict(self, fact: Fact) -> dict:
        """Convert Fact to dict."""
        return {
            'name': fact.name,
            'id': fact.id,
            'file_path': fact.file_path,
            'logic_tables': [self._logic_table_to_dict(lt) for lt in fact.logic_tables]
        }
    
    def _logic_table_to_dict(self, logic_table: LogicTable) -> dict:
        """Convert LogicTable to dict."""
        return {
            'name': logic_table.name,
            'id': logic_table.id,
            'file_path': logic_table.file_path,
            'column_name': logic_table.column_name
        }

