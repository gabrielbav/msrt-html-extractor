#!/usr/bin/env python3
"""
Neo4j Data Loading Script

This script loads MicroStrategy data from JSON output into Neo4j graph database.
It uses MERGE operations to support both insert and update, preventing duplicates.
All data is linked to an Environment node for versioning and tracking.

Usage:
    # Load data
    python scripts/load_to_neo4j.py --json-file output.json --environment-id prod-2024 --environment-name "Production"
    python scripts/load_to_neo4j.py --json-file output.json --environment-id dev --environment-name "Development" --entities reports,datasets
    python scripts/load_to_neo4j.py --json-file output.json --environment-id test --environment-name "Test" --dry-run
    
    # Delete data by environment
    python scripts/load_to_neo4j.py --environment-id prod-2024 --delete-environment
    python scripts/load_to_neo4j.py --environment-id prod-2024 --delete-environment --dry-run
    
    # Delete data by report
    python scripts/load_to_neo4j.py --environment-id prod-2024 --delete-report 8B2ED31E4C5E988B93B1C69081C7C66C
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from datetime import datetime
from collections import defaultdict

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


class Neo4jDataLoader:
    """Load MicroStrategy data into Neo4j graph database."""
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str,
        environment_id: str,
        environment_name: str,
        batch_size: int = 100,
        dry_run: bool = False
    ):
        """
        Initialize the data loader.
        
        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
            database: Database name
            environment_id: Environment identifier for this data load
            environment_name: Human-readable environment name
            batch_size: Number of nodes to process in each batch
            dry_run: If True, show what would be loaded without executing
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.environment_id = environment_id
        self.environment_name = environment_name
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.driver: Optional[Driver] = None
        
        # Statistics tracking
        self.stats = defaultdict(int)
        self.errors = []
        
    def connect(self) -> bool:
        """Connect to Neo4j database."""
        if self.dry_run:
            print("✓ [DRY RUN] Would connect to Neo4j")
            return True
        
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
        if self.driver and not self.dry_run:
            self.driver.close()
            print("✓ Connection closed")
    
    def _execute_batch(self, query: str, parameters: List[Dict], description: str) -> int:
        """
        Execute a batch query.
        
        Args:
            query: Cypher query with parameters
            parameters: List of parameter dictionaries for batch processing
            description: Human-readable description for logging
            
        Returns:
            int: Number of records processed
        """
        if not parameters:
            return 0
        
        if self.dry_run:
            print(f"  [DRY RUN] Would execute: {description} ({len(parameters)} records)")
            return len(parameters)
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, {
                    "batch": parameters,
                    "env_id": self.environment_id
                })
                summary = result.consume()
                return len(parameters)
        except Exception as e:
            self.errors.append(f"{description}: {e}")
            print(f"  ✗ Error in {description}: {e}")
            return 0
    
    def create_environment(self) -> bool:
        """Create or update the Environment node."""
        print(f"\n🌍 Creating Environment: {self.environment_name} ({self.environment_id})")
        
        if self.dry_run:
            print("  [DRY RUN] Would create/update Environment node")
            return True
        
        query = """
        MERGE (e:Environment {id: $env_id})
        ON CREATE SET e.created_at = datetime()
        SET e.name = $env_name,
            e.updated_at = datetime()
        RETURN e
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                session.run(query, {
                    "env_id": self.environment_id,
                    "env_name": self.environment_name
                })
            print(f"  ✓ Environment created/updated")
            return True
        except Exception as e:
            print(f"  ✗ Error creating environment: {e}")
            return False
    
    def load_reports(self, reports: List[Dict]) -> int:
        """Load Report nodes."""
        print(f"\n📊 Loading {len(reports)} Reports...")
        
        query = """
        UNWIND $batch as row
        MERGE (r:Report {id: row.id})
        ON CREATE SET r.created_at = datetime()
        SET r.name = row.name,
            r.file_path = row.file_path,
            r.updated_at = datetime()
        
        WITH r
        MERGE (e:Environment {id: $env_id})
        MERGE (r)-[rel:BELONGS_TO]->(e)
        SET rel.loaded_at = datetime()
        """
        
        batch = []
        total = 0
        
        for report in reports:
            batch.append({
                "id": report.get("id"),
                "name": report.get("name"),
                "file_path": report.get("file_path")
            })
            
            if len(batch) >= self.batch_size:
                count = self._execute_batch(query, batch, "Reports")
                total += count
                self.stats["reports"] += count
                batch = []
        
        # Process remaining
        if batch:
            count = self._execute_batch(query, batch, "Reports")
            total += count
            self.stats["reports"] += count
        
        print(f"  ✓ Loaded {total} reports")
        return total
    
    def load_datasets(self, reports: List[Dict]) -> int:
        """Load Dataset nodes and CONTAINS relationships."""
        print(f"\n📦 Loading Datasets...")
        
        query = """
        UNWIND $batch as row
        MERGE (d:Dataset {id: row.id})
        ON CREATE SET d.created_at = datetime()
        SET d.name = row.name,
            d.file_path = row.file_path,
            d.applicationObject = row.applicationObject,
            d.graphic = row.graphic,
            d.updated_at = datetime()
        
        WITH d, row
        MERGE (e:Environment {id: $env_id})
        MERGE (d)-[rel:BELONGS_TO]->(e)
        SET rel.loaded_at = datetime()
        
        WITH d, row
        MERGE (r:Report {id: row.report_id})
        MERGE (r)-[:CONTAINS]->(d)
        """
        
        batch = []
        total = 0
        
        for report in reports:
            report_id = report.get("id")
            for dataset in report.get("datasets", []):
                batch.append({
                    "id": dataset.get("id"),
                    "name": dataset.get("name"),
                    "file_path": dataset.get("file_path"),
                    "applicationObject": dataset.get("applicationObject"),
                    "graphic": dataset.get("graphic"),
                    "report_id": report_id
                })
                
                if len(batch) >= self.batch_size:
                    count = self._execute_batch(query, batch, "Datasets")
                    total += count
                    self.stats["datasets"] += count
                    batch = []
        
        if batch:
            count = self._execute_batch(query, batch, "Datasets")
            total += count
            self.stats["datasets"] += count
        
        print(f"  ✓ Loaded {total} datasets")
        return total
    
    def load_attributes(self, reports: List[Dict]) -> int:
        """Load Attribute nodes and HAS_ATTRIBUTE relationships."""
        print(f"\n🏷️  Loading Attributes...")
        
        query = """
        UNWIND $batch as row
        MERGE (a:Attribute {id: row.id})
        ON CREATE SET a.created_at = datetime()
        SET a.name = row.name,
            a.name_on_dataset = row.name_on_dataset,
            a.file_path = row.file_path,
            a.applicationSchema = row.applicationSchema,
            a.updated_at = datetime()
        
        WITH a, row
        MERGE (e:Environment {id: $env_id})
        MERGE (a)-[rel:BELONGS_TO]->(e)
        SET rel.loaded_at = datetime()
        
        WITH a, row
        MERGE (d:Dataset {id: row.dataset_id})
        MERGE (d)-[:HAS_ATTRIBUTE]->(a)
        """
        
        batch = []
        total = 0
        
        for report in reports:
            for dataset in report.get("datasets", []):
                dataset_id = dataset.get("id")
                for attribute in dataset.get("atributos", []):
                    batch.append({
                        "id": attribute.get("id"),
                        "name": attribute.get("name"),
                        "name_on_dataset": attribute.get("name_on_dataset"),
                        "file_path": attribute.get("file_path"),
                        "applicationSchema": attribute.get("applicationSchema"),
                        "dataset_id": dataset_id
                    })
                    
                    if len(batch) >= self.batch_size:
                        count = self._execute_batch(query, batch, "Attributes")
                        total += count
                        self.stats["attributes"] += count
                        batch = []
        
        if batch:
            count = self._execute_batch(query, batch, "Attributes")
            total += count
            self.stats["attributes"] += count
        
        print(f"  ✓ Loaded {total} attributes")
        return total
    
    def load_forms_and_tables(self, reports: List[Dict]) -> tuple:
        """Load Form nodes, Table nodes, and their relationships."""
        print(f"\n📝 Loading Forms and Tables...")
        
        # Load Forms and HAS_FORM relationships
        form_query = """
        UNWIND $batch as row
        MERGE (a:Attribute {id: row.attribute_id})
        MERGE (f:Form {attribute_id: row.attribute_id, name: row.form_name})
        ON CREATE SET f.created_at = datetime()
        SET f.name = row.form_name,
            f.updated_at = datetime()
        
        WITH f, row
        MERGE (e:Environment {id: $env_id})
        MERGE (f)-[rel:BELONGS_TO]->(e)
        SET rel.loaded_at = datetime()
        
        WITH f, row
        MATCH (a:Attribute {id: row.attribute_id})
        MERGE (a)-[:HAS_FORM]->(f)
        """
        
        # Load Tables and USES_TABLE relationships
        table_query = """
        UNWIND $batch as row
        MERGE (t:Table {id: row.table_id})
        ON CREATE SET t.created_at = datetime()
        SET t.name = row.table_name,
            t.file_path = row.file_path,
            t.updated_at = datetime()
        
        WITH t, row
        MERGE (e:Environment {id: $env_id})
        MERGE (t)-[rel:BELONGS_TO]->(e)
        SET rel.loaded_at = datetime()
        
        WITH t, row
        MATCH (f:Form {attribute_id: row.attribute_id, name: row.form_name})
        MERGE (f)-[ut:USES_TABLE]->(t)
        SET ut.column_name = row.column_name
        """
        
        form_batch = []
        table_batch = []
        forms_processed = set()
        total_forms = 0
        total_tables = 0
        
        for report in reports:
            for dataset in report.get("datasets", []):
                for attribute in dataset.get("atributos", []):
                    attribute_id = attribute.get("id")
                    
                    for form in attribute.get("formularios", []):
                        form_name = form.get("name")
                        form_key = (attribute_id, form_name)
                        
                        # Load form only once per attribute
                        if form_key not in forms_processed:
                            form_batch.append({
                                "attribute_id": attribute_id,
                                "form_name": form_name
                            })
                            forms_processed.add(form_key)
                            
                            if len(form_batch) >= self.batch_size:
                                count = self._execute_batch(form_query, form_batch, "Forms")
                                total_forms += count
                                self.stats["forms"] += count
                                form_batch = []
                        
                        # Load tables for this form
                        for table in form.get("logic_tables", []):
                            table_batch.append({
                                "attribute_id": attribute_id,
                                "form_name": form_name,
                                "table_id": table.get("id"),
                                "table_name": table.get("name"),
                                "file_path": table.get("file_path"),
                                "column_name": table.get("column_name")
                            })
                            
                            if len(table_batch) >= self.batch_size:
                                count = self._execute_batch(table_query, table_batch, "Tables (from Forms)")
                                total_tables += count
                                self.stats["tables"] += count
                                table_batch = []
        
        # Process remaining batches
        if form_batch:
            count = self._execute_batch(form_query, form_batch, "Forms")
            total_forms += count
            self.stats["forms"] += count
        
        if table_batch:
            count = self._execute_batch(table_query, table_batch, "Tables (from Forms)")
            total_tables += count
            self.stats["tables"] += count
        
        print(f"  ✓ Loaded {total_forms} forms and {total_tables} tables (from attributes)")
        return total_forms, total_tables
    
    def load_metrics(self, reports: List[Dict]) -> int:
        """Load Metric nodes and HAS_METRIC relationships."""
        print(f"\n📈 Loading Metrics...")
        
        query = """
        UNWIND $batch as row
        MERGE (m:Metric {id: row.id})
        ON CREATE SET m.created_at = datetime()
        SET m.name = row.name,
            m.file_path = row.file_path,
            m.applicationObject = row.applicationObject,
            m.tipo = row.tipo,
            m.formula = row.formula,
            m.updated_at = datetime()
        
        WITH m, row
        MERGE (e:Environment {id: $env_id})
        MERGE (m)-[rel:BELONGS_TO]->(e)
        SET rel.loaded_at = datetime()
        
        WITH m, row
        MERGE (d:Dataset {id: row.dataset_id})
        MERGE (d)-[:HAS_METRIC]->(m)
        """
        
        batch = []
        total = 0
        
        for report in reports:
            for dataset in report.get("datasets", []):
                dataset_id = dataset.get("id")
                for metric in dataset.get("metricas", []):
                    batch.append({
                        "id": metric.get("id"),
                        "name": metric.get("name"),
                        "file_path": metric.get("file_path"),
                        "applicationObject": metric.get("applicationObject"),
                        "tipo": metric.get("tipo"),
                        "formula": metric.get("formula"),
                        "dataset_id": dataset_id
                    })
                    
                    if len(batch) >= self.batch_size:
                        count = self._execute_batch(query, batch, "Metrics")
                        total += count
                        self.stats["metrics"] += count
                        batch = []
        
        if batch:
            count = self._execute_batch(query, batch, "Metrics")
            total += count
            self.stats["metrics"] += count
        
        print(f"  ✓ Loaded {total} metrics")
        return total
    
    def load_functions(self, reports: List[Dict]) -> int:
        """Load Function nodes and USES_FUNCTION relationships."""
        print(f"\n⚙️  Loading Functions...")
        
        query = """
        UNWIND $batch as row
        MERGE (f:Function {name: row.function_name, file_path: row.file_path})
        ON CREATE SET f.created_at = datetime()
        SET f.updated_at = datetime()
        
        WITH f, row
        MERGE (e:Environment {id: $env_id})
        MERGE (f)-[rel:BELONGS_TO]->(e)
        SET rel.loaded_at = datetime()
        
        WITH f, row
        MERGE (m:Metric {id: row.metric_id})
        MERGE (m)-[:USES_FUNCTION]->(f)
        """
        
        batch = []
        total = 0
        
        for report in reports:
            for dataset in report.get("datasets", []):
                for metric in dataset.get("metricas", []):
                    function = metric.get("function")
                    if function and metric.get("tipo") == "simples":
                        batch.append({
                            "metric_id": metric.get("id"),
                            "function_name": function.get("name"),
                            "file_path": function.get("file_path")
                        })
                        
                        if len(batch) >= self.batch_size:
                            count = self._execute_batch(query, batch, "Functions")
                            total += count
                            self.stats["functions"] += count
                            batch = []
        
        if batch:
            count = self._execute_batch(query, batch, "Functions")
            total += count
            self.stats["functions"] += count
        
        print(f"  ✓ Loaded {total} functions")
        return total
    
    def load_facts(self, reports: List[Dict]) -> int:
        """Load Fact nodes and USES_FACT relationships."""
        print(f"\n🔢 Loading Facts...")
        
        query = """
        UNWIND $batch as row
        MERGE (f:Fact {id: row.id})
        ON CREATE SET f.created_at = datetime()
        SET f.name = row.name,
            f.file_path = row.file_path,
            f.applicationObject = row.applicationObject,
            f.updated_at = datetime()
        
        WITH f, row
        MERGE (e:Environment {id: $env_id})
        MERGE (f)-[rel:BELONGS_TO]->(e)
        SET rel.loaded_at = datetime()
        
        WITH f, row
        MERGE (m:Metric {id: row.metric_id})
        MERGE (m)-[:USES_FACT]->(f)
        """
        
        batch = []
        total = 0
        
        for report in reports:
            for dataset in report.get("datasets", []):
                for metric in dataset.get("metricas", []):
                    fact = metric.get("fact")
                    if fact and metric.get("tipo") == "simples":
                        batch.append({
                            "id": fact.get("id"),
                            "name": fact.get("name"),
                            "file_path": fact.get("file_path"),
                            "applicationObject": fact.get("applicationObject"),
                            "metric_id": metric.get("id")
                        })
                        
                        if len(batch) >= self.batch_size:
                            count = self._execute_batch(query, batch, "Facts")
                            total += count
                            self.stats["facts"] += count
                            batch = []
        
        if batch:
            count = self._execute_batch(query, batch, "Facts")
            total += count
            self.stats["facts"] += count
        
        print(f"  ✓ Loaded {total} facts")
        return total
    
    def load_fact_tables(self, reports: List[Dict]) -> int:
        """Load Tables from Facts and READS_FROM relationships."""
        print(f"\n🗄️  Loading Tables (from Facts)...")
        
        query = """
        UNWIND $batch as row
        MERGE (t:Table {id: row.table_id})
        ON CREATE SET t.created_at = datetime()
        SET t.name = row.table_name,
            t.file_path = row.file_path,
            t.updated_at = datetime()
        
        WITH t, row
        MERGE (e:Environment {id: $env_id})
        MERGE (t)-[rel:BELONGS_TO]->(e)
        SET rel.loaded_at = datetime()
        
        WITH t, row
        MERGE (f:Fact {id: row.fact_id})
        MERGE (f)-[rf:READS_FROM]->(t)
        SET rf.column_name = row.column_name
        """
        
        batch = []
        total = 0
        
        for report in reports:
            for dataset in report.get("datasets", []):
                for metric in dataset.get("metricas", []):
                    fact = metric.get("fact")
                    if fact and metric.get("tipo") == "simples":
                        for table in fact.get("logic_tables", []):
                            batch.append({
                                "fact_id": fact.get("id"),
                                "table_id": table.get("id"),
                                "table_name": table.get("name"),
                                "file_path": table.get("file_path"),
                                "column_name": table.get("column_name")
                            })
                            
                            if len(batch) >= self.batch_size:
                                count = self._execute_batch(query, batch, "Tables (from Facts)")
                                total += count
                                batch = []
        
        if batch:
            count = self._execute_batch(query, batch, "Tables (from Facts)")
            total += count
        
        print(f"  ✓ Loaded {total} table references (from facts)")
        return total
    
    def load_composite_metrics(self, reports: List[Dict]) -> int:
        """Load COMPOSED_OF relationships for composite metrics."""
        print(f"\n🔗 Loading Composite Metric Relationships...")
        
        query = """
        UNWIND $batch as row
        MERGE (parent:Metric {id: row.parent_id})
        MERGE (child:Metric {id: row.child_id})
        MERGE (parent)-[:COMPOSED_OF]->(child)
        """
        
        batch = []
        total = 0
        
        for report in reports:
            for dataset in report.get("datasets", []):
                for metric in dataset.get("metricas", []):
                    if metric.get("tipo") == "composto":
                        parent_id = metric.get("id")
                        for child_metric in metric.get("metricas", []):
                            batch.append({
                                "parent_id": parent_id,
                                "child_id": child_metric.get("id")
                            })
                            
                            if len(batch) >= self.batch_size:
                                count = self._execute_batch(query, batch, "Composite Metrics")
                                total += count
                                self.stats["composite_relationships"] += count
                                batch = []
        
        if batch:
            count = self._execute_batch(query, batch, "Composite Metrics")
            total += count
            self.stats["composite_relationships"] += count
        
        print(f"  ✓ Loaded {total} composite metric relationships")
        return total
    
    def load_users(self, reports: List[Dict]) -> int:
        """Load User nodes and their access relationships to Reports."""
        print(f"\n👤 Loading Users...")
        
        # Query to load User node
        user_query = """
        UNWIND $batch as row
        MERGE (u:User {name: row.name})
        ON CREATE SET u.created_at = datetime()
        SET u.id = row.id,
            u.fullname = row.fullname,
            u.file_path = row.file_path,
            u.updated_at = datetime()
        
        WITH u, row
        MERGE (e:Environment {id: $env_id})
        MERGE (u)-[rel:BELONGS_TO]->(e)
        SET rel.loaded_at = datetime()
        """
        
        # Query to load relationships with dynamic relationship type
        relationship_query = """
        UNWIND $batch as row
        MATCH (u:User {name: row.user_name})
        MATCH (r:Report {id: row.report_id})
        CALL apoc.merge.relationship(u, row.access_type, {}, {loaded_at: datetime()}, r, {}) YIELD rel
        RETURN rel
        """
        
        # Fallback query if APOC is not available
        relationship_query_fallback = """
        UNWIND $batch as row
        MATCH (u:User {name: row.user_name})
        MATCH (r:Report {id: row.report_id})
        WITH u, r, row
        CALL {
            WITH u, r, row
            WITH u, r, row.access_type as relType
            CALL apoc.create.relationship(u, relType, {loaded_at: datetime()}, r) YIELD rel
            RETURN rel
        }
        RETURN rel
        """
        
        user_batch = []
        relationship_batch = []
        total_users = 0
        total_relationships = 0
        users_seen = set()
        
        for report in reports:
            report_id = report.get("id")
            
            # Process owner
            owner = report.get("owner")
            if owner:
                user_name = owner.get("name")
                if user_name and user_name not in users_seen:
                    user_batch.append({
                        "name": user_name,
                        "id": owner.get("id"),
                        "fullname": owner.get("fullname"),
                        "file_path": owner.get("file_path")
                    })
                    users_seen.add(user_name)
                    
                    if len(user_batch) >= self.batch_size:
                        count = self._execute_batch(user_query, user_batch, "Users")
                        total_users += count
                        self.stats["users"] += count
                        user_batch = []
                
                # Create owner relationship
                if user_name:
                    access_type = owner.get("access", "owner").upper().replace(" ", "_")
                    relationship_batch.append({
                        "user_name": user_name,
                        "report_id": report_id,
                        "access_type": access_type
                    })
            
            # Process access_control
            for access_entry in report.get("access_control", []):
                user_name = access_entry.get("name")
                if user_name and user_name not in users_seen:
                    user_batch.append({
                        "name": user_name,
                        "id": access_entry.get("id"),
                        "fullname": access_entry.get("fullname"),
                        "file_path": access_entry.get("file_path")
                    })
                    users_seen.add(user_name)
                    
                    if len(user_batch) >= self.batch_size:
                        count = self._execute_batch(user_query, user_batch, "Users")
                        total_users += count
                        self.stats["users"] += count
                        user_batch = []
                
                # Create access relationship
                if user_name:
                    access_type = access_entry.get("access", "").upper().replace(" ", "_")
                    if access_type:
                        relationship_batch.append({
                            "user_name": user_name,
                            "report_id": report_id,
                            "access_type": access_type
                        })
        
        # Process remaining user batches
        if user_batch:
            count = self._execute_batch(user_query, user_batch, "Users")
            total_users += count
            self.stats["users"] += count
        
        # Process relationships
        # Try to use dynamic relationship creation
        if relationship_batch:
            if self.dry_run:
                print(f"  [DRY RUN] Would create {len(relationship_batch)} user-report relationships")
                total_relationships = len(relationship_batch)
                self.stats["user_relationships"] += total_relationships
            else:
                # Process relationships one by one with dynamic type
                print(f"  Creating {len(relationship_batch)} user-report access relationships...")
                for rel_data in relationship_batch:
                    query = f"""
                    MATCH (u:User {{name: $user_name}})
                    MATCH (r:Report {{id: $report_id}})
                    MERGE (u)-[rel:{rel_data['access_type']}]->(r)
                    SET rel.loaded_at = datetime()
                    """
                    try:
                        with self.driver.session(database=self.database) as session:
                            session.run(query, {
                                "user_name": rel_data["user_name"],
                                "report_id": rel_data["report_id"]
                            })
                        total_relationships += 1
                        self.stats["user_relationships"] += 1
                    except Exception as e:
                        self.errors.append(f"User relationship ({rel_data['access_type']}): {e}")
                        print(f"  ✗ Error creating relationship: {e}")
        
        print(f"  ✓ Loaded {total_users} users and {total_relationships} access relationships")
        return total_users
    
    def delete_by_environment(self) -> bool:
        """Delete all data associated with an environment."""
        print(f"\n🗑️  Deleting data for Environment: {self.environment_name} ({self.environment_id})")
        
        if self.dry_run:
            print("  [DRY RUN] Would delete all nodes and relationships for this environment")
            return True
        
        # Count nodes before deletion
        print("\n  Counting nodes to delete...")
        try:
            with self.driver.session(database=self.database) as session:
                # Count all nodes belonging to this environment
                result = session.run("""
                    MATCH (n)-[:BELONGS_TO]->(e:Environment {id: $env_id})
                    RETURN labels(n)[0] as label, count(n) as count
                    ORDER BY count DESC
                """, {"env_id": self.environment_id})
                
                total_nodes = 0
                print("  Nodes to delete:")
                for record in result:
                    count = record["count"]
                    total_nodes += count
                    print(f"    {record['label']}: {count}")
                
                if total_nodes == 0:
                    print(f"  ℹ️  No data found for environment: {self.environment_id}")
                    return True
                
                # Delete all nodes and their relationships
                print(f"\n  Deleting {total_nodes} nodes and their relationships...")
                session.run("""
                    MATCH (n)-[:BELONGS_TO]->(e:Environment {id: $env_id})
                    DETACH DELETE n
                """, {"env_id": self.environment_id})
                
                # Delete the environment node if it has no more relationships
                session.run("""
                    MATCH (e:Environment {id: $env_id})
                    WHERE NOT (e)<-[:BELONGS_TO]-()
                    DELETE e
                """, {"env_id": self.environment_id})
                
                print(f"  ✓ Successfully deleted all data for environment: {self.environment_id}")
                return True
                
        except Exception as e:
            print(f"  ✗ Error deleting data: {e}")
            return False
    
    def delete_by_report(self, report_id: str) -> bool:
        """Delete a specific report and all its related data."""
        print(f"\n🗑️  Deleting Report: {report_id}")
        
        if self.dry_run:
            print("  [DRY RUN] Would delete report and all related nodes")
            return True
        
        # Count nodes before deletion
        print("\n  Counting nodes to delete...")
        try:
            with self.driver.session(database=self.database) as session:
                # Count all nodes related to this report
                result = session.run("""
                    MATCH (r:Report {id: $report_id})
                    OPTIONAL MATCH (r)-[*]->(n)
                    WHERE NOT n:Environment
                    RETURN labels(n)[0] as label, count(DISTINCT n) as count
                    ORDER BY count DESC
                """, {"report_id": report_id})
                
                total_nodes = 0
                print("  Related nodes to delete:")
                for record in result:
                    if record["label"]:
                        count = record["count"]
                        total_nodes += count
                        print(f"    {record['label']}: {count}")
                
                # Check if report exists
                result = session.run("""
                    MATCH (r:Report {id: $report_id})
                    RETURN count(r) as count
                """, {"report_id": report_id})
                
                report_count = result.single()["count"]
                if report_count == 0:
                    print(f"  ℹ️  Report not found: {report_id}")
                    return True
                
                # Delete report and all related nodes
                print(f"\n  Deleting report and {total_nodes} related nodes...")
                
                # Delete in order: from leaf nodes to report
                # 1. Delete tables used by forms and facts
                session.run("""
                    MATCH (r:Report {id: $report_id})-[:CONTAINS]->(d:Dataset)
                    OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FORM]->(f:Form)-[:USES_TABLE]->(t:Table)
                    OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:Metric)-[:USES_FACT]->(fact:Fact)-[:READS_FROM]->(t2:Table)
                    WITH collect(DISTINCT t) + collect(DISTINCT t2) as tables
                    UNWIND tables as table
                    DETACH DELETE table
                """, {"report_id": report_id})
                
                # 2. Delete forms
                session.run("""
                    MATCH (r:Report {id: $report_id})-[:CONTAINS]->(d:Dataset)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FORM]->(f:Form)
                    DETACH DELETE f
                """, {"report_id": report_id})
                
                # 3. Delete facts and functions
                session.run("""
                    MATCH (r:Report {id: $report_id})-[:CONTAINS]->(d:Dataset)-[:HAS_METRIC]->(m:Metric)
                    OPTIONAL MATCH (m)-[:USES_FACT]->(fact:Fact)
                    OPTIONAL MATCH (m)-[:USES_FUNCTION]->(func:Function)
                    DETACH DELETE fact, func
                """, {"report_id": report_id})
                
                # 4. Delete metrics and attributes
                session.run("""
                    MATCH (r:Report {id: $report_id})-[:CONTAINS]->(d:Dataset)
                    OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:Metric)
                    OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(a:Attribute)
                    DETACH DELETE m, a
                """, {"report_id": report_id})
                
                # 5. Delete datasets
                session.run("""
                    MATCH (r:Report {id: $report_id})-[:CONTAINS]->(d:Dataset)
                    DETACH DELETE d
                """, {"report_id": report_id})
                
                # 6. Delete user relationships to this report
                session.run("""
                    MATCH (u:User)-[rel]->(r:Report {id: $report_id})
                    WHERE type(rel) <> 'BELONGS_TO'
                    DELETE rel
                """, {"report_id": report_id})
                
                # 7. Finally delete the report
                session.run("""
                    MATCH (r:Report {id: $report_id})
                    DETACH DELETE r
                """, {"report_id": report_id})
                
                print(f"  ✓ Successfully deleted report: {report_id}")
                return True
                
        except Exception as e:
            print(f"  ✗ Error deleting report: {e}")
            return False
    
    def load_data(self, json_file: Path, entities: List[str]) -> bool:
        """
        Load data from JSON file.
        
        Args:
            json_file: Path to JSON file
            entities: List of entities to load (or ['all'])
            
        Returns:
            bool: True if successful
        """
        print("=" * 70)
        print("Neo4j Data Loading")
        print("=" * 70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Environment: {self.environment_name} ({self.environment_id})")
        print(f"JSON File: {json_file}")
        print(f"Entities: {', '.join(entities)}")
        print(f"Batch Size: {self.batch_size}")
        if self.dry_run:
            print("⚠️  DRY RUN MODE - No data will be written")
        print("=" * 70)
        
        # Load JSON data
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            reports = data.get("relatorios", [])
            print(f"\n✓ Loaded JSON file with {len(reports)} reports")
        except Exception as e:
            print(f"✗ Error loading JSON file: {e}")
            return False
        
        # Connect to Neo4j
        if not self.connect():
            return False
        
        try:
            # Create environment
            if not self.create_environment():
                return False
            
            # Load entities based on filter
            load_all = "all" in entities
            
            if load_all or "reports" in entities:
                self.load_reports(reports)
            
            if load_all or "datasets" in entities:
                self.load_datasets(reports)
            
            if load_all or "attributes" in entities:
                self.load_attributes(reports)
                self.load_forms_and_tables(reports)
            
            if load_all or "metrics" in entities:
                self.load_metrics(reports)
                self.load_functions(reports)
                self.load_facts(reports)
                self.load_fact_tables(reports)
                self.load_composite_metrics(reports)
            
            if load_all or "users" in entities:
                self.load_users(reports)
            
            # Display statistics
            self._display_statistics()
            
            print("\n" + "=" * 70)
            if self.dry_run:
                print("✓ Dry run complete - no data was written")
            else:
                print("✓ Data loading complete!")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error during data loading: {e}")
            return False
        finally:
            self.close()
    
    def _display_statistics(self):
        """Display loading statistics."""
        print("\n" + "=" * 70)
        print("📊 Loading Statistics")
        print("=" * 70)
        print("\n🔄 Records Processed in This Batch:")
        
        for key, value in sorted(self.stats.items()):
            print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Show actual unique node counts in database
        if not self.dry_run:
            print("\n💾 Total Unique Nodes in Database:")
            try:
                with self.driver.session(database=self.database) as session:
                    labels = ["Report", "Dataset", "Attribute", "Metric", "Fact", 
                             "Function", "Table", "Form", "User"]
                    
                    for label in labels:
                        result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                        count = result.single()["count"]
                        print(f"  {label}: {count}")
                    
                    # Show user access relationship counts
                    if self.stats.get("user_relationships", 0) > 0:
                        print("\n🔐 User Access Relationships by Type:")
                        result = session.run("""
                            MATCH (u:User)-[r]->(rep:Report)
                            WHERE type(r) <> 'BELONGS_TO'
                            RETURN type(r) as access_type, count(r) as count
                            ORDER BY count DESC
                        """)
                        for record in result:
                            print(f"  {record['access_type']}: {record['count']}")
                    
                    # Check for duplicates
                    print("\n🔍 Data Integrity Check:")
                    has_duplicates = False
                    
                    for label in ["Report", "Dataset", "Attribute", "Metric", "Fact", "Table"]:
                        result = session.run(f"""
                            MATCH (n:{label})
                            WITH n.id as id, count(*) as cnt
                            WHERE cnt > 1
                            RETURN count(*) as duplicates
                        """)
                        dup_count = result.single()["duplicates"]
                        if dup_count > 0:
                            print(f"  ⚠️  {label}: {dup_count} duplicate IDs found!")
                            has_duplicates = True
                    
                    if not has_duplicates:
                        print(f"  ✓ No duplicates found - MERGE working correctly")
                        
            except Exception as e:
                print(f"  ✗ Error getting node counts: {e}")
        
        if self.errors:
            print(f"\n⚠️  Errors: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more errors")


def load_config_from_env() -> Dict[str, str]:
    """Load Neo4j configuration from environment variables."""
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
        description="Load MicroStrategy data into Neo4j graph database"
    )
    parser.add_argument(
        "--json-file",
        type=Path,
        help="Path to JSON file (e.g., output.json)"
    )
    parser.add_argument(
        "--environment-id",
        required=True,
        help="Environment ID (e.g., prod-2024, dev-latest)"
    )
    parser.add_argument(
        "--environment-name",
        help="Environment name (e.g., 'Production', 'Development')"
    )
    parser.add_argument(
        "--delete-environment",
        action="store_true",
        help="Delete all data for the specified environment-id"
    )
    parser.add_argument(
        "--delete-report",
        help="Delete a specific report by report-id"
    )
    parser.add_argument(
        "--entities",
        default="all",
        help="Comma-separated list of entities to load: all, reports, datasets, attributes, metrics, facts, tables, users (default: all)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for bulk operations (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be loaded without executing"
    )
    parser.add_argument(
        "--uri",
        help="Neo4j connection URI (default: from NEO4J_URI env)"
    )
    parser.add_argument(
        "--user",
        help="Neo4j username (default: from NEO4J_USER env)"
    )
    parser.add_argument(
        "--password",
        help="Neo4j password (default: from NEO4J_PASSWORD env)"
    )
    parser.add_argument(
        "--database",
        help="Neo4j database name (default: from NEO4J_DATABASE env)"
    )
    
    args = parser.parse_args()
    
    # Check if this is a delete operation
    is_delete_operation = args.delete_environment or args.delete_report
    
    # Validate arguments based on operation type
    if not is_delete_operation:
        # Loading data requires json-file and environment-name
        if not args.json_file:
            print("✗ Error: --json-file is required for loading data")
            sys.exit(1)
        if not args.environment_name:
            print("✗ Error: --environment-name is required for loading data")
            sys.exit(1)
        if not args.json_file.exists():
            print(f"✗ Error: JSON file not found: {args.json_file}")
            sys.exit(1)
    else:
        # Delete operations only require environment-id (and optionally environment-name for display)
        if not args.environment_name:
            args.environment_name = args.environment_id
    
    # Parse entities (only needed for loading)
    if not is_delete_operation:
        entities = [e.strip().lower() for e in args.entities.split(",")]
        valid_entities = {"all", "reports", "datasets", "attributes", "metrics", "facts", "tables", "users"}
        invalid = set(entities) - valid_entities
        if invalid:
            print(f"✗ Error: Invalid entities: {', '.join(invalid)}")
            print(f"Valid entities: {', '.join(valid_entities)}")
            sys.exit(1)
    else:
        entities = []
    
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
    
    # Create loader
    loader = Neo4jDataLoader(
        uri=config["uri"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        environment_id=args.environment_id,
        environment_name=args.environment_name,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    # Execute operation based on arguments
    if args.delete_environment:
        # Delete all data for the environment
        print("=" * 70)
        print("Neo4j Data Deletion - By Environment")
        print("=" * 70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Environment: {args.environment_name} ({args.environment_id})")
        if args.dry_run:
            print("⚠️  DRY RUN MODE - No data will be deleted")
        print("=" * 70)
        
        if not loader.connect():
            sys.exit(1)
        
        try:
            success = loader.delete_by_environment()
        finally:
            loader.close()
        
        sys.exit(0 if success else 1)
        
    elif args.delete_report:
        # Delete specific report
        print("=" * 70)
        print("Neo4j Data Deletion - By Report")
        print("=" * 70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Report ID: {args.delete_report}")
        if args.dry_run:
            print("⚠️  DRY RUN MODE - No data will be deleted")
        print("=" * 70)
        
        if not loader.connect():
            sys.exit(1)
        
        try:
            success = loader.delete_by_report(args.delete_report)
        finally:
            loader.close()
        
        sys.exit(0 if success else 1)
        
    else:
        # Load data
        success = loader.load_data(args.json_file, entities)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

