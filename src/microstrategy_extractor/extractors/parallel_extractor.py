"""Parallel extraction support for processing multiple reports concurrently.

Uses ThreadPoolExecutor instead of ProcessPoolExecutor because:
- Report extraction is I/O-bound (reading HTML files)
- Threads have much lower overhead than processes
- GIL is not a bottleneck for I/O operations
- 2-3x faster than multiprocessing for this workload
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Dict
import logging

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

from microstrategy_extractor.core.models import Relatorio
from microstrategy_extractor.extractors.report_extractor import ReportExtractor
from microstrategy_extractor.parsers.report_parser import extract_report_links
from microstrategy_extractor.parsers.base_parser import preload_common_files, preload_all_html_files, get_cache_stats
from microstrategy_extractor.utils.logger import get_logger

logger = get_logger(__name__)


class ParallelReportExtractor:
    """Wrapper for ReportExtractor with parallel (threaded) processing support."""
    
    def __init__(self, base_path: Path, max_workers: int = 4):
        """
        Initialize parallel extractor.
        
        Args:
            base_path: Base path to HTML files
            max_workers: Maximum number of worker threads
        """
        self.base_path = Path(base_path)
        self.max_workers = max_workers
        # Don't create shared extractor - each thread needs its own to avoid contention!
    
    def extract_all_reports(self, parallel: bool = True, aggressive_cache: bool = False) -> List[Relatorio]:
        """
        Extract all reports with optional parallelization.
        
        Pre-loads index files (or ALL files with aggressive_cache) into global cache.
        
        Args:
            parallel: Whether to use parallel processing
            aggressive_cache: If True, pre-load ALL HTML files (4-8GB RAM, 2-3x faster)
            
        Returns:
            List of Relatorio objects
        """
        # PRE-LOAD files into global cache BEFORE starting extraction
        if aggressive_cache:
            logger.info("=== AGGRESSIVE CACHING: Pre-loading ALL HTML files ===")
            preload_all_html_files(self.base_path)
        else:
            logger.info("=== Memory Optimization: Pre-loading common files ===")
            preload_common_files(self.base_path)
        
        # Get list of all reports
        temp_extractor = ReportExtractor(self.base_path)
        reports_info = extract_report_links(temp_extractor.documento_path)
        
        logger.info(f"Found {len(reports_info)} reports to process")
        
        if not parallel or len(reports_info) < 2:
            logger.info("Using sequential extraction with global cache")
            return self._extract_sequential(reports_info)
        
        logger.info(f"Using parallel extraction with {self.max_workers} threads (global cache shared)")
        return self._extract_parallel(reports_info)
    
    def _extract_sequential(self, reports_info: List[Dict]) -> List[Relatorio]:
        """
        Extract reports sequentially.
        
        Args:
            reports_info: List of report information dicts
            
        Returns:
            List of Relatorio objects
        """
        # Create one extractor for sequential mode (can reuse caches)
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
        Extract reports in parallel using ThreadPoolExecutor.
        
        Threads are preferred over processes for I/O-bound operations because:
        - Lower overhead (no process spawning or serialization)
        - Shared memory (single ReportExtractor instance)
        - GIL is not a bottleneck for I/O operations
        
        Args:
            reports_info: List of report information dicts
            
        Returns:
            List of Relatorio objects
        """
        relatorios = []
        total = len(reports_info)
        
        # Create tasks for each report using threads
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks - using lambda to capture self.extractor
            future_to_report = {
                executor.submit(self._extract_single_report, report_info): report_info
                for report_info in reports_info
            }
            
            # Collect results as they complete with progress bar
            if TQDM_AVAILABLE:
                progress_bar = tqdm(
                    total=total, 
                    desc="Extracting reports", 
                    unit="report",
                    bar_format="{desc}: {percentage:.2f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]"
                )
            
            completed = 0
            
            for future in as_completed(future_to_report):
                completed += 1
                report_info = future_to_report[future]
                
                try:
                    result = future.result()
                    if result:
                        relatorios.extend(result)
                        if TQDM_AVAILABLE:
                            progress_bar.set_postfix_str(f"Latest: {report_info['name'][:40]}...")
                            progress_bar.update(1)
                        else:
                            logger.info(f"[{completed}/{total}] Completed: {report_info['name']}")
                    else:
                        if TQDM_AVAILABLE:
                            progress_bar.update(1)
                        else:
                            logger.warning(f"[{completed}/{total}] No data extracted: {report_info['name']}")
                except Exception as e:
                    if TQDM_AVAILABLE:
                        progress_bar.update(1)
                    logger.error(f"[{completed}/{total}] Failed: {report_info['name']} - {e}")
            
            if TQDM_AVAILABLE:
                progress_bar.close()
        
        # Report cache statistics
        file_stats = get_cache_stats()
        
        logger.info(f"Parallel extraction complete: {len(relatorios)} reports extracted")
        logger.info(f"=== File Cache Stats ===")
        logger.info(f"  Files: {file_stats['size']} cached, {file_stats['hits']} hits, "
                   f"{file_stats['misses']} misses, {file_stats['hit_rate']}% hit rate")
        return relatorios
    
    def _extract_single_report(self, report_info: Dict) -> Optional[List[Relatorio]]:
        """
        Extract a single report (thread-safe method).
        
        Each thread creates its own ReportExtractor instance to avoid
        dictionary contention on shared caches (_parsed_files, _metric_cache, etc.)
        
        Args:
            report_info: Report information dict
            
        Returns:
            List of Relatorio objects or None if extraction failed
        """
        try:
            # CRITICAL: Create a NEW extractor instance for THIS thread
            # This eliminates contention on shared dictionaries (_parsed_files, caches)
            extractor = ReportExtractor(self.base_path)
            relatorios = extractor.extract_report(report_info['name'])
            return relatorios if relatorios else None
        except Exception as e:
            logger.error(f"Error extracting '{report_info['name']}': {e}")
            return None


def extract_reports_parallel(base_path: Path, max_workers: int = 4) -> List[Relatorio]:
    """
    Convenience function for parallel report extraction.
    
    Args:
        base_path: Base path to HTML files
        max_workers: Maximum number of worker threads
        
    Returns:
        List of all extracted Relatorio objects
    """
    parallel_extractor = ParallelReportExtractor(base_path, max_workers)
    return parallel_extractor.extract_all_reports(parallel=True)

