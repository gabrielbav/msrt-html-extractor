"""Parallel extraction support for processing multiple reports concurrently."""

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional
import logging

from models import Relatorio
from extractor import ReportExtractor
from utils.logger import get_logger

logger = get_logger(__name__)


class ParallelReportExtractor:
    """Wrapper for ReportExtractor with parallel processing support."""
    
    def __init__(self, base_path: Path, max_workers: int = 4):
        """
        Initialize parallel extractor.
        
        Args:
            base_path: Base path to HTML files
            max_workers: Maximum number of worker processes
        """
        self.base_path = Path(base_path)
        self.max_workers = max_workers
    
    def extract_all_reports(self, parallel: bool = True) -> List[Relatorio]:
        """
        Extract all reports with optional parallelization.
        
        Args:
            parallel: Whether to use parallel processing
            
        Returns:
            List of Relatorio objects
        """
        # Create extractor to get report list
        extractor = ReportExtractor(self.base_path)
        
        # Get list of all reports
        from html_parser import extract_report_links
        reports_info = extract_report_links(extractor.documento_path)
        
        logger.info(f"Found {len(reports_info)} reports to process")
        
        if not parallel or len(reports_info) < 2:
            logger.info("Using sequential extraction")
            return self._extract_sequential(reports_info)
        
        logger.info(f"Using parallel extraction with {self.max_workers} workers")
        return self._extract_parallel(reports_info)
    
    def _extract_sequential(self, reports_info: List[Dict]) -> List[Relatorio]:
        """
        Extract reports sequentially.
        
        Args:
            reports_info: List of report information dicts
            
        Returns:
            List of Relatorio objects
        """
        extractor = ReportExtractor(self.base_path)
        relatorios = []
        
        for i, report_info in enumerate(reports_info, 1):
            logger.info(f"Processing report {i}/{len(reports_info)}: {report_info['name']}")
            try:
                extracted_reports = extractor.extract_report(report_info['name'])
                if extracted_reports:
                    relatorios.extend(extracted_reports)
            except Exception as e:
                logger.error(f"Error extracting report '{report_info['name']}': {e}")
                continue
        
        return relatorios
    
    def _extract_parallel(self, reports_info: List[Dict]) -> List[Relatorio]:
        """
        Extract reports in parallel using ProcessPoolExecutor.
        
        Args:
            reports_info: List of report information dicts
            
        Returns:
            List of Relatorio objects
        """
        relatorios = []
        
        # Create tasks for each report
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_report = {
                executor.submit(_extract_single_report_worker, self.base_path, report_info): report_info
                for report_info in reports_info
            }
            
            # Collect results as they complete
            completed = 0
            total = len(reports_info)
            
            for future in as_completed(future_to_report):
                completed += 1
                report_info = future_to_report[future]
                
                try:
                    result = future.result()
                    if result:
                        relatorios.extend(result)
                        logger.info(f"[{completed}/{total}] Completed: {report_info['name']}")
                    else:
                        logger.warning(f"[{completed}/{total}] No data extracted: {report_info['name']}")
                except Exception as e:
                    logger.error(f"[{completed}/{total}] Failed: {report_info['name']} - {e}")
        
        logger.info(f"Parallel extraction complete: {len(relatorios)} reports extracted")
        return relatorios


def _extract_single_report_worker(base_path: Path, report_info: Dict) -> Optional[List[Relatorio]]:
    """
    Worker function for parallel extraction (must be top-level for pickling).
    
    Args:
        base_path: Base path to HTML files
        report_info: Report information dict
        
    Returns:
        List of Relatorio objects or None if extraction failed
    """
    try:
        # Each worker process needs its own extractor instance
        extractor = ReportExtractor(base_path)
        
        # Extract the report
        relatorios = extractor.extract_report(report_info['name'])
        
        return relatorios if relatorios else None
        
    except Exception as e:
        # Log error (will be caught by parent process)
        logging.error(f"Worker error extracting '{report_info['name']}': {e}")
        return None


def extract_reports_parallel(base_path: Path, max_workers: int = 4) -> List[Relatorio]:
    """
    Convenience function for parallel report extraction.
    
    Args:
        base_path: Base path to HTML files
        max_workers: Maximum number of worker processes
        
    Returns:
        List of all extracted Relatorio objects
    """
    parallel_extractor = ParallelReportExtractor(base_path, max_workers)
    return parallel_extractor.extract_all_reports(parallel=True)

