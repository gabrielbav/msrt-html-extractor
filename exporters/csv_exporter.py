"""Unified CSV export logic - single source of truth for CSV generation."""

import csv
from pathlib import Path
from typing import List, Dict, Set
from models import Relatorio
from constants import CSVFiles
from utils.logger import get_logger
from exceptions import ExportError

logger = get_logger(__name__)


class CSVExporter:
    """Unified CSV exporter for relatorio data."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize CSV exporter.
        
        Args:
            output_dir: Directory for CSV output files
        """
        self.output_dir = Path(output_dir)
    
    def export(self, relatorios: List[Relatorio]) -> None:
        """
        Export relatorios to normalized CSV structure.
        
        Args:
            relatorios: List of Relatorio objects to export
            
        Raises:
            ExportError: If export fails
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Exporting {len(relatorios)} reports to CSV in {self.output_dir}")
            
            # Export entities
            self._export_entities(relatorios)
            
            # Export relationships
            self._export_relationships(relatorios)
            
            logger.info("CSV export completed successfully")
            
        except Exception as e:
            raise ExportError(f"Failed to export CSV: {e}", self.output_dir, "CSV")
    
    def _export_entities(self, relatorios: List[Relatorio]) -> None:
        """Export entity tables (Reports, DataSets, Attributes, etc.)."""
        # Collect unique entities
        all_datasets = {}
        all_attributes = {}
        all_metrics = {}
        all_facts = {}
        all_functions = {}
        all_tables = {}
        
        for relatorio in relatorios:
            for dataset in relatorio.datasets:
                if dataset.id not in all_datasets:
                    all_datasets[dataset.id] = dataset
                
                for atributo in dataset.atributos:
                    if atributo.id not in all_attributes:
                        all_attributes[atributo.id] = atributo
                    
                    for formulario in atributo.formularios:
                        for logic_table in formulario.logic_tables:
                            if logic_table.id and logic_table.id not in all_tables:
                                all_tables[logic_table.id] = logic_table
                
                # Collect metrics recursively
                for metrica in dataset.metricas:
                    self._collect_metric_recursive(metrica, all_metrics, all_functions, all_facts, all_tables)
        
        # Write entity CSV files
        self._write_reports_csv(relatorios)
        self._write_datasets_csv(all_datasets)
        self._write_attributes_csv(all_attributes)
        self._write_metrics_csv(all_metrics)
        self._write_facts_csv(all_facts)
        self._write_functions_csv(all_functions)
        self._write_tables_csv(all_tables)
    
    def _collect_metric_recursive(self, metrica, all_metrics, all_functions, all_facts, all_tables):
        """Recursively collect metric and related objects."""
        if metrica.id not in all_metrics:
            all_metrics[metrica.id] = metrica
            
            if metrica.function:
                func_key = metrica.function.name
                if func_key not in all_functions:
                    all_functions[func_key] = metrica.function
            
            if metrica.fact:
                if metrica.fact.id not in all_facts:
                    all_facts[metrica.fact.id] = metrica.fact
                
                for logic_table in metrica.fact.logic_tables:
                    if logic_table.id and logic_table.id not in all_tables:
                        all_tables[logic_table.id] = logic_table
            
            for child_metrica in metrica.metricas:
                self._collect_metric_recursive(child_metrica, all_metrics, all_functions, all_facts, all_tables)
    
    def _export_relationships(self, relatorios: List[Relatorio]) -> None:
        """Export relationship tables."""
        self._write_report_dataset_csv(relatorios)
        self._write_dataset_attribute_csv(relatorios)
        self._write_dataset_metric_csv(relatorios)
        self._write_attribute_form_table_csv(relatorios)
        self._write_metric_function_csv(relatorios)
        self._write_metric_fact_csv(relatorios)
        self._write_fact_table_csv(relatorios)
        self._write_metric_metric_csv(relatorios)
    
    def _write_reports_csv(self, relatorios: List[Relatorio]):
        """Write Reports.csv."""
        file_path = self.output_dir / CSVFiles.REPORTS
        logger.debug(f"Writing {file_path}")
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'file_path'])
            for relatorio in relatorios:
                writer.writerow([relatorio.id, relatorio.name, relatorio.file_path])
    
    def _write_datasets_csv(self, all_datasets: Dict):
        """Write DataSets.csv."""
        file_path = self.output_dir / CSVFiles.DATASETS
        logger.debug(f"Writing {file_path}")
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
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
    
    def _write_attributes_csv(self, all_attributes: Dict):
        """Write Attributes.csv."""
        file_path = self.output_dir / CSVFiles.ATTRIBUTES
        logger.debug(f"Writing {file_path}")
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
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
    
    def _write_metrics_csv(self, all_metrics: Dict):
        """Write Metrics.csv."""
        file_path = self.output_dir / CSVFiles.METRICS
        logger.debug(f"Writing {file_path}")
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
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
    
    def _write_facts_csv(self, all_facts: Dict):
        """Write Facts.csv."""
        file_path = self.output_dir / CSVFiles.FACTS
        logger.debug(f"Writing {file_path}")
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'file_path'])
            for fact in all_facts.values():
                writer.writerow([fact.id, fact.name, fact.file_path])
    
    def _write_functions_csv(self, all_functions: Dict):
        """Write Functions.csv."""
        file_path = self.output_dir / CSVFiles.FUNCTIONS
        logger.debug(f"Writing {file_path}")
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'file_path'])
            for function in sorted(all_functions.values(), key=lambda x: x.name):
                writer.writerow([function.name, function.file_path])
    
    def _write_tables_csv(self, all_tables: Dict):
        """Write Tables.csv."""
        file_path = self.output_dir / CSVFiles.TABLES
        logger.debug(f"Writing {file_path}")
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'file_path'])
            for table in all_tables.values():
                writer.writerow([table.id, table.name, table.file_path or ''])
    
    def _write_report_dataset_csv(self, relatorios: List[Relatorio]):
        """Write Report_DataSet.csv."""
        file_path = self.output_dir / CSVFiles.REPORT_DATASET
        logger.debug(f"Writing {file_path}")
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['report_id', 'dataset_id'])
            for relatorio in relatorios:
                for dataset in relatorio.datasets:
                    writer.writerow([relatorio.id, dataset.id])
    
    def _write_dataset_attribute_csv(self, relatorios: List[Relatorio]):
        """Write DataSet_Attribute.csv."""
        file_path = self.output_dir / CSVFiles.DATASET_ATTRIBUTE
        logger.debug(f"Writing {file_path}")
        
        written = set()
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['dataset_id', 'attribute_id'])
            for relatorio in relatorios:
                for dataset in relatorio.datasets:
                    for atributo in dataset.atributos:
                        key = (dataset.id, atributo.id)
                        if key not in written:
                            writer.writerow([dataset.id, atributo.id])
                            written.add(key)
    
    def _write_dataset_metric_csv(self, relatorios: List[Relatorio]):
        """Write DataSet_Metric.csv."""
        file_path = self.output_dir / CSVFiles.DATASET_METRIC
        logger.debug(f"Writing {file_path}")
        
        written = set()
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['dataset_id', 'metric_id'])
            for relatorio in relatorios:
                for dataset in relatorio.datasets:
                    for metrica in dataset.metricas:
                        key = (dataset.id, metrica.id)
                        if key not in written:
                            writer.writerow([dataset.id, metrica.id])
                            written.add(key)
    
    def _write_attribute_form_table_csv(self, relatorios: List[Relatorio]):
        """Write AttributeForm_Table.csv."""
        file_path = self.output_dir / CSVFiles.ATTRIBUTE_FORM_TABLE
        logger.debug(f"Writing {file_path}")
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
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
    
    def _write_metric_function_csv(self, relatorios: List[Relatorio]):
        """Write Metric_Function.csv."""
        file_path = self.output_dir / CSVFiles.METRIC_FUNCTION
        logger.debug(f"Writing {file_path}")
        
        collected_metrics = {}
        for relatorio in relatorios:
            for dataset in relatorio.datasets:
                for metrica in dataset.metricas:
                    self._collect_all_metrics(metrica, collected_metrics)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['metric_id', 'function_name'])
            for metrica in collected_metrics.values():
                if metrica.function:
                    writer.writerow([metrica.id, metrica.function.name])
    
    def _write_metric_fact_csv(self, relatorios: List[Relatorio]):
        """Write Metric_Fact.csv."""
        file_path = self.output_dir / CSVFiles.METRIC_FACT
        logger.debug(f"Writing {file_path}")
        
        collected_metrics = {}
        for relatorio in relatorios:
            for dataset in relatorio.datasets:
                for metrica in dataset.metricas:
                    self._collect_all_metrics(metrica, collected_metrics)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['metric_id', 'fact_id'])
            for metrica in collected_metrics.values():
                if metrica.fact:
                    writer.writerow([metrica.id, metrica.fact.id])
    
    def _write_fact_table_csv(self, relatorios: List[Relatorio]):
        """Write Fact_Table.csv."""
        file_path = self.output_dir / CSVFiles.FACT_TABLE
        logger.debug(f"Writing {file_path}")
        
        collected_facts = {}
        for relatorio in relatorios:
            for dataset in relatorio.datasets:
                for metrica in dataset.metricas:
                    self._collect_facts_from_metric(metrica, collected_facts)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['fact_id', 'table_id', 'column_name'])
            for fact in collected_facts.values():
                for logic_table in fact.logic_tables:
                    writer.writerow([
                        fact.id,
                        logic_table.id,
                        logic_table.column_name or ''
                    ])
    
    def _write_metric_metric_csv(self, relatorios: List[Relatorio]):
        """Write Metric_Metric.csv."""
        file_path = self.output_dir / CSVFiles.METRIC_METRIC
        logger.debug(f"Writing {file_path}")
        
        collected_metrics = {}
        for relatorio in relatorios:
            for dataset in relatorio.datasets:
                for metrica in dataset.metricas:
                    self._collect_all_metrics(metrica, collected_metrics)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['parent_metric_id', 'child_metric_id'])
            
            def write_relationships(metrica):
                for child_metrica in metrica.metricas:
                    writer.writerow([metrica.id, child_metrica.id])
                    write_relationships(child_metrica)
            
            for metrica in collected_metrics.values():
                write_relationships(metrica)
    
    def _collect_all_metrics(self, metrica, collected: Dict):
        """Recursively collect all metrics."""
        if metrica.id not in collected:
            collected[metrica.id] = metrica
            for child in metrica.metricas:
                self._collect_all_metrics(child, collected)
    
    def _collect_facts_from_metric(self, metrica, collected: Dict):
        """Recursively collect all facts from metrics."""
        if metrica.fact and metrica.fact.id not in collected:
            collected[metrica.fact.id] = metrica.fact
        for child in metrica.metricas:
            self._collect_facts_from_metric(child, collected)

