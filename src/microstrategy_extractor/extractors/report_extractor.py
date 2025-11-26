"""Main report extractor coordinating all extraction strategies."""

from pathlib import Path
from typing import List, Optional, Dict

from microstrategy_extractor.extractors.base_extractor import BaseExtractor
from microstrategy_extractor.extractors.dataset_extractor import DatasetExtractor
from microstrategy_extractor.extractors.attribute_extractor import AttributeExtractor
from microstrategy_extractor.extractors.metric_extractor import MetricExtractor
from microstrategy_extractor.core.models import Relatorio, Owner, AccessControlEntry
from microstrategy_extractor.parsers.report_parser import find_report_by_name, find_report_by_id, extract_report_links, extract_datasets_from_report, extract_owner, extract_access_control
from microstrategy_extractor.parsers.attribute_parser import find_attribute_link
from microstrategy_extractor.parsers.metric_parser import find_metric_link
from microstrategy_extractor.parsers.base_parser import preload_common_files, preload_all_html_files, get_cache_stats
from microstrategy_extractor.utils.logger import get_logger
from microstrategy_extractor.cache import MemoryCache
from microstrategy_extractor.config.settings import Config

logger = get_logger(__name__)


class ReportExtractor(BaseExtractor):
    """
    Main extractor coordinating all extraction strategies.
    
    REFACTORED: Now uses specialized extractors for each entity type.
    """
    
    def __init__(self, base_path: Path, config: Optional[Config] = None):
        """
        Initialize report extractor with specialized extractors.
        
        Args:
            base_path: Base path to HTML files
            config: Optional configuration object
        """
        super().__init__(base_path, cache=None, config=config)
        
        # Create specialized extractors (share same cache)
        self.dataset_extractor = DatasetExtractor(base_path, self.cache, config)
        self.attribute_extractor = AttributeExtractor(base_path, self.cache, config)
        self.metric_extractor = MetricExtractor(base_path, self.cache, config)
        
        # Document paths for compatibility
        self.documento_path = self.get_html_file_path('documento')
        self.relatorio_path = self.get_html_file_path('relatorio')
        self.cubo_inteligente_path = self.get_html_file_path('cubo_inteligente')
        self.atalho_path = self.get_html_file_path('atalho')
        self.metrica_index_path = self.get_html_file_path('metrica')
        self.fato_index_path = self.get_html_file_path('fato')
        self.funcao_index_path = self.get_html_file_path('funcao')
        self.atributo_index_path = self.get_html_file_path('atributo')
        self.tabela_logica_index_path = self.get_html_file_path('tabela_logica')
        self.pasta_index_path = self.get_html_file_path('pasta')
        
        # Legacy cache dicts (for backward compatibility)
        self._parsed_files = {}
        self._metric_cache = {}
        self._attribute_cache = {}
    
    def extract_report(self, report_name: str) -> List[Relatorio]:
        """
        Extract complete data model for all reports with the given name.
        
        Args:
            report_name: Name of report to extract
            
        Returns:
            List of Relatorio objects
        """
        logger.info(f"Extracting report(s): {report_name}")
        
        # Find reports
        reports_info = find_report_by_name(self.documento_path, report_name)
        if not reports_info:
            logger.warning(f"Report '{report_name}' not found in Documento.html")
            return []
        
        logger.info(f"Found {len(reports_info)} report(s) with name '{report_name}'")
        
        relatorios = []
        for report_info in reports_info:
            relatorio = self._extract_single_report(report_info)
            if relatorio:
                relatorios.append(relatorio)
        
        return relatorios
    
    def extract_report_by_id(self, report_id: str) -> Optional[Relatorio]:
        """
        Extract complete data model for a specific report by ID.
        
        Args:
            report_id: Report ID
            
        Returns:
            Relatorio object or None
        """
        logger.info(f"Extracting report by ID: {report_id}")
        
        report_info = find_report_by_id(self.documento_path, report_id)
        if not report_info:
            logger.warning(f"Report with ID '{report_id}' not found")
            return None
        
        return self._extract_single_report(report_info)
    
    def extract_all_reports(self, aggressive_cache: bool = False, filter_names: List[str] = None) -> List[Relatorio]:
        """
        Extract data model for all reports in Documento.html with live progress display.
        
        Args:
            aggressive_cache: If True, pre-load ALL HTML files into memory before extraction
            filter_names: Optional list of report names to extract (if None, extracts all)
        
        Returns:
            List of all Relatorio objects
        """
        # Pre-cache files if requested
        if aggressive_cache:
            preload_all_html_files(self.base_path)
        else:
            # Always pre-load common index files for better performance
            preload_common_files(self.base_path)
        
        reports_info = extract_report_links(self.documento_path)
        
        # Filter reports if filter_names provided
        if filter_names:
            reports_info = [r for r in reports_info if r['name'] in filter_names]
            logger.info(f"Filtered to {len(reports_info)} reports matching filter")
        
        relatorios = []
        
        logger.info(f"Found {len(reports_info)} reports to process")
        
        for i, report_info in enumerate(reports_info, 1):
            try:
                logger.info(f"Processing report {i}/{len(reports_info)}: {report_info['name']}")
                relatorio = self._extract_single_report(report_info)
                if relatorio:
                    relatorios.append(relatorio)
            except Exception as e:
                logger.error(f"Error extracting report '{report_info['name']}': {e}")
                continue
        
        # Log cache stats
        cache_stats = get_cache_stats()
        logger.info(f"Cache statistics: {cache_stats['hits']} hits, {cache_stats['misses']} misses, "
                   f"{cache_stats['hit_rate']}% hit rate")
        
        return relatorios
    
    def _extract_single_report(self, report_info: Dict) -> Optional[Relatorio]:
        """Extract a single report."""
        report_id = report_info.get('anchor', '')
        if not report_id:
            logger.warning(f"Report anchor not found for: {report_info['name']}")
            return None
        
        report_file = self.base_path / report_info['file']
        if not report_file.exists():
            logger.error(f"Report file not found: {report_file}")
            return None
        
        file_path_with_anchor = f"{report_info['file']}#{report_id}"
        
        logger.info(f"Extracting report ID: {report_id}")
        
        relatorio = Relatorio(
            name=report_info['name'],
            id=report_id,
            file_path=file_path_with_anchor
        )
        
        # Extract report details
        soup = self.get_parsed_file(report_info['file'])
        
        # Extract owner (pass anchor to restrict search to this report)
        owner_data = extract_owner(soup, self.pasta_index_path, report_id)
        if owner_data:
            relatorio.owner = Owner(
                name=owner_data['name'],
                id=owner_data['id'],
                file_path=owner_data['file_path'],
                fullname=owner_data.get('fullname'),
                access=owner_data.get('access'),
                migration_stage=owner_data.get('migration_stage'),
                decision=owner_data.get('decision')
            )
        
        # Extract access control (pass anchor to restrict search to this report)
        access_control_data = extract_access_control(soup, self.pasta_index_path, report_id)
        for ac_data in access_control_data:
            relatorio.access_control.append(
                AccessControlEntry(
                    name=ac_data['name'],
                    access=ac_data['access'],
                    fullname=ac_data.get('fullname'),
                    id=ac_data.get('id'),
                    file_path=ac_data.get('file_path')
                )
            )
        
        # Extract datasets
        anchor = report_info.get('anchor', '').split('#')[-1] if '#' in report_info.get('anchor', '') else report_info.get('anchor', '')
        datasets_info = extract_datasets_from_report(soup, report_info['name'], anchor)
        
        logger.info(f"Found {len(datasets_info)} datasets")
        
        # Extract each dataset
        for ds_info in datasets_info:
            dataset_result = self.dataset_extractor.extract(ds_info, relatorio.id)
            
            if isinstance(dataset_result, tuple):
                # New format: returns (dataset, atributos_info, metricas_info)
                dataset, atributos_info, metricas_info = dataset_result
                
                # Extract attributes
                for attr_info in atributos_info:
                    attr_link = find_attribute_link(
                        self.atributo_index_path,
                        attr_info['name_on_dataset'],
                        attr_info.get('id')
                    )
                    if attr_link:
                        atributo = self.attribute_extractor.extract(
                            attr_link['name'],
                            attr_info['name_on_dataset'],
                            f"{attr_link['file']}#{attr_link['anchor']}" if attr_link.get('anchor') else attr_link['file'],
                            dataset.id
                        )
                        if atributo:
                            dataset.atributos.append(atributo)
                
                # Extract metrics
                for metrica_info in metricas_info:
                    metrica_link = find_metric_link(
                        self.metrica_index_path,
                        metrica_info['name_on_dataset'],
                        metrica_info.get('id')
                    )
                    if metrica_link:
                        metrica_file_path = f"{metrica_link['file']}#{metrica_link['anchor']}" if metrica_link.get('anchor') else metrica_link['file']
                        metrica_anchor = metrica_link.get('anchor', metrica_info.get('id'))
                        
                        metrica = self.metric_extractor.extract(
                            metrica_link['name'],
                            metrica_file_path,
                            dataset.id,
                            metrica_anchor
                        )
                        if metrica:
                            dataset.metricas.append(metrica)
                    else:
                        # Handle embedded/derived metrics not in Metric.html index
                        from microstrategy_extractor.core.models import Metrica
                        
                        metric_name = metrica_info['name_on_dataset']
                        metric_id = metrica_info.get('id', '')
                        
                        logger.info(f"Embedded metric detected (not in index): {metric_name} (ID: {metric_id})")
                        
                        # Create embedded metric with available information
                        embedded_metrica = Metrica(
                            name=metric_name,
                            id=metric_id,
                            file_path=metrica_info.get('href', ''),
                            dataset_id=dataset.id,
                            tipo='embedded',
                            applicationObject='DerivedMetric',
                            formula=None,
                            function=None,
                            fact=None
                        )
                        dataset.metricas.append(embedded_metrica)
                
                relatorio.datasets.append(dataset)
            
            elif dataset_result:
                # Old format: just dataset
                relatorio.datasets.append(dataset_result)
        
        return relatorio
    
    def _get_parsed_file(self, file_path: str):
        """Legacy method for backward compatibility."""
        return self.get_parsed_file(file_path)

