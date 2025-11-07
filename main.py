"""Main script for extracting report data model."""

import argparse
import logging
import sys
from pathlib import Path

from extractor import ReportExtractor
from output import export_to_json, export_to_csv, print_summary


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
        '--output-csv-dir',
        type=str,
        help='Output directory for CSV files'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
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
    
    # Initialize extractor
    extractor = ReportExtractor(base_path)
    
    # Extract reports
    if args.report_id:
        logger.info(f"Extracting single report by ID: {args.report_id}")
        relatorio = extractor.extract_report_by_id(args.report_id)
        if not relatorio:
            logger.error(f"Failed to extract report with ID: {args.report_id}")
            sys.exit(1)
        relatorios = [relatorio]
    elif args.report:
        logger.info(f"Extracting report(s) by name: {args.report}")
        relatorios = extractor.extract_report(args.report)
        if not relatorios:
            logger.error(f"Failed to extract report: {args.report}")
            sys.exit(1)
        logger.info(f"Extracted {len(relatorios)} report(s) with name '{args.report}'")
    else:
        logger.info("Extracting all reports")
        relatorios = extractor.extract_all_reports()
        if not relatorios:
            logger.error("No reports extracted")
            sys.exit(1)
    
    # Print summary
    print_summary(relatorios)
    
    # Export to JSON
    if args.output_json:
        output_path = Path(args.output_json)
        logger.info(f"Exporting to JSON: {output_path}")
        export_to_json(relatorios, output_path)
        logger.info(f"JSON export completed: {output_path}")
    
    # Export to CSV
    if args.output_csv_dir:
        output_dir = Path(args.output_csv_dir)
        logger.info(f"Exporting to CSV: {output_dir}")
        export_to_csv(relatorios, output_dir)
        logger.info(f"CSV export completed: {output_dir}")
    
    if not args.output_json and not args.output_csv_dir:
        logger.warning("No output format specified. Use --output-json or --output-csv-dir")
    
    logger.info("Extraction completed successfully")


if __name__ == '__main__':
    main()

