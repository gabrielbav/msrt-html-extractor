"""Export data model to JSON format."""

import json
from pathlib import Path
from typing import List, Optional
from microstrategy_extractor.core.models import Relatorio
from microstrategy_extractor.utils.logger import get_logger

logger = get_logger(__name__)


def _prepend_base_path(file_path: Optional[str], base_path: str) -> Optional[str]:
    """Prepend base_path to file_path if file_path is not None."""
    if file_path is None:
        return None
    return f"{base_path}/{file_path}"


def serialize_metric(metrica, base_path: str) -> dict:
    """Recursively serialize a metric with all its fields and child metrics."""
    metrica_data = {
        'name': metrica.name,
        'id': metrica.id,
        'migration_stage': metrica.migration_stage,
        'decision': metrica.decision,
        'file_path': _prepend_base_path(metrica.file_path, base_path),
        'applicationObject': metrica.applicationObject,
        'tipo': metrica.tipo,
        'formula': metrica.formula
    }
    
    # Add function object if present (for simple metrics)
    if metrica.function:
        metrica_data['function'] = {
            'name': metrica.function.name,
            'id': metrica.function.id,
            'migration_stage': metrica.function.migration_stage,
            'decision': metrica.function.decision,
            'file_path': _prepend_base_path(metrica.function.file_path, base_path)
        }
    else:
        metrica_data['function'] = None
    
    # Add fact object if present (for simple metrics)
    if metrica.fact:
        metrica_data['fact'] = {
            'name': metrica.fact.name,
            'id': metrica.fact.id,
            'migration_stage': metrica.fact.migration_stage,
            'decision': metrica.fact.decision,
            'file_path': _prepend_base_path(metrica.fact.file_path, base_path),
            'logic_tables': [
                {
                    'name': lt.name,
                    'id': lt.id,
                    'migration_stage': lt.migration_stage,
                    'decision': lt.decision,
                    'file_path': _prepend_base_path(lt.file_path, base_path),
                    'column_name': lt.column_name
                }
                for lt in metrica.fact.logic_tables
            ]
        }
    else:
        metrica_data['fact'] = None
    
    # Recursively add child metrics (for composite metrics)
    metrica_data['metricas'] = [
        serialize_metric(child, base_path) for child in metrica.metricas
    ]
    
    return metrica_data


def export_to_json(relatorios: List[Relatorio], output_path: Path, base_path: str = ""):
    """Export data model to JSON format."""
    logger.info(f"Exporting {len(relatorios)} reports to JSON: {output_path}")
    
    data = {
        'relatorios': []
    }
    
    for relatorio in relatorios:
        relatorio_data = {
            'name': relatorio.name,
            'id': relatorio.id,
            'migration_stage': relatorio.migration_stage,
            'decision': relatorio.decision,
            'file_path': _prepend_base_path(relatorio.file_path, base_path),
            'datasets': []
        }
        
        # Add owner if present
        if relatorio.owner:
            relatorio_data['owner'] = {
                'name': relatorio.owner.name,
                'id': relatorio.owner.id,
                'file_path': _prepend_base_path(relatorio.owner.file_path, base_path),
                'fullname': relatorio.owner.fullname,
                'access': relatorio.owner.access,
                'migration_stage': relatorio.owner.migration_stage,
                'decision': relatorio.owner.decision
            }
        else:
            relatorio_data['owner'] = None
        
        # Add access control
        relatorio_data['access_control'] = [
            {
                'name': ac.name,
                'access': ac.access,
                'fullname': ac.fullname,
                'id': ac.id,
                'migration_stage': ac.migration_stage,
                'decision': ac.decision,
                'file_path': _prepend_base_path(ac.file_path, base_path)
            }
            for ac in relatorio.access_control
        ]
        
        for dataset in relatorio.datasets:
            dataset_data = {
                'name': dataset.name,
                'id': dataset.id,
                'migration_stage': dataset.migration_stage,
                'decision': dataset.decision,
                'file_path': _prepend_base_path(dataset.file_path, base_path),
                'applicationObject': dataset.applicationObject,
                'graphic': dataset.graphic,
                'atributos': [],
                'metricas': []
            }
            
            for atributo in dataset.atributos:
                atributo_data = {
                    'name': atributo.name,  # Official name from Atributo.html
                    'name_on_dataset': atributo.name_on_dataset,  # Name as found in dataset
                    'id': atributo.id,
                    'migration_stage': atributo.migration_stage,
                    'decision': atributo.decision,
                    'file_path': _prepend_base_path(atributo.file_path, base_path),
                    'applicationSchema': atributo.applicationSchema,
                    'formularios': []
                }
                
                for formulario in atributo.formularios:
                    formulario_data = {
                        'id': formulario.id,
                        'name': formulario.name,
                        'migration_stage': formulario.migration_stage,
                        'decision': formulario.decision,
                        'logic_tables': [
                            {
                                'name': lt.name,
                                'id': lt.id,
                                'migration_stage': lt.migration_stage,
                                'decision': lt.decision,
                                'file_path': _prepend_base_path(lt.file_path, base_path),
                                'column_name': lt.column_name
                            }
                            for lt in formulario.logic_tables
                        ]
                    }
                    atributo_data['formularios'].append(formulario_data)
                
                dataset_data['atributos'].append(atributo_data)
            
            # Serialize metrics (including nested metrics for composite metrics)
            for metrica in dataset.metricas:
                dataset_data['metricas'].append(serialize_metric(metrica, base_path))
            
            relatorio_data['datasets'].append(dataset_data)
        
        data['relatorios'].append(relatorio_data)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Successfully exported to {output_path}")


