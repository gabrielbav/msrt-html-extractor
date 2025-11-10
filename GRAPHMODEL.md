# Neo4j Graph Model Documentation

## Overview

This document describes the Neo4j graph database schema for storing MicroStrategy data model information. The graph model represents the hierarchical relationships between Reports, Datasets, Attributes, Metrics, Facts, Functions, and Tables, along with environment tracking for data versioning.

---

## Node Labels and Properties

### 1. Environment

Represents the environment/context in which data was loaded (e.g., "Production", "Development", "UAT").

**Properties:**
- `id` (String, Required, Unique): Environment unique identifier
- `name` (String, Required): Environment name
- `created_at` (DateTime): Timestamp when environment was created
- `updated_at` (DateTime): Timestamp when environment was last updated

### 2. Report

Represents a MicroStrategy report object.

**Properties:**
- `id` (String, Required, Unique): Report unique identifier (32-char hex)
- `name` (String, Required): Report name
- `file_path` (String): Reference to HTML file

### 3. Dataset

Represents a MicroStrategy dataset (Intelligent Cube, Report, or Shortcut).

**Properties:**
- `id` (String, Required, Unique): Dataset unique identifier (32-char hex)
- `name` (String, Required): Dataset name
- `file_path` (String): Reference to HTML file
- `applicationObject` (String, Nullable): Object type ("CuboInteligente", "Report", "Atalho")
- `graphic` (String, Nullable): Chart/graphic type

### 4. Attribute

Represents a MicroStrategy attribute.

**Properties:**
- `id` (String, Required, Unique): Attribute unique identifier (32-char hex)
- `name` (String, Required): Attribute name
- `name_on_dataset` (String): Display name on dataset (may differ from name)
- `file_path` (String): Reference to HTML file
- `applicationSchema` (String): Schema classification ("Atributo")

### 5. Form

Represents an attribute form (ID, Description, Name, etc.).

**Properties:**
- `name` (String, Required): Form name (e.g., "ID", "DESC", "Name")

**Note:** Forms do not have a unique `id` field. They are identified by their name within the context of their parent Attribute.

### 6. Metric

Represents a MicroStrategy metric (simple or composite).

**Properties:**
- `id` (String, Required, Unique): Metric unique identifier (32-char hex)
- `name` (String, Required): Metric name
- `file_path` (String): Reference to HTML file
- `applicationObject` (String): Object type ("Metrica")
- `tipo` (String, Required): Metric type ("simples" or "composto")
- `formula` (String, Nullable): Metric formula expression

**Business Rules:**
- Simple metrics (`tipo: "simples"`): Have relationships to Function and Fact
- Composite metrics (`tipo: "composto"`): Have relationships to other Metrics via `COMPOSED_OF`

### 7. Function

Represents an aggregation function (Sum, Avg, Count, etc.).

**Properties:**
- `name` (String, Required): Function name
- `file_path` (String, Required): Reference to HTML file

**Note:** Functions do not have a unique `id` field. They are uniquely identified by the composite key (`name`, `file_path`).

### 8. Fact

Represents a MicroStrategy fact.

**Properties:**
- `id` (String, Required, Unique): Fact unique identifier (32-char hex)
- `name` (String, Required): Fact name
- `file_path` (String): Reference to HTML file
- `applicationObject` (String): Object type ("Fato")

### 9. Table

Represents a logical database table.

**Properties:**
- `id` (String, Required, Unique): Table unique identifier (32-char hex)
- `name` (String, Required): Table name
- `file_path` (String): Reference to HTML file

---

## Relationships

### Core Relationships (From Original Model)

| Relationship | Source | Target | Properties | Cardinality | Description |
|--------------|--------|--------|------------|-------------|-------------|
| `CONTAINS` | Report | Dataset | - | 1:N | Report contains one or more datasets |
| `HAS_ATTRIBUTE` | Dataset | Attribute | - | 1:N | Dataset includes attributes |
| `HAS_METRIC` | Dataset | Metric | - | 1:N | Dataset includes metrics |
| `HAS_FORM` | Attribute | Form | - | 1:N | Attribute has multiple forms |
| `USES_TABLE` | Form | Table | `column_name` (String) | 1:N | Form reads from table column |
| `USES_FUNCTION` | Metric | Function | - | 0..1 | Simple metric uses aggregation function |
| `USES_FACT` | Metric | Fact | - | 0..1 | Simple metric aggregates a fact |
| `COMPOSED_OF` | Metric | Metric | - | 0..N | Composite metric references child metrics (recursive) |
| `READS_FROM` | Fact | Table | `column_name` (String) | 1:N | Fact reads from table column |

