"""Main script for extracting report data model."""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path if package is not installed
try:
    from microstrategy_extractor.extractors.report_extractor import ReportExtractor
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).parent / 'src'))
    from microstrategy_extractor.extractors.report_extractor import ReportExtractor

from microstrategy_extractor.exporters import export_to_json, print_summary
from microstrategy_extractor.parsers.report_parser import extract_report_links


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Extract report data model from MicroStrategy HTML documentation'
    )
    parser.add_argument(
        '--base-path',
        type=str,
        required=True,
        help='Path to directory containing HTML files (e.g., RAW_DATA/04 - Relatórios Gerenciais - BARE (20250519221644))'
    )
    parser.add_argument(
        '--report',
        type=str,
        help='Extract specific report by name (e.g., "04.10.043 - Resultado Comercial - Líderes"). If not specified, extracts all reports.'
    )
    parser.add_argument(
        '--report-id',
        type=str,
        help='Extract specific report by ID (e.g., "D8C7F01F4650B3CBC97AB991C79FB9DF"). Takes precedence over --report if both are specified.'
    )
    parser.add_argument(
        '--output-json',
        type=str,
        help='Output JSON file path'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--filter',
        type=str,
        help='Filter reports by name pattern (e.g., "Boletim" to extract only reports containing "Boletim")'
    )
    parser.add_argument(
        '--aggressive-cache',
        action='store_true',
        help='Pre-load ALL HTML files into memory (uses 4-8GB RAM but 2-3x faster)'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    base_path = Path(args.base_path)
    if not base_path.exists():
        logger.error(f"Base path does not exist: {base_path}")
        sys.exit(1)
    
    documento_path = base_path / "Documento.html"
    if not documento_path.exists():
        logger.error(f"Documento.html not found in: {base_path}")
        sys.exit(1)
    
    logger.info(f"Configuration: aggressive_cache={'enabled' if args.aggressive_cache else 'disabled'}")
    
    # Extract reports
    if args.report_id:
        # Single report by ID - always use sequential
        logger.info(f"Extracting single report by ID: {args.report_id}")
        extractor = ReportExtractor(base_path)
        relatorio = extractor.extract_report_by_id(args.report_id)
        if not relatorio:
            logger.error(f"Failed to extract report with ID: {args.report_id}")
            sys.exit(1)
        relatorios = [relatorio]
    elif args.report:
        # Single/few reports by name - always use sequential
        logger.info(f"Extracting report(s) by name: {args.report}")
        extractor = ReportExtractor(base_path)
        relatorios = extractor.extract_report(args.report)
        if not relatorios:
            logger.error(f"Failed to extract report: {args.report}")
            sys.exit(1)
        logger.info(f"Extracted {len(relatorios)} report(s) with name '{args.report}'")
    else:
        # Extract all reports (with optional filter) - always sequential
        if args.filter:
            logger.info(f"Filtering reports by pattern: '{args.filter}'")
            # Get all report names
            temp_extractor = ReportExtractor(base_path)
            all_reports = extract_report_links(temp_extractor.documento_path)
            filtered_reports = [r['name'] for r in all_reports if args.filter.lower() in r['name'].lower()]
            logger.info(f"Found {len(filtered_reports)} reports matching filter (out of {len(all_reports)} total)")
            
            if not filtered_reports:
                logger.error(f"No reports match filter: {args.filter}")
                sys.exit(1)
            
            # Extract filtered reports
            extractor = ReportExtractor(base_path)
            relatorios = extractor.extract_all_reports(filter_names=filtered_reports, aggressive_cache=args.aggressive_cache)
        else:
            logger.info("Extracting all reports (sequential mode with live progress)")
            extractor = ReportExtractor(base_path)
            relatorios = extractor.extract_all_reports(aggressive_cache=args.aggressive_cache)
        
        if not relatorios:
            logger.error("No reports extracted")
            sys.exit(1)
    
    # Print summary
    print_summary(relatorios)
    
    # Export to JSON
    if args.output_json:
        output_path = Path(args.output_json)
        logger.info(f"Exporting to JSON: {output_path}")
        export_to_json(relatorios, output_path, base_path=str(base_path))
        logger.info(f"JSON export completed: {output_path}")
    else:
        logger.warning("No output file specified. Use --output-json")
    
    logger.info("Extraction completed successfully")


if __name__ == '__main__':
    main()

