"""Export data model to JSON and CSV formats."""

import json
import csv
from pathlib import Path
from typing import List, Dict, Set
from models import Relatorio


def serialize_metric(metrica) -> dict:
    """Recursively serialize a metric with all its fields and child metrics."""
    metrica_data = {
        'name': metrica.name,
        'id': metrica.id,
        'file_path': metrica.file_path,
        'applicationObject': metrica.applicationObject,
        'tipo': metrica.tipo,
        'formula': metrica.formula,
    }
    
    # Add function object if present (for simple metrics)
    if metrica.function:
        metrica_data['function'] = {
            'name': metrica.function.name,
            'file_path': metrica.function.file_path
        }
    else:
        metrica_data['function'] = None
    
    # Add fact object if present (for simple metrics)
    if metrica.fact:
        metrica_data['fact'] = {
            'name': metrica.fact.name,
            'id': metrica.fact.id,
            'file_path': metrica.fact.file_path,
            'logic_tables': [
                {
                    'name': lt.name,
                    'id': lt.id,
                    'file_path': lt.file_path,
                    'column_name': lt.column_name
                }
                for lt in metrica.fact.logic_tables
            ]
        }
    else:
        metrica_data['fact'] = None
    
    # Recursively add child metrics (for composite metrics)
    metrica_data['metricas'] = [
        serialize_metric(child) for child in metrica.metricas
    ]
    
    return metrica_data