### Environment Tracking Relationship (New)

| Relationship | Source | Target | Properties | Cardinality | Description |
|--------------|--------|--------|------------|-------------|-------------|
| `BELONGS_TO` | All Nodes* | Environment | `loaded_at` (DateTime) | N:1 | Links data to its source environment |

**All Nodes:** Report, Dataset, Attribute, Form, Metric, Function, Fact, Table

---

## Constraints

### Unique Constraints (Prevent Duplicates)

```cypher
CREATE CONSTRAINT report_id_unique IF NOT EXISTS
FOR (r:Report) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT dataset_id_unique IF NOT EXISTS
FOR (d:Dataset) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT attribute_id_unique IF NOT EXISTS
FOR (a:Attribute) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT metric_id_unique IF NOT EXISTS
FOR (m:Metric) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT fact_id_unique IF NOT EXISTS
FOR (f:Fact) REQUIRE f.id IS UNIQUE;

CREATE CONSTRAINT table_id_unique IF NOT EXISTS
FOR (t:Table) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT environment_id_unique IF NOT EXISTS
FOR (e:Environment) REQUIRE e.id IS UNIQUE;

-- Composite key for Function (no single ID field)
CREATE CONSTRAINT function_composite_unique IF NOT EXISTS
FOR (f:Function) REQUIRE (f.name, f.file_path) IS UNIQUE;
```

---

## Indexes

### Performance Indexes

```cypher
-- Name-based lookups
CREATE INDEX report_name_index IF NOT EXISTS
FOR (r:Report) ON (r.name);

CREATE INDEX dataset_name_index IF NOT EXISTS
FOR (d:Dataset) ON (d.name);

CREATE INDEX attribute_name_index IF NOT EXISTS
FOR (a:Attribute) ON (a.name);

CREATE INDEX metric_name_index IF NOT EXISTS
FOR (m:Metric) ON (m.name);

CREATE INDEX fact_name_index IF NOT EXISTS
FOR (f:Fact) ON (f.name);

CREATE INDEX table_name_index IF NOT EXISTS
FOR (t:Table) ON (t.name);

CREATE INDEX environment_name_index IF NOT EXISTS
FOR (e:Environment) ON (e.name);

-- Type filtering
CREATE INDEX metric_tipo_index IF NOT EXISTS
FOR (m:Metric) ON (m.tipo);

CREATE INDEX dataset_application_object_index IF NOT EXISTS
FOR (d:Dataset) ON (d.applicationObject);
```

---

## Cypher Query Examples

### 1. Find All Data for a Specific Environment

```cypher
// Get all nodes belonging to an environment
MATCH (n)-[:BELONGS_TO]->(e:Environment {name: 'Production'})
RETURN labels(n) as NodeType, count(n) as Count
ORDER BY Count DESC;

// Get detailed data for a specific environment
MATCH (r:Report)-[:BELONGS_TO]->(e:Environment {id: 'env-prod-001'})
OPTIONAL MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:Metric)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(a:Attribute)
RETURN r.name as Report, 
       collect(DISTINCT d.name) as Datasets,
       collect(DISTINCT m.name) as Metrics,
       collect(DISTINCT a.name) as Attributes;
```

### 2. Find Reports Using a Specific Table