def print_summary(relatorios: List[Relatorio]):
    """Print summary statistics of extracted data."""
    # Count unique IDs (to avoid counting duplicates from multiple reports)
    unique_datasets = set()
    unique_attributes = set()
    unique_attribute_forms = 0
    unique_metrics = set()
    unique_facts = set()
    unique_tables = set()
    unique_functions = set()
    
    # Count relationships (total, including reuses)
    total_report_datasets = 0
    total_dataset_attributes = 0
    total_dataset_metrics = 0
    total_attribute_forms = 0
    total_attribute_form_tables = 0
    total_metric_metrics = 0
    total_metric_facts = 0
    total_fact_tables = 0
    
    # Count metrics by type
    simple_metrics = set()
    composite_metrics = set()
    
    def collect_entities_from_metric(metrica):
        """Recursively collect facts, functions, and tables from metric hierarchy."""
        if metrica.tipo == 'simples':
            simple_metrics.add(metrica.id)
        else:
            composite_metrics.add(metrica.id)
        
        if metrica.function:
            unique_functions.add(metrica.function.name)
        
        if metrica.fact:
            unique_facts.add(metrica.fact.id)
            for lt in metrica.fact.logic_tables:
                unique_tables.add(lt.id)
        
        # Recursively process child metrics to collect their entities
        for child in metrica.metricas:
            collect_entities_from_metric(child)
    
    for relatorio in relatorios:
        for dataset in relatorio.datasets:
            unique_datasets.add(dataset.id)
            total_report_datasets += 1
            
            for atributo in dataset.atributos:
                unique_attributes.add(atributo.id)
                total_dataset_attributes += 1
                
                for formulario in atributo.formularios:
                    unique_attribute_forms += 1
                    total_attribute_forms += 1
                    for lt in formulario.logic_tables:
                        unique_tables.add(lt.id)
                        total_attribute_form_tables += 1
            
            # Count only dataset-level metrics (the "columns" in the report)
            # Don't recursively count child metrics as separate entities
            for metrica in dataset.metricas:
                total_dataset_metrics += 1
                unique_metrics.add(metrica.id)  # Only count dataset-level metrics
                
                # Collect entities (facts, functions, tables) from entire metric hierarchy
                collect_entities_from_metric(metrica)
                
                # Count facts for this metric and its children
                if metrica.fact:
                    total_metric_facts += 1
                    total_fact_tables += len(metrica.fact.logic_tables)
                
                # Count composite relationships
                def count_composite_rels(m):
                    count = 0
                    for child in m.metricas:
                        count += 1
                        count += count_composite_rels(child)
                        if child.fact:
                            nonlocal total_metric_facts, total_fact_tables
                            total_metric_facts += 1
                            total_fact_tables += len(child.fact.logic_tables)
                    return count
                
                total_metric_metrics += count_composite_rels(metrica)
    
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY (UNIQUE IDs)")
    print("=" * 60)
    print(f"Total Reports: {len(relatorios)}")
    print(f"Total DataSets: {len(unique_datasets)}")
    print(f"Total Attributes: {len(unique_attributes)}")
    print(f"Total AttributesForm: {unique_attribute_forms}")
    print(f"Total Metrics: {len(unique_metrics)}")
    print(f"  - Simples: {len(simple_metrics)}")
    print(f"  - Compostas: {len(composite_metrics)}")
    print(f"Total Facts: {len(unique_facts)}")
    print(f"Total Functions: {len(unique_functions)}")
    print(f"Total Tables: {len(unique_tables)}")
    print()
    print("Relationships:")
    print(f"  Report -> DataSets: {total_report_datasets}")
    print(f"  DataSet -> Attributes: {total_dataset_attributes}")
    print(f"  DataSet -> Metrics: {total_dataset_metrics}")
    print(f"  Attribute -> AttributeForm: {total_attribute_forms}")
    print(f"  AttributeForm -> Tables: {total_attribute_form_tables}")
    print(f"  Metric -> Metrics: {total_metric_metrics}")
    print(f"  Metric -> Facts: {total_metric_facts}")
    print(f"  Fact -> Tables: {total_fact_tables}")
    print("=" * 60)
    print()


class JSONExporter:
    """Class-based JSON exporter for the new architecture."""
    
    def __init__(self, output_path: Path):
        """Initialize the JSON exporter.
        
        Args:
            output_path: Path to output JSON file
        """
        self.output_path = Path(output_path)
    
    def export(self, relatorios: List[Relatorio]):
        """Export relatorios to JSON.
        
        Args:
            relatorios: List of Relatorio objects to export
        """
        export_to_json(relatorios, self.output_path)
    
    def export_with_summary(self, relatorios: List[Relatorio]):
        """Export relatorios to JSON and print summary.
        
        Args:
            relatorios: List of Relatorio objects to export
        """
        print_summary(relatorios)
        self.export(relatorios)

