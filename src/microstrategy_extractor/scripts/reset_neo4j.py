#!/usr/bin/env python3
"""
Neo4j Database Reset Script

This script completely wipes the Neo4j database, removing all nodes, relationships,
constraints, and indexes. Optionally, it can also drop the database entirely from Neo4j.
Use with caution!

Usage:
    # Interactive mode (safest - requires confirmation)
    python -m microstrategy_extractor.scripts.reset_neo4j
    
    # Preview without executing
    python -m microstrategy_extractor.scripts.reset_neo4j --dry-run
    
    # Force reset without confirmation
    python -m microstrategy_extractor.scripts.reset_neo4j --force
    
    # Drop the database completely (Enterprise Edition only)
    python -m microstrategy_extractor.scripts.reset_neo4j --drop-db
    
    # Custom connection
    python -m microstrategy_extractor.scripts.reset_neo4j --uri bolt://localhost:7687 --user neo4j --password mypass
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional
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


class Neo4jDatabaseResetter:
    """Reset Neo4j database by deleting all data, constraints, and indexes."""
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
        dry_run: bool = False,
        force: bool = False,
        drop_db: bool = False
    ):
        """
        Initialize the database resetter.
        
        Args:
            uri: Neo4j connection URI (e.g., bolt://localhost:7687)
            user: Neo4j username
            password: Neo4j password
            database: Database name (default: neo4j)
            dry_run: If True, show what would be deleted without executing
            force: If True, skip interactive confirmation
            drop_db: If True, drop the database completely after clearing it
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.dry_run = dry_run
        self.force = force
        self.drop_db = drop_db
        self.driver: Optional[Driver] = None
        
        # Statistics
        self.stats = {
            "nodes_by_label": {},
            "total_nodes": 0,
            "total_relationships": 0,
            "constraints": [],
            "indexes": []
        }
    
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
            if self.dry_run:
                print(f"✓ Connected to Neo4j at {self.uri} (DRY RUN - will not modify data)")
            else:
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
    
    def collect_statistics(self) -> bool:
        """
        Collect current database statistics.
        
        Returns:
            bool: True if successful
        """
        try:
            with self.driver.session(database=self.database) as session:
                # Count nodes by label
                labels = ["Report", "Dataset", "Attribute", "Metric", "Fact", 
                         "Function", "Table", "Form", "User", "Environment"]
                
                for label in labels:
                    result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                    count = result.single()["count"]
                    if count > 0:
                        self.stats["nodes_by_label"][label] = count
                        self.stats["total_nodes"] += count
                
                # Count nodes without specific labels
                result = session.run("""
                    MATCH (n)
                    WHERE size(labels(n)) = 0
                    RETURN count(n) as count
                """)
                unlabeled = result.single()["count"]
                if unlabeled > 0:
                    self.stats["nodes_by_label"]["Unlabeled"] = unlabeled
                    self.stats["total_nodes"] += unlabeled
                
                # Count total relationships
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                self.stats["total_relationships"] = result.single()["count"]
                
                # Get constraints
                result = session.run("SHOW CONSTRAINTS")
                self.stats["constraints"] = [
                    {
                        "name": record.get("name"),
                        "type": record.get("type"),
                        "entityType": record.get("entityType"),
                        "labelsOrTypes": record.get("labelsOrTypes"),
                        "properties": record.get("properties")
                    }
                    for record in result
                ]
                
                # Get indexes
                result = session.run("SHOW INDEXES")
                self.stats["indexes"] = [
                    {
                        "name": record.get("name"),
                        "type": record.get("type"),
                        "entityType": record.get("entityType"),
                        "labelsOrTypes": record.get("labelsOrTypes"),
                        "properties": record.get("properties")
                    }
                    for record in result
                ]
            
            return True
        except Exception as e:
            print(f"✗ Error collecting statistics: {e}")
            return False
    
    def display_statistics(self):
        """Display current database statistics."""
        print("\n📊 Current Database Statistics:")
        print()
        
        if self.stats["nodes_by_label"]:
            print("  Nodes by Label:")
            for label, count in sorted(self.stats["nodes_by_label"].items(), key=lambda x: x[1], reverse=True):
                print(f"    {label}: {count:,}")
        else:
            print("  No nodes found")
        
        print()
        print(f"  Total Nodes: {self.stats['total_nodes']:,}")
        print(f"  Total Relationships: {self.stats['total_relationships']:,}")
        print()
        print(f"  Constraints: {len(self.stats['constraints'])}")
        print(f"  Indexes: {len(self.stats['indexes'])}")
    
    def confirm_reset(self) -> bool:
        """
        Request user confirmation for reset operation.
        
        Returns:
            bool: True if user confirms, False otherwise
        """
        if self.force:
            print("\n⚠️  FORCE MODE: Skipping confirmation")
            return True
        
        if self.dry_run:
            print("\n[DRY RUN] Would request user confirmation")
            return True
        
        print("\n" + "=" * 70)
        if self.drop_db:
            print("⚠️  WARNING: This will PERMANENTLY DELETE the database from Neo4j!")
            print("    - All data, constraints, and indexes will be deleted")
            print("    - The database itself will be dropped and no longer exist")
        else:
            print("⚠️  WARNING: This will PERMANENTLY DELETE all data, constraints, and indexes!")
        print("=" * 70)
        print()
        
        # Check if database is empty
        if self.stats["total_nodes"] == 0 and len(self.stats["constraints"]) == 0 and len(self.stats["indexes"]) == 0:
            print("ℹ️  Database is already empty. Nothing to reset.")
            return False
        
        try:
            response = input("Type 'yes' to confirm reset: ").strip().lower()
            if response == "yes":
                print("\n✓ Reset confirmed")
                return True
            else:
                print("\n✗ Reset cancelled")
                return False
        except (KeyboardInterrupt, EOFError):
            print("\n\n✗ Reset cancelled by user")
            return False
    
    def delete_all_nodes_and_relationships(self) -> bool:
        """
        Delete all nodes and relationships from the database.
        
        Returns:
            bool: True if successful
        """
        if self.stats["total_nodes"] == 0:
            print("\n📭 No nodes to delete")
            return True
        
        print(f"\n🗑️  Deleting {self.stats['total_nodes']:,} nodes and {self.stats['total_relationships']:,} relationships...")
        
        if self.dry_run:
            print("  [DRY RUN] Would execute: MATCH (n) DETACH DELETE n")
            return True
        
        try:
            with self.driver.session(database=self.database) as session:
                session.run("MATCH (n) DETACH DELETE n")
            print(f"  ✓ Successfully deleted all nodes and relationships")
            return True
        except Exception as e:
            print(f"  ✗ Error deleting nodes: {e}")
            return False
    
    def drop_all_constraints(self) -> bool:
        """
        Drop all constraints from the database.
        
        Returns:
            bool: True if successful
        """
        if not self.stats["constraints"]:
            print("\n📭 No constraints to drop")
            return True
        
        print(f"\n🗑️  Dropping {len(self.stats['constraints'])} constraints...")
        
        if self.dry_run:
            print("  [DRY RUN] Would drop the following constraints:")
            for constraint in self.stats["constraints"]:
                print(f"    - {constraint['name']}")
            return True
        
        success_count = 0
        error_count = 0
        
        try:
            with self.driver.session(database=self.database) as session:
                for constraint in self.stats["constraints"]:
                    constraint_name = constraint["name"]
                    try:
                        session.run(f"DROP CONSTRAINT {constraint_name}")
                        print(f"  ✓ Dropped constraint: {constraint_name}")
                        success_count += 1
                    except Exception as e:
                        print(f"  ✗ Error dropping constraint {constraint_name}: {e}")
                        error_count += 1
            
            if error_count == 0:
                print(f"  ✓ Successfully dropped all {success_count} constraints")
                return True
            else:
                print(f"  ⚠️  Dropped {success_count} constraints, {error_count} errors")
                return False
        except Exception as e:
            print(f"  ✗ Error dropping constraints: {e}")
            return False
    
    def drop_all_indexes(self) -> bool:
        """
        Drop all indexes from the database.
        
        Returns:
            bool: True if successful
        """
        if not self.stats["indexes"]:
            print("\n📭 No indexes to drop")
            return True
        
        print(f"\n🗑️  Dropping {len(self.stats['indexes'])} indexes...")
        
        if self.dry_run:
            print("  [DRY RUN] Would drop the following indexes:")
            for index in self.stats["indexes"]:
                print(f"    - {index['name']}")
            return True
        
        success_count = 0
        error_count = 0
        
        try:
            with self.driver.session(database=self.database) as session:
                for index in self.stats["indexes"]:
                    index_name = index["name"]
                    try:
                        session.run(f"DROP INDEX {index_name}")
                        print(f"  ✓ Dropped index: {index_name}")
                        success_count += 1
                    except Exception as e:
                        print(f"  ✗ Error dropping index {index_name}: {e}")
                        error_count += 1
            
            if error_count == 0:
                print(f"  ✓ Successfully dropped all {success_count} indexes")
                return True
            else:
                print(f"  ⚠️  Dropped {success_count} indexes, {error_count} errors")
                return False
        except Exception as e:
            print(f"  ✗ Error dropping indexes: {e}")
            return False
    
    def verify_database_empty(self) -> bool:
        """
        Verify that the database is completely empty.
        
        Returns:
            bool: True if database is empty
        """
        if self.dry_run:
            print("\n[DRY RUN] Would verify database is empty")
            return True
        
        print("\n🔍 Verifying database is empty...")
        
        try:
            with self.driver.session(database=self.database) as session:
                # Count nodes
                result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = result.single()["count"]
                
                # Count relationships
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = result.single()["count"]
                
                # Count constraints
                result = session.run("SHOW CONSTRAINTS")
                constraint_count = len(list(result))
                
                # Count indexes
                result = session.run("SHOW INDEXES")
                index_count = len(list(result))
                
                if node_count == 0 and rel_count == 0 and constraint_count == 0 and index_count == 0:
                    print("  ✓ Database is completely empty")
                    return True
                else:
                    print(f"  ⚠️  Database not completely empty:")
                    if node_count > 0:
                        print(f"    - {node_count} nodes remaining")
                    if rel_count > 0:
                        print(f"    - {rel_count} relationships remaining")
                    if constraint_count > 0:
                        print(f"    - {constraint_count} constraints remaining")
                    if index_count > 0:
                        print(f"    - {index_count} indexes remaining")
                    return False
        except Exception as e:
            print(f"  ✗ Error verifying database: {e}")
            return False
    
    def drop_database(self) -> bool:
        """
        Drop the database completely from Neo4j.
        
        Returns:
            bool: True if successful
        """
        print(f"\n💣 Dropping database '{self.database}' from Neo4j...")
        
        if self.dry_run:
            print(f"  [DRY RUN] Would execute: DROP DATABASE `{self.database}`")
            return True
        
        try:
            # Need to connect to system database to drop another database
            with self.driver.session(database="system") as session:
                # Check if database exists first
                result = session.run("SHOW DATABASES")
                databases = [record["name"] for record in result]
                
                if self.database not in databases:
                    print(f"  ℹ️  Database '{self.database}' does not exist (already dropped or never created)")
                    return True
                
                # Try to drop the database
                try:
                    session.run(f"DROP DATABASE `{self.database}`")
                    print(f"  ✓ Successfully dropped database '{self.database}'")
                    return True
                except Exception as drop_error:
                    error_msg = str(drop_error)
                    if "Unsupported administration command" in error_msg or "UnsupportedAdministrationCommand" in error_msg:
                        print(f"  ⚠️  Cannot drop database: Neo4j Community Edition does not support dropping databases")
                        print(f"     The database has been cleared but still exists")
                        return False
                    elif "default database" in error_msg.lower() or "cannot drop the default database" in error_msg.lower():
                        print(f"  ⚠️  Cannot drop default database '{self.database}'")
                        print(f"     The database has been cleared but cannot be dropped")
                        return False
                    else:
                        print(f"  ✗ Failed to drop database: {drop_error}")
                        return False
        except Exception as e:
            error_msg = str(e)
            if "Unsupported administration command" in error_msg or "UnsupportedAdministrationCommand" in error_msg:
                print(f"  ⚠️  Cannot drop database: Neo4j Community Edition does not support multiple databases")
                print(f"     The database has been cleared but cannot be dropped")
                return False
            else:
                print(f"  ✗ Error dropping database: {e}")
                return False
    
    def reset(self) -> bool:
        """
        Execute the complete database reset.
        
        Returns:
            bool: True if successful
        """
        print("=" * 70)
        print("Neo4j Database Reset")
        print("=" * 70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Database: {self.database}")
        print(f"URI: {self.uri}")
        if self.dry_run:
            print("Mode: DRY RUN (no changes will be made)")
        elif self.force:
            print("Mode: FORCE (no confirmation required)")
        else:
            print("Mode: INTERACTIVE (confirmation required)")
        if self.drop_db:
            print("Action: CLEAR DATA + DROP DATABASE")
        else:
            print("Action: CLEAR DATA ONLY (keep database)")
        print("=" * 70)
        
        # Connect to database
        if not self.connect():
            return False
        
        try:
            # Collect statistics
            if not self.collect_statistics():
                return False
            
            # Display statistics
            self.display_statistics()
            
            # Request confirmation
            if not self.confirm_reset():
                return False
            
            # Execute reset operations
            print("\n" + "=" * 70)
            print("Executing Reset Operations")
            print("=" * 70)
            
            # Delete all nodes and relationships
            if not self.delete_all_nodes_and_relationships():
                print("\n⚠️  Warning: Failed to delete all nodes and relationships")
            
            # Drop all constraints
            if not self.drop_all_constraints():
                print("\n⚠️  Warning: Failed to drop all constraints")
            
            # Drop all indexes
            if not self.drop_all_indexes():
                print("\n⚠️  Warning: Failed to drop all indexes")
            
            # Verify database is empty
            if not self.dry_run:
                self.verify_database_empty()
            
            # Drop database if requested
            if self.drop_db:
                drop_success = self.drop_database()
                if not drop_success and not self.dry_run:
                    print("\n⚠️  Warning: Database was cleared but could not be dropped")
            
            # Success message
            print("\n" + "=" * 70)
            if self.dry_run:
                print("✓ Dry run complete - no changes were made")
            else:
                if self.drop_db:
                    print("✓ Database reset and drop complete!")
                else:
                    print("✓ Database reset complete!")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error during reset: {e}")
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
        # Go up 3 levels: scripts -> microstrategy_extractor -> src -> project_root
        project_root = Path(__file__).parent.parent.parent.parent
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
        description="Reset Neo4j database (delete all data, constraints, and indexes)",
        epilog="WARNING: This operation is IRREVERSIBLE. Use with caution!"
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without executing (safe preview mode)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip interactive confirmation (use with caution!)"
    )
    parser.add_argument(
        "--drop-db",
        action="store_true",
        help="Drop the database completely from Neo4j (Enterprise Edition only)"
    )
    
    args = parser.parse_args()
    
    # Cannot use both dry-run and force
    if args.dry_run and args.force:
        print("✗ Error: --dry-run and --force cannot be used together")
        sys.exit(1)
    
    # Load configuration from environment
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
    
    # Create resetter and execute
    resetter = Neo4jDatabaseResetter(
        uri=config["uri"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        dry_run=args.dry_run,
        force=args.force,
        drop_db=args.drop_db
    )
    
    success = resetter.reset()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