```cypher
// Find reports that use a specific table through attributes
MATCH (r:Report)-[:CONTAINS]->(d:Dataset)-[:HAS_ATTRIBUTE]->(a:Attribute)
      -[:HAS_FORM]->(f:Form)-[:USES_TABLE]->(t:Table {name: 'FT_SALES'})
RETURN DISTINCT r.name as Report, r.id as ReportID;

// Find reports that use a specific table through facts
MATCH (r:Report)-[:CONTAINS]->(d:Dataset)-[:HAS_METRIC]->(m:Metric)
      -[:USES_FACT]->(fact:Fact)-[:READS_FROM]->(t:Table {name: 'FT_SALES'})
RETURN DISTINCT r.name as Report, r.id as ReportID;
```

### 3. Find Metric Lineage (Composite Metrics Breakdown)

```cypher
// Recursive query to find all component metrics
MATCH path = (m:Metric {name: 'ROI %'})-[:COMPOSED_OF*]->(component:Metric)
RETURN m.name as CompositeMetric,
       component.name as ComponentMetric,
       component.tipo as MetricType,
       component.formula as Formula,
       length(path) as Depth
ORDER BY Depth;

// Get full metric tree with functions and facts
MATCH (m:Metric {name: 'Net Profit'})
CALL apoc.path.subgraphAll(m, {
    relationshipFilter: 'COMPOSED_OF>|USES_FUNCTION>|USES_FACT>',
    maxLevel: 10
})
YIELD nodes, relationships
RETURN nodes, relationships;
```

### 4. Find All Attributes Sourced from a Table

```cypher
MATCH (t:Table {name: 'DIM_CUSTOMER'})<-[:USES_TABLE]-(f:Form)
      <-[:HAS_FORM]-(a:Attribute)
RETURN a.name as Attribute,
       f.name as Form,
       t.name as Table,
       [(f)-[ut:USES_TABLE]->(t) | ut.column_name][0] as ColumnName;
```

### 5. Delete Data from a Specific Environment

```cypher
// Delete all data associated with an environment
MATCH (n)-[r:BELONGS_TO]->(e:Environment {id: 'env-dev-001'})
DETACH DELETE n;

// Then delete the environment itself
MATCH (e:Environment {id: 'env-dev-001'})
DELETE e;

// OR: Delete everything in one query (use with caution!)
MATCH (e:Environment {id: 'env-dev-001'})
OPTIONAL MATCH (n)-[:BELONGS_TO]->(e)
DETACH DELETE e, n;
```

### 6. Find Duplicate Data Across Environments

```cypher
// Find reports that exist in multiple environments
MATCH (r:Report)-[:BELONGS_TO]->(e:Environment)
WITH r.id as ReportID, r.name as ReportName, collect(e.name) as Environments
WHERE size(Environments) > 1
RETURN ReportID, ReportName, Environments
ORDER BY ReportName;

// Find metrics with different formulas across environments
MATCH (m1:Metric)-[:BELONGS_TO]->(e1:Environment),
      (m2:Metric)-[:BELONGS_TO]->(e2:Environment)
WHERE m1.id = m2.id 
  AND m1.formula <> m2.formula
  AND e1.name < e2.name
RETURN m1.id as MetricID,
       m1.name as MetricName,
       e1.name as Environment1,
       m1.formula as Formula1,
       e2.name as Environment2,
       m2.formula as Formula2;
```

### 7. Get Environment Statistics

```cypher
MATCH (e:Environment)
OPTIONAL MATCH (r:Report)-[:BELONGS_TO]->(e)
OPTIONAL MATCH (d:Dataset)-[:BELONGS_TO]->(e)
OPTIONAL MATCH (m:Metric)-[:BELONGS_TO]->(e)
OPTIONAL MATCH (a:Attribute)-[:BELONGS_TO]->(e)
OPTIONAL MATCH (t:Table)-[:BELONGS_TO]->(e)
RETURN e.name as Environment,
       e.id as EnvironmentID,
       count(DISTINCT r) as Reports,
       count(DISTINCT d) as Datasets,
       count(DISTINCT m) as Metrics,
       count(DISTINCT a) as Attributes,
       count(DISTINCT t) as Tables,
       e.created_at as CreatedAt,
       e.updated_at as UpdatedAt;
```

### 8. Find Simple vs Composite Metrics

