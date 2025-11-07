#!/usr/bin/env python3
"""Convert JSON output to CSV files without re-extracting from HTML."""

import json
import sys
import logging
from pathlib import Path
from typing import List

from models import Relatorio, DataSet, Atributo, Metrica, Function, Fact, Formulario, LogicTable
from output import export_to_csv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def json_to_relatorios(json_path: Path) -> List[Relatorio]:
    """Load JSON file and convert back to Relatorio objects."""
    logger.info(f"Loading JSON from: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    relatorios = []
    
    for rel_data in data['relatorios']:
        relatorio = Relatorio(
            name=rel_data['name'],
            id=rel_data['id'],
            file_path=rel_data['file_path']
        )
        
        # Rebuild datasets
        for ds_data in rel_data['datasets']:
            dataset = DataSet(
                name=ds_data['name'],
                id=ds_data['id'],
                file_path=ds_data['file_path'],
                relatorio_id=relatorio.id,
                applicationObject=ds_data.get('applicationObject'),
                graphic=ds_data.get('graphic')
            )
            
            # Rebuild attributes
            for attr_data in ds_data['atributos']:
                atributo = Atributo(
                    name=attr_data['name'],
                    name_on_dataset=attr_data['name_on_dataset'],
                    id=attr_data['id'],
                    file_path=attr_data['file_path'],
                    dataset_id=dataset.id,
                    applicationSchema=attr_data.get('applicationSchema')
                )
                
                # Rebuild formularios
                for form_data in attr_data.get('formularios', []):
                    formulario = Formulario(name=form_data['name'])
                    
                    # Rebuild logic tables
                    for lt_data in form_data.get('logic_tables', []):
                        logic_table = LogicTable(
                            name=lt_data['name'],
                            id=lt_data['id'],
                            file_path=lt_data.get('file_path'),
                            column_name=lt_data.get('column_name')
                        )
                        formulario.logic_tables.append(logic_table)
                    
                    atributo.formularios.append(formulario)
                
                dataset.atributos.append(atributo)
            
            # Rebuild metrics
            for metric_data in ds_data['metricas']:
                metrica = _rebuild_metric(metric_data, dataset.id)
                dataset.metricas.append(metrica)
            
            relatorio.datasets.append(dataset)
        
        relatorios.append(relatorio)
    
    logger.info(f"Loaded {len(relatorios)} report(s)")
    return relatorios


def _rebuild_metric(metric_data: dict, dataset_id: str) -> Metrica:
    """Recursively rebuild a metric from JSON data."""
    metrica = Metrica(
        name=metric_data['name'],
        id=metric_data['id'],
        file_path=metric_data['file_path'],
        dataset_id=dataset_id,
        tipo=metric_data['tipo'],
        applicationObject=metric_data.get('applicationObject'),
        formula=metric_data.get('formula')
    )
    
    # Rebuild function if present
    if metric_data.get('function'):
        func_data = metric_data['function']
        metrica.function = Function(
            name=func_data['name'],
            file_path=func_data['file_path']
        )
    
    # Rebuild fact if present
    if metric_data.get('fact'):
        fact_data = metric_data['fact']
        metrica.fact = Fact(
            name=fact_data['name'],
            id=fact_data['id'],
            file_path=fact_data['file_path']
        )
        
        # Rebuild logic tables for fact
        for lt_data in fact_data.get('logic_tables', []):
            logic_table = LogicTable(
                name=lt_data['name'],
                id=lt_data['id'],
                file_path=lt_data.get('file_path'),
                column_name=lt_data.get('column_name')
            )
            metrica.fact.logic_tables.append(logic_table)
    
    # Rebuild child metrics (for composite metrics)
    for child_data in metric_data.get('metricas', []):
        child_metric = _rebuild_metric(child_data, dataset_id)
        metrica.metricas.append(child_metric)
    
    return metrica


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert JSON output to CSV files')
    parser.add_argument(
        '--input-json',
        type=str,
        required=True,
        help='Input JSON file path'
    )
    parser.add_argument(
        '--output-csv-dir',
        type=str,
        required=True,
        help='Output directory for CSV files'
    )
    
    args = parser.parse_args()
    
    json_path = Path(args.input_json)
    if not json_path.exists():
        logger.error(f"JSON file not found: {json_path}")
        sys.exit(1)
    
    # Load relatorios from JSON
    relatorios = json_to_relatorios(json_path)
    
    # Export to CSV
    output_dir = Path(args.output_csv_dir)
    logger.info(f"Exporting to CSV: {output_dir}")
    export_to_csv(relatorios, output_dir)
    logger.info(f"CSV export completed: {output_dir}")


if __name__ == '__main__':
    main()