def export_to_json(relatorios: List[Relatorio], output_path: Path):
    """Export data model to JSON format."""
    data = {
        'relatorios': []
    }
    
    for relatorio in relatorios:
        relatorio_data = {
            'name': relatorio.name,
            'id': relatorio.id,
            'file_path': relatorio.file_path,
            'datasets': []
        }
        
        for dataset in relatorio.datasets:
            dataset_data = {
                'name': dataset.name,
                'id': dataset.id,
                'file_path': dataset.file_path,
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
                    'file_path': atributo.file_path,
                    'applicationSchema': atributo.applicationSchema,
                    'formularios': []
                }
                
                for formulario in atributo.formularios:
                    formulario_data = {
                        'name': formulario.name,
                        'logic_tables': [
                            {
                                'name': lt.name,
                                'id': lt.id,
                                'file_path': lt.file_path,
                                'column_name': lt.column_name
                            }
                            for lt in formulario.logic_tables
                        ]
                    }
                    atributo_data['formularios'].append(formulario_data)
                
                dataset_data['atributos'].append(atributo_data)
            
            # Serialize metrics (including nested metrics for composite metrics)
            for metrica in dataset.metricas:
                dataset_data['metricas'].append(serialize_metric(metrica))
            
            relatorio_data['datasets'].append(dataset_data)
        
        data['relatorios'].append(relatorio_data)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_to_csv(relatorios: List[Relatorio], output_dir: Path):
    """Export data model to normalized CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect unique entities
    all_datasets = {}
    all_attributes = {}
    all_metrics = {}
    all_facts = {}
    all_functions = {}
    all_tables = {}
    all_attribute_forms = {}  # (attribute_id, form_name) -> form data
    
    # First pass: collect all unique entities
    for relatorio in relatorios:
        for dataset in relatorio.datasets:
            if dataset.id not in all_datasets:
                all_datasets[dataset.id] = dataset
            
            for atributo in dataset.atributos:
                if atributo.id not in all_attributes:
                    all_attributes[atributo.id] = atributo
                
                for formulario in atributo.formularios:
                    key = (atributo.id, formulario.name)
                    if key not in all_attribute_forms:
                        all_attribute_forms[key] = formulario
                    
                    for logic_table in formulario.logic_tables:
                        if logic_table.id and logic_table.id not in all_tables:
                            all_tables[logic_table.id] = logic_table
            
            # Collect metrics recursively
            def collect_metric(metrica):
                if metrica.id not in all_metrics:
                    all_metrics[metrica.id] = metrica
                
                if metrica.function:
                    # Functions don't have IDs, use name as key
                    func_key = metrica.function.name
                    if func_key not in all_functions:
                        all_functions[func_key] = metrica.function
                
                if metrica.fact:
                    if metrica.fact.id not in all_facts:
                        all_facts[metrica.fact.id] = metrica.fact
                    
                    for logic_table in metrica.fact.logic_tables:
                        if logic_table.id and logic_table.id not in all_tables:
                            all_tables[logic_table.id] = logic_table
                
                # Recurse for composite metrics
                for child_metrica in metrica.metricas:
                    collect_metric(child_metrica)
            
            for metrica in dataset.metricas:
                collect_metric(metrica)
    
    # ========== NORMALIZED TABLES (Entities) ==========
    
    # 1. Reports
    with open(output_dir / 'Reports.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'file_path'])
        for relatorio in relatorios:
            writer.writerow([relatorio.id, relatorio.name, relatorio.file_path])
    
    # 2. DataSets
    with open(output_dir / 'DataSets.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'file_path', 'applicationObject', 'graphic'])
        for dataset in all_datasets.values():
            writer.writerow([
                dataset.id,
                dataset.name,
                dataset.file_path,
                dataset.applicationObject or '',
                dataset.graphic or ''
            ])
    
    # 3. Attributes
    with open(output_dir / 'Attributes.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'name_on_dataset', 'file_path', 'applicationSchema'])
        for atributo in all_attributes.values():
            writer.writerow([
                atributo.id,
                atributo.name,
                atributo.name_on_dataset,
                atributo.file_path,
                atributo.applicationSchema or ''
            ])
    
    # 4. AttributesForm
    with open(output_dir / 'AttributesForm.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['attribute_id', 'form_name'])
        for (attr_id, form_name) in sorted(all_attribute_forms.keys()):
            writer.writerow([attr_id, form_name])
    
    # 5. Functions
    with open(output_dir / 'Functions.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'file_path'])
        for function in sorted(all_functions.values(), key=lambda x: x.name):
            writer.writerow([function.name, function.file_path])
    
    # 6. Metrics
    with open(output_dir / 'Metrics.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'file_path', 'applicationObject', 'tipo', 'formula'])
        for metrica in all_metrics.values():
            writer.writerow([
                metrica.id,
                metrica.name,
                metrica.file_path,
                metrica.applicationObject or '',
                metrica.tipo,
                metrica.formula or ''
            ])
    
    # 7. Facts
    with open(output_dir / 'Facts.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'file_path'])
        for fact in all_facts.values():
            writer.writerow([fact.id, fact.name, fact.file_path])
    
    # 8. Tables
    with open(output_dir / 'Tables.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'file_path'])
        for table in all_tables.values():
            writer.writerow([table.id, table.name, table.file_path or ''])
    
    # ========== RELATIONSHIP TABLES ==========
    
    # R1. Report_DataSet
    with open(output_dir / 'Report_DataSet.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['report_id', 'dataset_id'])
        for relatorio in relatorios:
            for dataset in relatorio.datasets:
                writer.writerow([relatorio.id, dataset.id])
    
    # R2. DataSet_Attribute
    with open(output_dir / 'DataSet_Attribute.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['dataset_id', 'attribute_id'])
        written = set()
        for relatorio in relatorios:
            for dataset in relatorio.datasets:
                for atributo in dataset.atributos:
                    key = (dataset.id, atributo.id)
                    if key not in written:
                        writer.writerow([dataset.id, atributo.id])
                        written.add(key)
    
    # R3. DataSet_Metric
    with open(output_dir / 'DataSet_Metric.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['dataset_id', 'metric_id'])
        written = set()
        for relatorio in relatorios:
            for dataset in relatorio.datasets:
                for metrica in dataset.metricas:
                    key = (dataset.id, metrica.id)
                    if key not in written:
                        writer.writerow([dataset.id, metrica.id])
                        written.add(key)
    
    # R4. AttributeForm_Table
    with open(output_dir / 'AttributeForm_Table.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['attribute_id', 'form_name', 'table_id', 'column_name'])
        for relatorio in relatorios:
            for dataset in relatorio.datasets:
                for atributo in dataset.atributos:
                    for formulario in atributo.formularios:
                        for logic_table in formulario.logic_tables:
                            writer.writerow([
                                atributo.id,
                                formulario.name,
                                logic_table.id,
                                logic_table.column_name or ''
                            ])
    
    # R5. Metric_Function
    with open(output_dir / 'Metric_Function.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['metric_id', 'function_name'])
        for metrica in all_metrics.values():
            if metrica.function:
                writer.writerow([metrica.id, metrica.function.name])
    
    # R6. Metric_Fact
    with open(output_dir / 'Metric_Fact.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['metric_id', 'fact_id'])
        for metrica in all_metrics.values():
            if metrica.fact:
                writer.writerow([metrica.id, metrica.fact.id])
    
    # R7. Fact_Table
    with open(output_dir / 'Fact_Table.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['fact_id', 'table_id', 'column_name'])
        for fact in all_facts.values():
            for logic_table in fact.logic_tables:
                writer.writerow([
                    fact.id,
                    logic_table.id,
                    logic_table.column_name or ''
                ])
    
    # R8. Metric_Metric (parent-child relationships for composite metrics)
    with open(output_dir / 'Metric_Metric.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['parent_metric_id', 'child_metric_id'])
        
        def write_metric_relationships(metrica):
            for child_metrica in metrica.metricas:
                writer.writerow([metrica.id, child_metrica.id])
                write_metric_relationships(child_metrica)
        
        for metrica in all_metrics.values():
            write_metric_relationships(metrica)


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
    
    def count_metric(metrica, counted_metrics: Set[str]):
        """Recursively count metrics."""
        if metrica.id not in counted_metrics:
            counted_metrics.add(metrica.id)
            unique_metrics.add(metrica.id)
            
            if metrica.tipo == 'simples':
                simple_metrics.add(metrica.id)
            else:
                composite_metrics.add(metrica.id)
            
            if metrica.function:
                unique_functions.add(metrica.function.name)
            
            if metrica.fact:
                unique_facts.add(metrica.fact.id)
                total_metric_facts_local = 1
                for lt in metrica.fact.logic_tables:
                    unique_tables.add(lt.id)
                return total_metric_facts_local, len(metrica.fact.logic_tables)
            
        return 0, 0
    
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
            
            counted_metrics_in_dataset = set()
            for metrica in dataset.metricas:
                total_dataset_metrics += 1
                mf, ft = count_metric(metrica, counted_metrics_in_dataset)
                total_metric_facts += mf
                total_fact_tables += ft
                
                # Count composite relationships
                def count_composite_rels(m):
                    count = 0
                    for child in m.metricas:
                        count += 1
                        count += count_composite_rels(child)
                        count_metric(child, counted_metrics_in_dataset)
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
