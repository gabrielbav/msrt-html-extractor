#!/usr/bin/env python3
"""
Script to normalize the output.json into CSV files with proper relational structure.
"""

import json
import csv
import os
from typing import Dict, List, Set, Any
from collections import defaultdict


class DataNormalizer:
    def __init__(self, json_file_path: str, output_dir: str):
        self.json_file_path = json_file_path
        self.output_dir = output_dir
        
        # Main entity tables
        self.reports: List[Dict] = []
        self.datasets: List[Dict] = []
        self.attributes: List[Dict] = []
        self.attributes_forms: List[Dict] = []
        self.functions: List[Dict] = []
        self.metrics: List[Dict] = []
        self.facts: List[Dict] = []
        self.tables: List[Dict] = []
        
        # Relationship tables
        self.report_datasets: List[Dict] = []
        self.dataset_attributes: List[Dict] = []
        self.dataset_metrics: List[Dict] = []
        self.attribute_forms: List[Dict] = []
        self.form_tables: List[Dict] = []
        self.metric_metrics: List[Dict] = []
        self.metric_facts: List[Dict] = []
        self.metric_functions: List[Dict] = []
        self.fact_tables: List[Dict] = []
        
        # Sets to track unique entities
        self.seen_reports: Set[str] = set()
        self.seen_datasets: Set[str] = set()
        self.seen_attributes: Set[str] = set()
        self.seen_forms: Set[str] = set()
        self.seen_functions: Set[str] = set()
        self.seen_metrics: Set[str] = set()
        self.seen_facts: Set[str] = set()
        self.seen_tables: Set[str] = set()
        
        # Counters for entities without IDs
        self.form_counter = 0
        self.function_counter = 0
        
    def load_json(self) -> Dict:
        """Load the JSON file."""
        print(f"Loading JSON from {self.json_file_path}...")
        with open(self.json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_form_id(self, attribute_id: str, form_name: str) -> str:
        """Generate a unique ID for a form."""
        self.form_counter += 1
        return f"FORM_{attribute_id}_{self.form_counter}"
    
    def extract_function_id(self, file_path: str) -> str:
        """Extract function ID from file_path or generate one."""
        if '#' in file_path:
            return file_path.split('#')[-1]
        self.function_counter += 1
        return f"FUNC_{self.function_counter}"
    
    def process_table(self, table_data: Dict, parent_type: str, parent_id: str) -> None:
        """Process a logic table."""
        table_id = table_data.get('id')
        
        if table_id and table_id not in self.seen_tables:
            self.tables.append({
                'id': table_id,
                'name': table_data.get('name', ''),
                'file_path': table_data.get('file_path', '')
            })
            self.seen_tables.add(table_id)
        
        # Create relationship based on parent type
        if parent_type == 'form' and table_id:
            self.form_tables.append({
                'form_id': parent_id,
                'table_id': table_id,
                'column_name': table_data.get('column_name', '')
            })
        elif parent_type == 'fact' and table_id:
            self.fact_tables.append({
                'fact_id': parent_id,
                'table_id': table_id,
                'column_name': table_data.get('column_name', '')
            })
    
    def process_fact(self, fact_data: Dict) -> str:
        """Process a fact and return its ID."""
        fact_id = fact_data.get('id')
        
        if fact_id and fact_id not in self.seen_facts:
            self.facts.append({
                'id': fact_id,
                'name': fact_data.get('name', ''),
                'file_path': fact_data.get('file_path', '')
            })
            self.seen_facts.add(fact_id)
            
            # Process logic tables
            for table_data in fact_data.get('logic_tables', []):
                self.process_table(table_data, 'fact', fact_id)
        
        return fact_id
    
    def process_function(self, function_data: Dict) -> str:
        """Process a function and return its ID."""
        function_name = function_data.get('name', '')
        file_path = function_data.get('file_path', '')
        function_id = self.extract_function_id(file_path)
        
        if function_id not in self.seen_functions:
            self.functions.append({
                'id': function_id,
                'name': function_name,
                'file_path': file_path
            })
            self.seen_functions.add(function_id)
        
        return function_id
    
    def process_metric(self, metric_data: Dict, parent_dataset_id: str = None, 
                      parent_metric_id: str = None) -> str:
        """Process a metric (can be simple or composite) and return its ID."""
        metric_id = metric_data.get('id')
        
        if metric_id and metric_id not in self.seen_metrics:
            metric = {
                'id': metric_id,
                'name': metric_data.get('name', ''),
                'file_path': metric_data.get('file_path', ''),
                'application_object': metric_data.get('applicationObject', ''),
                'tipo': metric_data.get('tipo', ''),
                'formula': metric_data.get('formula', '')
            }
            self.metrics.append(metric)
            self.seen_metrics.add(metric_id)
            
            # Process function if exists (simple metrics)
            if 'function' in metric_data and metric_data['function']:
                function_id = self.process_function(metric_data['function'])
                self.metric_functions.append({
                    'metric_id': metric_id,
                    'function_id': function_id
                })
            
            # Process fact if exists (simple metrics)
            if 'fact' in metric_data and metric_data['fact']:
                fact_id = self.process_fact(metric_data['fact'])
                if fact_id:
                    self.metric_facts.append({
                        'metric_id': metric_id,
                        'fact_id': fact_id
                    })
            
            # Process nested metrics (composite metrics)
            for nested_metric in metric_data.get('metricas', []):
                child_metric_id = self.process_metric(nested_metric, None, metric_id)
                if child_metric_id:
                    self.metric_metrics.append({
                        'parent_metric_id': metric_id,
                        'child_metric_id': child_metric_id
                    })
        
        # Create relationship with parent dataset
        if parent_dataset_id and metric_id:
            self.dataset_metrics.append({
                'dataset_id': parent_dataset_id,
                'metric_id': metric_id
            })
        
        return metric_id
    
    def process_form(self, form_data: Dict, attribute_id: str) -> str:
        """Process an attribute form and return its ID."""
        form_name = form_data.get('name', '')
        form_id = self.generate_form_id(attribute_id, form_name)
        
        if form_id not in self.seen_forms:
            self.attributes_forms.append({
                'id': form_id,
                'name': form_name,
                'attribute_id': attribute_id
            })
            self.seen_forms.add(form_id)
            
            # Process logic tables
            for table_data in form_data.get('logic_tables', []):
                self.process_table(table_data, 'form', form_id)
        
        # Create relationship
        self.attribute_forms.append({
            'attribute_id': attribute_id,
            'form_id': form_id
        })
        
        return form_id
    
    def process_attribute(self, attribute_data: Dict, dataset_id: str) -> None:
        """Process an attribute."""
        attribute_id = attribute_data.get('id')
        
        if attribute_id and attribute_id not in self.seen_attributes:
            self.attributes.append({
                'id': attribute_id,
                'name': attribute_data.get('name', ''),
                'name_on_dataset': attribute_data.get('name_on_dataset', ''),
                'file_path': attribute_data.get('file_path', ''),
                'application_schema': attribute_data.get('applicationSchema', '')
            })
            self.seen_attributes.add(attribute_id)
            
            # Process forms
            for form_data in attribute_data.get('formularios', []):
                self.process_form(form_data, attribute_id)
        
        # Create relationship with dataset
        if attribute_id:
            self.dataset_attributes.append({
                'dataset_id': dataset_id,
                'attribute_id': attribute_id
            })
    
    def process_dataset(self, dataset_data: Dict, report_id: str) -> None:
        """Process a dataset."""
        dataset_id = dataset_data.get('id')
        
        if dataset_id and dataset_id not in self.seen_datasets:
            self.datasets.append({
                'id': dataset_id,
                'name': dataset_data.get('name', ''),
                'file_path': dataset_data.get('file_path', ''),
                'application_object': dataset_data.get('applicationObject', '')
            })
            self.seen_datasets.add(dataset_id)
            
            # Process attributes
            for attribute_data in dataset_data.get('atributos', []):
                self.process_attribute(attribute_data, dataset_id)
            
            # Process metrics
            for metric_data in dataset_data.get('metricas', []):
                self.process_metric(metric_data, dataset_id, None)
        
        # Create relationship with report
        if dataset_id:
            self.report_datasets.append({
                'report_id': report_id,
                'dataset_id': dataset_id
            })
    
    def process_report(self, report_data: Dict) -> None:
        """Process a report."""
        report_id = report_data.get('id')
        
        if report_id and report_id not in self.seen_reports:
            self.reports.append({
                'id': report_id,
                'name': report_data.get('name', ''),
                'file_path': report_data.get('file_path', '')
            })
            self.seen_reports.add(report_id)
            
            # Process datasets
            for dataset_data in report_data.get('datasets', []):
                self.process_dataset(dataset_data, report_id)
    
    def normalize(self) -> None:
        """Main normalization process."""
        data = self.load_json()
        
        print("Processing reports...")
        for report_data in data.get('relatorios', []):
            self.process_report(report_data)
        
        print(f"\nProcessing complete!")
        print(f"  Reports: {len(self.reports)}")
        print(f"  Datasets: {len(self.datasets)}")
        print(f"  Attributes: {len(self.attributes)}")
        print(f"  Attribute Forms: {len(self.attributes_forms)}")
        print(f"  Functions: {len(self.functions)}")
        print(f"  Metrics: {len(self.metrics)}")
        print(f"  Facts: {len(self.facts)}")
        print(f"  Tables: {len(self.tables)}")
    
    def write_csv(self, filename: str, data: List[Dict], fieldnames: List[str]) -> None:
        """Write data to a CSV file."""
        if not data:
            print(f"  Skipping {filename} (no data)")
            return
        
        filepath = os.path.join(self.output_dir, filename)
        print(f"  Writing {filename} ({len(data)} rows)...")
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    
    def export_to_csv(self) -> None:
        """Export all normalized data to CSV files."""
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"\nExporting to CSV files in {self.output_dir}...")
        
        # Main entity tables
        self.write_csv('reports.csv', self.reports, 
                      ['id', 'name', 'file_path'])
        
        self.write_csv('datasets.csv', self.datasets, 
                      ['id', 'name', 'file_path', 'application_object'])
        
        self.write_csv('attributes.csv', self.attributes, 
                      ['id', 'name', 'name_on_dataset', 'file_path', 'application_schema'])
        
        self.write_csv('attributes_forms.csv', self.attributes_forms, 
                      ['id', 'name', 'attribute_id'])
        
        self.write_csv('functions.csv', self.functions, 
                      ['id', 'name', 'file_path'])
        
        self.write_csv('metrics.csv', self.metrics, 
                      ['id', 'name', 'file_path', 'application_object', 'tipo', 'formula'])
        
        self.write_csv('facts.csv', self.facts, 
                      ['id', 'name', 'file_path'])
        
        self.write_csv('tables.csv', self.tables, 
                      ['id', 'name', 'file_path'])
        
        # Relationship tables
        self.write_csv('report_datasets.csv', self.report_datasets, 
                      ['report_id', 'dataset_id'])
        
        self.write_csv('dataset_attributes.csv', self.dataset_attributes, 
                      ['dataset_id', 'attribute_id'])
        
        self.write_csv('dataset_metrics.csv', self.dataset_metrics, 
                      ['dataset_id', 'metric_id'])
        
        self.write_csv('attribute_forms.csv', self.attribute_forms, 
                      ['attribute_id', 'form_id'])
        
        self.write_csv('form_tables.csv', self.form_tables, 
                      ['form_id', 'table_id', 'column_name'])
        
        self.write_csv('metric_metrics.csv', self.metric_metrics, 
                      ['parent_metric_id', 'child_metric_id'])
        
        self.write_csv('metric_facts.csv', self.metric_facts, 
                      ['metric_id', 'fact_id'])
        
        self.write_csv('metric_functions.csv', self.metric_functions, 
                      ['metric_id', 'function_id'])
        
        self.write_csv('fact_tables.csv', self.fact_tables, 
                      ['fact_id', 'table_id', 'column_name'])
        
        print("\nExport complete!")


def main():
    json_file = '/Users/gvieira/BlankProject/output.json'
    output_dir = '/Users/gvieira/BlankProject/output_csv'
    
    normalizer = DataNormalizer(json_file, output_dir)
    normalizer.normalize()
    normalizer.export_to_csv()
    
    print("\n✓ Data normalization completed successfully!")


if __name__ == '__main__':
    main()