```cypher
// Count metrics by type in an environment
MATCH (m:Metric)-[:BELONGS_TO]->(e:Environment {name: 'Production'})
RETURN m.tipo as MetricType, count(m) as Count;

// Find all composite metrics and their depth
MATCH (m:Metric {tipo: 'composto'})-[:BELONGS_TO]->(e:Environment {name: 'Production'})
OPTIONAL MATCH path = (m)-[:COMPOSED_OF*]->(component:Metric)
WITH m, max(length(path)) as MaxDepth
RETURN m.name as CompositeMetric, 
       COALESCE(MaxDepth, 0) as Depth
ORDER BY Depth DESC;
```

### 9. Find All Tables Used by a Report

```cypher
// Get all tables (through both attributes and metrics)
MATCH (r:Report {name: 'Monthly Sales Analysis'})-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FORM]->(f:Form)
              -[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:Metric)-[:USES_FACT]->(fact:Fact)
              -[:READS_FROM]->(t2:Table)
WITH r, collect(DISTINCT t1) + collect(DISTINCT t2) as AllTables
UNWIND AllTables as t
RETURN DISTINCT t.name as TableName, t.id as TableID
ORDER BY TableName;
```

### 10. Trace Data Lineage from Table to Report

```cypher
// Find all reports using data from a specific table
MATCH path = (t:Table {name: 'FT_SALES'})<-[:USES_TABLE|READS_FROM*1..5]-
             (intermediate)-[*1..5]-(r:Report)
WHERE (t)<-[:USES_TABLE]-(:Form) OR (t)<-[:READS_FROM]-(:Fact)
RETURN DISTINCT r.name as Report,
       [node in nodes(path) | labels(node)[0]] as Path
LIMIT 10;
```

---

## Data Loading Strategy

### MERGE Operations

All node creation uses `MERGE` to ensure idempotency:

1. **For nodes with unique ID:**
   ```cypher
   MERGE (n:NodeLabel {id: $id})
   SET n.property1 = $value1,
       n.property2 = $value2,
       n.updated_at = datetime()
   ```

2. **For Function nodes (composite key):**
   ```cypher
   MERGE (f:Function {name: $name, file_path: $file_path})
   SET f.updated_at = datetime()
   ```

3. **Environment linking:**
   ```cypher
   MERGE (e:Environment {id: $env_id})
   SET e.name = $env_name,
       e.updated_at = datetime()
   
   MERGE (n)-[r:BELONGS_TO]->(e)
   SET r.loaded_at = datetime()
   ```

### Batch Processing

For optimal performance:
- Process nodes in batches of 100-500
- Use `UNWIND` for bulk operations
- Separate transactions for nodes and relationships

---

## Best Practices

### 1. Environment Management

- Always specify environment when loading data
- Use meaningful environment IDs (e.g., `prod-2024-01`, `dev-latest`)
- Track loading timestamps via `loaded_at` relationship property

### 2. Query Performance

- Use indexes for name-based searches
- Limit relationship traversal depth for recursive queries
- Use `EXPLAIN` and `PROFILE` to optimize complex queries

### 3. Data Integrity

- Always use MERGE for data loading (prevents duplicates)
- Validate IDs before deletion operations
- Use transactions for bulk operations

### 4. Maintenance

- Regularly check for orphaned nodes
- Monitor environment statistics
- Archive old environments before deletion

---

## Graph Visualization in Neo4j Bloom

### Suggested Perspectives

1. **Report Lineage:** Focus on Report → Dataset → Attribute/Metric → Table paths
2. **Metric Composition:** Highlight recursive `COMPOSED_OF` relationships
3. **Environment Comparison:** Compare same entities across different environments
4. **Table Impact Analysis:** Show all reports/datasets using specific tables

### Color Coding Recommendations

- **Reports:** Blue
- **Datasets:** Yellow
- **Attributes:** Green
- **Metrics:** Pink (Simple: Light Pink, Composite: Dark Pink)
- **Facts:** Orange
- **Functions:** Light Green
- **Tables:** Purple
- **Environment:** Gray

---

## References

- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)
- [Neo4j Browser Guide](https://neo4j.com/docs/browser-manual/current/)
- [Neo4j Bloom User Guide](https://neo4j.com/docs/bloom-user-guide/current/)

