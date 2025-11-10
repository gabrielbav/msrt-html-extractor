#!/usr/bin/env python3
"""
Neo4j Schema Initialization Script

This script creates all necessary constraints and indexes for the MicroStrategy
graph model in Neo4j. It should be run once after starting the Neo4j container
and before loading any data.

Usage:
    python scripts/init_neo4j_schema.py
    python scripts/init_neo4j_schema.py --uri bolt://localhost:7687 --user neo4j --password mypassword
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
import argparse
from datetime import datetime

try:
    from neo4j import GraphDatabase, Driver
    from neo4j.exceptions import ClientError
except ImportError:
    print("Error: neo4j driver not installed. Install with: pip install neo4j")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")
    load_dotenv = None


class Neo4jSchemaInitializer:
    """Initialize Neo4j schema with constraints and indexes."""
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """
        Initialize the schema initializer.
        
        Args:
            uri: Neo4j connection URI (e.g., bolt://localhost:7687)
            user: Neo4j username
            password: Neo4j password
            database: Database name (default: neo4j)
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver: Driver = None
        
    def connect(self) -> bool:
        """
        Connect to Neo4j database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test connection
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                result.single()
            print(f"✓ Connected to Neo4j at {self.uri}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Neo4j: {e}")
            return False
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            print("✓ Connection closed")
    
    def _execute_query(self, query: str, description: str) -> bool:
        """
        Execute a single query and handle errors.
        
        Args:
            query: Cypher query to execute
            description: Human-readable description for logging
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.driver.session(database=self.database) as session:
                session.run(query)
            print(f"  ✓ {description}")
            return True
        except ClientError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e) or "already exists" in str(e):
                print(f"  ⊙ {description} (already exists)")
                return True
            else:
                print(f"  ✗ {description}: {e}")
                return False
        except Exception as e:
            print(f"  ✗ {description}: {e}")
            return False
    
    def create_constraints(self) -> Dict[str, bool]:
        """
        Create all unique constraints.
        
        Returns:
            dict: Results of constraint creation
        """
        print("\n📋 Creating Constraints...")
        
        constraints = [
            (
                "CREATE CONSTRAINT report_id_unique IF NOT EXISTS "
                "FOR (r:Report) REQUIRE r.id IS UNIQUE",
                "Report(id) unique constraint"
            ),
            (
                "CREATE CONSTRAINT dataset_id_unique IF NOT EXISTS "
                "FOR (d:Dataset) REQUIRE d.id IS UNIQUE",
                "Dataset(id) unique constraint"
            ),
            (
                "CREATE CONSTRAINT attribute_id_unique IF NOT EXISTS "
                "FOR (a:Attribute) REQUIRE a.id IS UNIQUE",
                "Attribute(id) unique constraint"
            ),
            (
                "CREATE CONSTRAINT metric_id_unique IF NOT EXISTS "
                "FOR (m:Metric) REQUIRE m.id IS UNIQUE",
                "Metric(id) unique constraint"
            ),
            (
                "CREATE CONSTRAINT fact_id_unique IF NOT EXISTS "
                "FOR (f:Fact) REQUIRE f.id IS UNIQUE",
                "Fact(id) unique constraint"
            ),
            (
                "CREATE CONSTRAINT table_id_unique IF NOT EXISTS "
                "FOR (t:Table) REQUIRE t.id IS UNIQUE",
                "Table(id) unique constraint"
            ),
            (
                "CREATE CONSTRAINT environment_id_unique IF NOT EXISTS "
                "FOR (e:Environment) REQUIRE e.id IS UNIQUE",
                "Environment(id) unique constraint"
            ),
            (
                "CREATE CONSTRAINT function_composite_unique IF NOT EXISTS "
                "FOR (f:Function) REQUIRE (f.name, f.file_path) IS UNIQUE",
                "Function(name, file_path) composite unique constraint"
            ),
        ]
        
        results = {}
        for query, description in constraints:
            results[description] = self._execute_query(query, description)
        
        return results
    
    def create_indexes(self) -> Dict[str, bool]:
        """
        Create all performance indexes.
        
        Returns:
            dict: Results of index creation
        """
        print("\n📊 Creating Indexes...")
        
        indexes = [
            # Name-based indexes
            (
                "CREATE INDEX report_name_index IF NOT EXISTS "
                "FOR (r:Report) ON (r.name)",
                "Report.name index"
            ),
            (
                "CREATE INDEX dataset_name_index IF NOT EXISTS "
                "FOR (d:Dataset) ON (d.name)",
                "Dataset.name index"
            ),
            (
                "CREATE INDEX attribute_name_index IF NOT EXISTS "
                "FOR (a:Attribute) ON (a.name)",
                "Attribute.name index"
            ),
            (
                "CREATE INDEX metric_name_index IF NOT EXISTS "
                "FOR (m:Metric) ON (m.name)",
                "Metric.name index"
            ),
            (
                "CREATE INDEX fact_name_index IF NOT EXISTS "
                "FOR (f:Fact) ON (f.name)",
                "Fact.name index"
            ),
            (
                "CREATE INDEX table_name_index IF NOT EXISTS "
                "FOR (t:Table) ON (t.name)",
                "Table.name index"
            ),
            (
                "CREATE INDEX environment_name_index IF NOT EXISTS "
                "FOR (e:Environment) ON (e.name)",
                "Environment.name index"
            ),
            # Type filtering indexes
            (
                "CREATE INDEX metric_tipo_index IF NOT EXISTS "
                "FOR (m:Metric) ON (m.tipo)",
                "Metric.tipo index"
            ),
            (
                "CREATE INDEX dataset_application_object_index IF NOT EXISTS "
                "FOR (d:Dataset) ON (d.applicationObject)",
                "Dataset.applicationObject index"
            ),
        ]
        
        results = {}
        for query, description in indexes:
            results[description] = self._execute_query(query, description)
        
        return results
    
    def verify_schema(self) -> Dict[str, int]:
        """
        Verify the schema by counting constraints and indexes.
        
        Returns:
            dict: Statistics about the schema
        """
        print("\n🔍 Verifying Schema...")
        
        stats = {}
        
        try:
            with self.driver.session(database=self.database) as session:
                # Count constraints
                result = session.run("SHOW CONSTRAINTS")
                constraints = list(result)
                stats["constraints"] = len(constraints)
                print(f"  ✓ Found {len(constraints)} constraints")
                
                # Count indexes
                result = session.run("SHOW INDEXES")
                indexes = list(result)
                stats["indexes"] = len(indexes)
                print(f"  ✓ Found {len(indexes)} indexes")
                
        except Exception as e:
            print(f"  ✗ Error verifying schema: {e}")
        
        return stats
    
    def display_statistics(self):
        """Display current database statistics."""
        print("\n📈 Database Statistics:")
        
        try:
            with self.driver.session(database=self.database) as session:
                # Count nodes by label
                labels = ["Report", "Dataset", "Attribute", "Metric", "Fact", 
                         "Function", "Table", "Form", "Environment"]
                
                for label in labels:
                    result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                    count = result.single()["count"]
                    print(f"  {label}: {count} nodes")
                
                # Count relationships
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                count = result.single()["count"]
                print(f"  Total Relationships: {count}")
                
        except Exception as e:
            print(f"  ✗ Error getting statistics: {e}")
    
    def initialize(self) -> bool:
        """
        Initialize the complete schema.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        print("=" * 60)
        print("Neo4j Schema Initialization")
        print("=" * 60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Database: {self.database}")
        
        if not self.connect():
            return False
        
        try:
            # Create constraints
            constraint_results = self.create_constraints()
            constraint_success = sum(1 for v in constraint_results.values() if v)
            print(f"\n✓ Created {constraint_success}/{len(constraint_results)} constraints")
            
            # Create indexes
            index_results = self.create_indexes()
            index_success = sum(1 for v in index_results.values() if v)
            print(f"✓ Created {index_success}/{len(index_results)} indexes")
            
            # Verify schema
            stats = self.verify_schema()
            
            # Display statistics
            self.display_statistics()
            
            print("\n" + "=" * 60)
            print("✓ Schema initialization complete!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error during initialization: {e}")
            return False
        finally:
            self.close()


def load_config_from_env() -> Dict[str, str]:
    """
    Load Neo4j configuration from environment variables.
    
    Returns:
        dict: Configuration dictionary
    """
    # Try to load .env file if dotenv is available
    if load_dotenv:
        project_root = Path(__file__).parent.parent
        env_file = project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
    
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password"),
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize Neo4j schema with constraints and indexes"
    )
    parser.add_argument(
        "--uri",
        help="Neo4j connection URI (default: from NEO4J_URI env or bolt://localhost:7687)"
    )
    parser.add_argument(
        "--user",
        help="Neo4j username (default: from NEO4J_USER env or 'neo4j')"
    )
    parser.add_argument(
        "--password",
        help="Neo4j password (default: from NEO4J_PASSWORD env or 'password')"
    )
    parser.add_argument(
        "--database",
        help="Neo4j database name (default: from NEO4J_DATABASE env or 'neo4j')"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config_from_env()
    
    # Override with command-line arguments if provided
    if args.uri:
        config["uri"] = args.uri
    if args.user:
        config["user"] = args.user
    if args.password:
        config["password"] = args.password
    if args.database:
        config["database"] = args.database
    
    # Initialize schema
    initializer = Neo4jSchemaInitializer(
        uri=config["uri"],
        user=config["user"],
        password=config["password"],
        database=config["database"]
    )
    
    success = initializer.initialize()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

