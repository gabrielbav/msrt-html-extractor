#!/usr/bin/env python3
"""
Script to import normalized CSV files into a PostgreSQL database.
Can be adapted for other databases (MySQL, SQL Server, etc.)
"""

import csv
import os
import psycopg2
from typing import List, Dict
import argparse
from pathlib import Path


class DatabaseImporter:
    def __init__(self, connection_string: str, csv_dir: str):
        """
        Initialize the database importer.
        
        Args:
            connection_string: PostgreSQL connection string
            csv_dir: Directory containing CSV files
        """
        self.connection_string = connection_string
        self.csv_dir = csv_dir
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection."""
        print(f"Connecting to database...")
        self.conn = psycopg2.connect(self.connection_string)
        self.cursor = self.conn.cursor()
        print("✓ Connected successfully")
        
    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✓ Disconnected from database")
    
    def execute_sql_file(self, sql_file: str):
        """Execute a SQL file."""
        print(f"\nExecuting SQL file: {sql_file}")
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql = f.read()
            self.cursor.execute(sql)
            self.conn.commit()
        print("✓ SQL file executed successfully")
    
    def import_csv(self, table_name: str, csv_file: str):
        """
        Import a CSV file into a database table.
        
        Args:
            table_name: Name of the target table
            csv_file: Path to the CSV file
        """
        if not os.path.exists(csv_file):
            print(f"  ⚠ Skipping {table_name} - CSV file not found")
            return
        
        print(f"  Importing {table_name}...")
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            if not rows:
                print(f"    ⚠ No data to import")
                return
            
            # Get column names from CSV header
            columns = list(rows[0].keys())
            
            # Build INSERT statement
            placeholders = ', '.join(['%s'] * len(columns))
            columns_str = ', '.join([f'"{col}"' for col in columns])
            insert_sql = f'INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})'
            
            # Insert rows
            inserted_count = 0
            for row in rows:
                values = [row[col] if row[col] != '' else None for col in columns]
                try:
                    self.cursor.execute(insert_sql, values)
                    inserted_count += 1
                except psycopg2.Error as e:
                    print(f"    ✗ Error inserting row: {e}")
                    self.conn.rollback()
                    continue
            
            self.conn.commit()
            print(f"    ✓ Imported {inserted_count} rows")
    
    def import_all_csvs(self):
        """Import all CSV files in the correct order."""
        print("\n" + "="*60)
        print("IMPORTING CSV FILES")
        print("="*60)
        
        # Order matters due to foreign key constraints
        import_order = [
            # Main entities first
            ('reports', 'reports.csv'),
            ('datasets', 'datasets.csv'),
            ('attributes', 'attributes.csv'),
            ('attributes_forms', 'attributes_forms.csv'),
            ('functions', 'functions.csv'),
            ('metrics', 'metrics.csv'),
            ('facts', 'facts.csv'),
            ('tables', 'tables.csv'),
            
            # Relationship tables
            ('report_datasets', 'report_datasets.csv'),
            ('dataset_attributes', 'dataset_attributes.csv'),
            ('dataset_metrics', 'dataset_metrics.csv'),
            ('attribute_forms', 'attribute_forms.csv'),
            ('form_tables', 'form_tables.csv'),
            ('metric_metrics', 'metric_metrics.csv'),
            ('metric_facts', 'metric_facts.csv'),
            ('metric_functions', 'metric_functions.csv'),
            ('fact_tables', 'fact_tables.csv'),
        ]
        
        for table_name, csv_filename in import_order:
            csv_path = os.path.join(self.csv_dir, csv_filename)
            self.import_csv(table_name, csv_path)
    
    def verify_import(self):
        """Verify the import by counting rows in each table."""
        print("\n" + "="*60)
        print("VERIFICATION")
        print("="*60)
        
        tables = [
            'reports', 'datasets', 'attributes', 'attributes_forms',
            'functions', 'metrics', 'facts', 'tables',
            'report_datasets', 'dataset_attributes', 'dataset_metrics',
            'attribute_forms', 'form_tables', 'metric_metrics',
            'metric_facts', 'metric_functions', 'fact_tables'
        ]
        
        print("\nTable Row Counts:")
        print("-" * 60)
        
        for table in tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = self.cursor.fetchone()[0]
            print(f"  {table:<30} {count:>10} rows")
    
    def run(self, create_schema: bool = True):
        """
        Run the complete import process.
        
        Args:
            create_schema: Whether to create the schema before importing
        """
        try:
            self.connect()
            
            if create_schema:
                # Try to find create_schema.sql in ../sql/ or in csv_dir
                sql_file = os.path.join(os.path.dirname(self.csv_dir), 'sql', 'create_schema.sql')
                if not os.path.exists(sql_file):
                    sql_file = os.path.join(self.csv_dir, 'create_schema.sql')
                
                if os.path.exists(sql_file):
                    self.execute_sql_file(sql_file)
                else:
                    print("⚠ Warning: create_schema.sql not found, skipping schema creation")
            
            self.import_all_csvs()
            self.verify_import()
            
            print("\n" + "="*60)
            print("✓ IMPORT COMPLETED SUCCESSFULLY")
            print("="*60)
            
        except Exception as e:
            print(f"\n✗ Error during import: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.disconnect()


def parse_connection_string(args) -> str:
    """
    Build PostgreSQL connection string from arguments.
    
    Args:
        args: Command line arguments
        
    Returns:
        Connection string
    """
    if args.connection_string:
        return args.connection_string
    
    # Build from individual parameters
    parts = []
    if args.host:
        parts.append(f"host={args.host}")
    if args.port:
        parts.append(f"port={args.port}")
    if args.database:
        parts.append(f"dbname={args.database}")
    if args.user:
        parts.append(f"user={args.user}")
    if args.password:
        parts.append(f"password={args.password}")
    
    return ' '.join(parts)


def main():
    parser = argparse.ArgumentParser(
        description='Import normalized CSV files into PostgreSQL database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using connection string
  python import_to_database.py --connection-string "host=localhost dbname=mydb user=myuser password=mypass"
  
  # Using individual parameters
  python import_to_database.py --host localhost --database mydb --user myuser --password mypass
  
  # Skip schema creation (if schema already exists)
  python import_to_database.py --connection-string "..." --no-create-schema
        """
    )
    
    # Connection parameters
    conn_group = parser.add_mutually_exclusive_group(required=True)
    conn_group.add_argument(
        '--connection-string',
        help='PostgreSQL connection string'
    )
    
    conn_group.add_argument(
        '--host',
        help='Database host'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5432,
        help='Database port (default: 5432)'
    )
    
    parser.add_argument(
        '--database',
        help='Database name'
    )
    
    parser.add_argument(
        '--user',
        help='Database user'
    )
    
    parser.add_argument(
        '--password',
        help='Database password'
    )
    
    # Other options
    parser.add_argument(
        '--csv-dir',
        default='../output_csv',
        help='Directory containing CSV files (default: ../output_csv)'
    )
    
    parser.add_argument(
        '--no-create-schema',
        action='store_true',
        help='Skip schema creation (useful if schema already exists)'
    )
    
    args = parser.parse_args()
    
    # Build connection string
    conn_string = parse_connection_string(args)
    
    if not conn_string:
        parser.error("Please provide either --connection-string or --host/--database/--user/--password")
    
    # Run import
    importer = DatabaseImporter(conn_string, args.csv_dir)
    importer.run(create_schema=not args.no_create_schema)


if __name__ == '__main__':
    main()

