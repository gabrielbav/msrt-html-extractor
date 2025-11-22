"""Dataset extraction logic."""

import uuid
from pathlib import Path
from typing import Optional, Dict, List
from bs4 import BeautifulSoup

from microstrategy_extractor.extractors.base_extractor import BaseExtractor
from microstrategy_extractor.core.models import DataSet
from microstrategy_extractor.parsers.report_parser import resolve_dataset_link, is_report_dataset, extract_graphic_type, extract_template_objects_report
from microstrategy_extractor.parsers.metric_parser import extract_template_objects
from microstrategy_extractor.utils.logger import get_logger
from microstrategy_extractor.core.constants import ApplicationObjects

logger = get_logger(__name__)


class DatasetExtractor(BaseExtractor):
    """Extractor for dataset details."""
    
    def extract(self, ds_info: Dict[str, str], relatorio_id: str) -> Optional[DataSet]:
        """
        Extract dataset details including attributes and metrics.
        
        Args:
            ds_info: Dataset info dict with 'name', 'id', 'href'
            relatorio_id: ID of parent report
            
        Returns:
            DataSet object or None
        """
        dataset_name = ds_info['name']
        dataset_id = ds_info.get('id', '')
        
        logger.info(f"Extracting dataset: {dataset_name}")
        
        # Resolve dataset file path
        dataset_result = self._resolve_dataset(dataset_id, dataset_name)
        
        # Handle case where dataset is not found
        if not dataset_result:
            return self._create_empty_dataset(dataset_name, dataset_id, relatorio_id)
        
        dataset_file, dataset_source = dataset_result
        
        # Extract ID from file path if not available
        if not dataset_id and '#' in dataset_file:
            dataset_id = dataset_file.split('#')[1]
            logger.info(f"Extracted dataset ID from file path: {dataset_id}")
        
        # Generate GUID if still no ID
        if not dataset_id:
            dataset_id = str(uuid.uuid4()).replace('-', '').upper()
            logger.info(f"Generated GUID for dataset without ID: {dataset_id}")
        
        # Handle Shortcut type
        if dataset_source == ApplicationObjects.SHORTCUT:
            return DataSet(
                name=dataset_name,
                id=dataset_id,
                file_path=dataset_file,
                relatorio_id=relatorio_id,
                applicationObject=ApplicationObjects.SHORTCUT,
                graphic=None
            )
        
        # Check if file exists
        file_name_only = dataset_file.split('#')[0]
        if not (self.base_path / file_name_only).exists():
            logger.warning(f"Dataset file not found: {file_name_only}")
            return None
        
        # Detect dataset type and extract accordingly
        soup = self.get_parsed_file(dataset_file)
        is_report = is_report_dataset(soup, dataset_id)
        
        if is_report:
            logger.info(f"Dataset is a Report type")
            application_object = ApplicationObjects.REPORT
            graphic_type = extract_graphic_type(soup, dataset_id)
            atributos_info, metricas_info = extract_template_objects_report(soup, dataset_id)
        else:
            application_object = ApplicationObjects.CUBO_INTELIGENTE if dataset_source == ApplicationObjects.CUBO_INTELIGENTE else None
            graphic_type = None
            atributos_info, metricas_info = extract_template_objects(soup, dataset_name, dataset_id)
        
        dataset = DataSet(
            name=dataset_name,
            id=dataset_id,
            file_path=dataset_file,
            relatorio_id=relatorio_id,
            applicationObject=application_object,
            graphic=graphic_type
        )
        
        logger.info(f"Found {len(atributos_info)} attributes and {len(metricas_info)} metrics")
        
        return dataset, atributos_info, metricas_info
    
    def _resolve_dataset(self, dataset_id: str, dataset_name: str) -> Optional[tuple]:
        """Resolve dataset to file path."""
        cubo_inteligente_path = self.get_html_file_path('cubo_inteligente')
        relatorio_path = self.get_html_file_path('relatorio')
        atalho_path = self.get_html_file_path('atalho')
        
        if dataset_id:
            return resolve_dataset_link(
                self.base_path,
                dataset_id,
                cubo_inteligente_path,
                relatorio_path,
                atalho_path,
                dataset_name=dataset_name
            )
        else:
            logger.warning(f"Dataset has no ID, trying to search by name: {dataset_name}")
            return resolve_dataset_link(
                self.base_path,
                "",
                cubo_inteligente_path,
                relatorio_path,
                atalho_path,
                dataset_name=dataset_name
            )
    
    def _create_empty_dataset(self, dataset_name: str, dataset_id: str, 
                             relatorio_id: str) -> DataSet:
        """Create empty dataset when not found in index files."""
        logger.warning(f"Dataset not found in index files: {dataset_name} (ID: {dataset_id})")
        
        # Generate GUID if no ID
        if not dataset_id:
            dataset_id = str(uuid.uuid4()).replace('-', '').upper()
            logger.info(f"Generated GUID for dataset without ID: {dataset_id}")
        
        return DataSet(
            name=dataset_name,
            id=dataset_id,
            file_path="",
            relatorio_id=relatorio_id,
            applicationObject="",
            graphic=None
        )

