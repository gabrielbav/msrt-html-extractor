"""Schema loader for database configuration."""

import yaml
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from utils.logger import get_logger
from exceptions import ConfigurationError

logger = get_logger(__name__)


@dataclass
class Column:
    """Database column definition."""
    name: str
    type: str
    primary_key: bool = False
    nullable: bool = True
    description: Optional[str] = None
    foreign_key: Optional[Dict[str, str]] = None


@dataclass
class Table:
    """Database table definition."""
    name: str
    csv_file: str
    description: Optional[str] = None
    columns: List[Column] = field(default_factory=list)
    primary_key: Optional[List[str]] = None


class SchemaLoader:
    """Load and manage database schema configuration."""
    
    def __init__(self, schema_file: Path):
        """
        Initialize schema loader.
        
        Args:
            schema_file: Path to db_schema.yaml
        """
        self.schema_file = Path(schema_file)
        self._schema_data = None
        self._entities: List[Table] = []
        self._relationships: List[Table] = []
        self._import_order: List[str] = []
    
    def load(self) -> None:
        """
        Load schema from YAML file.
        
        Raises:
            ConfigurationError: If schema file is invalid
        """
        if not self.schema_file.exists():
            raise ConfigurationError(
                f"Schema file not found: {self.schema_file}",
                "db_schema_file"
            )
        
        try:
            with open(self.schema_file, 'r', encoding='utf-8') as f:
                self._schema_data = yaml.safe_load(f)
            
            logger.info(f"Loaded schema from {self.schema_file}")
            
            # Parse entities
            self._parse_entities()
            
            # Parse relationships
            self._parse_relationships()
            
            # Get import order
            self._import_order = self._schema_data.get('import_order', [])
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in schema file: {e}", "db_schema_file")
        except Exception as e:
            raise ConfigurationError(f"Failed to load schema: {e}", "db_schema_file")
    
    def _parse_entities(self):
        """Parse entity table definitions."""
        entities_data = self._schema_data.get('entities', [])
        
        for entity_data in entities_data:
            table = self._parse_table(entity_data)
            self._entities.append(table)
    
    def _parse_relationships(self):
        """Parse relationship table definitions."""
        relationships_data = self._schema_data.get('relationships', [])
        
        for rel_data in relationships_data:
            table = self._parse_table(rel_data)
            self._relationships.append(table)
    
    def _parse_table(self, table_data: Dict) -> Table:
        """
        Parse a single table definition.
        
        Args:
            table_data: Table data from YAML
            
        Returns:
            Table object
        """
        columns = []
        columns_data = table_data.get('columns', [])
        
        for col_data in columns_data:
            column = Column(
                name=col_data['name'],
                type=col_data['type'],
                primary_key=col_data.get('primary_key', False),
                nullable=col_data.get('nullable', True),
                description=col_data.get('description'),
                foreign_key=col_data.get('foreign_key')
            )
            columns.append(column)
        
        return Table(
            name=table_data['name'],
            csv_file=table_data['csv_file'],
            description=table_data.get('description'),
            columns=columns,
            primary_key=table_data.get('primary_key')
        )
    
    def get_entities(self) -> List[Table]:
        """Get entity table definitions."""
        return self._entities
    
    def get_relationships(self) -> List[Table]:
        """Get relationship table definitions."""
        return self._relationships
    
    def get_all_tables(self) -> List[Table]:
        """Get all table definitions (entities + relationships)."""
        return self._entities + self._relationships
    
    def get_import_order(self) -> List[str]:
        """Get table names in correct import order."""
        return self._import_order
    
    def get_table(self, table_name: str) -> Optional[Table]:
        """
        Get a specific table definition by name.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Table object or None if not found
        """
        for table in self.get_all_tables():
            if table.name == table_name:
                return table
        return None
    
    def generate_create_sql(self, dialect: str = 'postgresql') -> str:
        """
        Generate CREATE TABLE SQL statements.
        
        Args:
            dialect: SQL dialect (postgresql, mysql, sqlite)
            
        Returns:
            SQL script as string
        """
        sql_parts = []
        
        # Generate entity tables
        for table in self._entities:
            sql_parts.append(self._generate_create_table_sql(table, dialect))
        
        # Generate relationship tables
        for table in self._relationships:
            sql_parts.append(self._generate_create_table_sql(table, dialect))
        
        return '\n\n'.join(sql_parts)
    
    def _generate_create_table_sql(self, table: Table, dialect: str) -> str:
        """Generate CREATE TABLE SQL for a single table."""
        lines = [f"CREATE TABLE {table.name} ("]
        
        # Add columns
        col_definitions = []
        for col in table.columns:
            parts = [f"  {col.name} {col.type}"]
            
            if col.primary_key:
                parts.append("PRIMARY KEY")
            
            if not col.nullable and not col.primary_key:
                parts.append("NOT NULL")
            
            col_definitions.append(' '.join(parts))
        
        # Add composite primary key if specified
        if table.primary_key and len(table.primary_key) > 1:
            pk_cols = ', '.join(table.primary_key)
            col_definitions.append(f"  PRIMARY KEY ({pk_cols})")
        
        lines.append(',\n'.join(col_definitions))
        lines.append(");")
        
        # Add foreign keys as ALTER TABLE (if supported)
        if dialect == 'postgresql':
            for col in table.columns:
                if col.foreign_key:
                    fk_table = col.foreign_key['table']
                    fk_column = col.foreign_key['column']
                    lines.append(f"\nALTER TABLE {table.name}")
                    lines.append(f"  ADD FOREIGN KEY ({col.name}) REFERENCES {fk_table}({fk_column});")
        
        return '\n'.join(lines)
    
    def get_csv_file_mapping(self) -> Dict[str, str]:
        """
        Get mapping of table names to CSV files.
        
        Returns:
            Dict mapping table_name -> csv_file
        """
        mapping = {}
        for table in self.get_all_tables():
            mapping[table.name] = table.csv_file
        return mapping

