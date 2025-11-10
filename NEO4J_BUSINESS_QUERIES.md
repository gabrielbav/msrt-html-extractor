# Neo4j Business Intelligence Queries

This document contains practical Cypher queries to answer real business questions about your MicroStrategy data model using actual data from your environment.

**Environment ID**: `20250519221644`  
**Environment Name**: `04 - Relatórios Gerenciais - BARE (20250519221644)`

---

## 📊 Table of Contents

1. [Impact Analysis](#1-impact-analysis)
2. [Column Change Analysis](#2-column-change-analysis)
3. [Unused Resources](#3-unused-resources)
4. [Shared Resources](#4-shared-resources)
5. [Metric Lineage](#5-metric-lineage)
6. [Migration Planning](#6-migration-planning)
7. [Dependency Analysis](#7-dependency-analysis)

---

## 1. Impact Analysis

### Q: If I change table X, what reports will be affected?

**Example: Change table `trans_TB_MD3_OBJETOS`**

```cypher
// Find all reports that use trans_TB_MD3_OBJETOS
MATCH (t:Table {name: 'trans_TB_MD3_OBJETOS'})-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (t)<-[:USES_TABLE]-(f:Form)<-[:HAS_FORM]-(a:Attribute)
      <-[:HAS_ATTRIBUTE]-(d:Dataset)<-[:CONTAINS]-(r:Report)
RETURN DISTINCT 
    r.name as Report,
    r.id as ReportID,
    count(DISTINCT d) as AffectedDatasets,
    count(DISTINCT a) as AffectedAttributes
ORDER BY AffectedAttributes DESC;
```

**Alternative path through Facts:**

```cypher
// Reports using trans_TB_MD3_OBJETOS via metrics/facts
MATCH (t:Table {name: 'trans_TB_MD3_OBJETOS'})-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (t)<-[:READS_FROM]-(fact:Fact)<-[:USES_FACT]-(m:Metric)
      <-[:HAS_METRIC]-(d:Dataset)<-[:CONTAINS]-(r:Report)
RETURN DISTINCT 
    r.name as Report,
    r.id as ReportID,
    count(DISTINCT m) as AffectedMetrics,
    count(DISTINCT d) as AffectedDatasets
ORDER BY AffectedMetrics DESC;
```

**Complete impact (both paths):**

```cypher
// All reports affected by table trans_TB_MD3_OBJETOS
MATCH (t:Table {name: 'trans_TB_MD3_OBJETOS'})-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
OPTIONAL MATCH path1 = (t)<-[:USES_TABLE]-(f:Form)<-[:HAS_FORM]-(a:Attribute)
                       <-[:HAS_ATTRIBUTE]-(d1:Dataset)<-[:CONTAINS]-(r1:Report)
OPTIONAL MATCH path2 = (t)<-[:READS_FROM]-(fact:Fact)<-[:USES_FACT]-(m:Metric)
                       <-[:HAS_METRIC]-(d2:Dataset)<-[:CONTAINS]-(r2:Report)
WITH t, collect(DISTINCT r1) + collect(DISTINCT r2) as AllReports
UNWIND AllReports as r
RETURN DISTINCT r.name as Report, r.id as ReportID
ORDER BY Report;
```

---

## 2. Column Change Analysis

### Q: If I change column name `ID_DW`, what metrics will break?

**Find all attributes using the column:**

```cypher
// Attributes using column ID_DW
MATCH (t:Table)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (t)<-[ut:USES_TABLE]-(f:Form)<-[:HAS_FORM]-(a:Attribute)
WHERE ut.column_name = 'ID_DW'
RETURN DISTINCT 
    t.name as Table,
    a.name as Attribute,
    f.name as Form,
    ut.column_name as ColumnName,
    count(DISTINCT t) as TableCount
ORDER BY Table, Attribute;
```

**Find metrics using the column:**

```cypher
// Metrics using column ID_DW (via facts)
MATCH (t:Table)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (t)<-[rf:READS_FROM]-(fact:Fact)<-[:USES_FACT]-(m:Metric)
WHERE rf.column_name = 'ID_DW'
RETURN DISTINCT 
    t.name as Table,
    m.name as Metric,
    m.formula as Formula,
    fact.name as Fact,
    rf.column_name as ColumnName
ORDER BY Table, Metric;
```

**Complete impact on reports:**

```cypher
// Reports affected by column ID_DW change
MATCH (t:Table)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (t)<-[rel]-(entity)
WHERE (rel.column_name = 'ID_DW')
MATCH (entity)-[*1..4]-(r:Report)
RETURN DISTINCT 
    t.name as Table,
    rel.column_name as Column,
    r.name as AffectedReport
ORDER BY Table, AffectedReport;
```

---

## 3. Unused Resources

### Q: What tables are no longer used by any active report?

```cypher
// Unused tables (not connected to any report)
MATCH (t:Table)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
WHERE NOT EXISTS {
    MATCH (t)<-[:USES_TABLE|READS_FROM]-()-[*1..5]-(r:Report)
    WHERE (r)-[:BELONGS_TO]->(e)
}
RETURN t.name as UnusedTable, t.id as TableID
ORDER BY UnusedTable
LIMIT 50;
```

**Unused metrics:**

```cypher
// Metrics not used in any dataset
MATCH (m:Metric)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
WHERE NOT EXISTS {
    MATCH (m)<-[:HAS_METRIC]-(d:Dataset)
}
RETURN m.name as UnusedMetric, m.tipo as Type, m.formula as Formula
ORDER BY UnusedMetric
LIMIT 50;
```

---

## 4. Shared Resources

### Q: Which datasets or tables are shared by multiple reports?

**Most shared datasets:**

```cypher
// Datasets shared by multiple reports
MATCH (d:Dataset)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (d)<-[:CONTAINS]-(r:Report)
WITH d, count(DISTINCT r) as ReportCount, collect(DISTINCT r.name) as Reports
WHERE ReportCount > 1
RETURN 
    d.name as Dataset,
    ReportCount,
    Reports
ORDER BY ReportCount DESC
LIMIT 20;
```

**Most shared tables:**

```cypher
// Tables used by the most reports
MATCH (t:Table)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH path = (t)<-[:USES_TABLE|READS_FROM]-()-[*1..5]-(r:Report)
WHERE (r)-[:BELONGS_TO]->(e)
WITH t, count(DISTINCT r) as ReportCount, collect(DISTINCT r.name) as Reports
WHERE ReportCount > 1
RETURN 
    t.name as Table,
    ReportCount,
    Reports[0..5] as SampleReports  // Show first 5 reports
ORDER BY ReportCount DESC
LIMIT 20;
```

**Tables used by most attributes:**

```cypher
// Tables heavily used by attributes
MATCH (t:Table)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (t)<-[:USES_TABLE]-(f:Form)<-[:HAS_FORM]-(a:Attribute)
WITH t, count(DISTINCT a) as AttributeCount, collect(DISTINCT a.name)[0..5] as SampleAttributes
WHERE AttributeCount > 1
RETURN 
    t.name as Table,
    AttributeCount,
    SampleAttributes
ORDER BY AttributeCount DESC
LIMIT 20;
```

---

## 5. Metric Lineage

### Q: Where does metric "DA" come from?

**Simple metric lineage:**

```cypher
// Lineage for metric DA
MATCH (m:Metric {name: 'DA'})-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
OPTIONAL MATCH (m)-[:USES_FUNCTION]->(func:Function)
OPTIONAL MATCH (m)-[:USES_FACT]->(fact:Fact)
OPTIONAL MATCH (fact)-[rf:READS_FROM]->(t:Table)
RETURN 
    m.name as Metric,
    m.tipo as Type,
    m.formula as Formula,
    func.name as Function,
    fact.name as Fact,
    collect(DISTINCT {table: t.name, column: rf.column_name}) as SourceTables;
```

**Composite metric breakdown (recursive):**

```cypher
// Recursive breakdown of composite metric
MATCH (m:Metric)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
WHERE m.tipo = 'composto'
MATCH path = (m)-[:COMPOSED_OF*1..5]->(component:Metric)
RETURN 
    m.name as CompositeMetric,
    length(path) as Depth,
    component.name as ComponentMetric,
    component.tipo as ComponentType,
    component.formula as ComponentFormula
ORDER BY m.name, Depth
LIMIT 50;
```

**Complete lineage from metric to table:**

```cypher
// Complete lineage: Metric -> Fact -> Table
MATCH (m:Metric {name: 'DA'})-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
OPTIONAL MATCH path1 = (m)-[:USES_FACT]->(fact:Fact)-[rf:READS_FROM]->(t:Table)
OPTIONAL MATCH path2 = (m)-[:COMPOSED_OF*]->(child:Metric)-[:USES_FACT]->(fact2:Fact)-[rf2:READS_FROM]->(t2:Table)
WITH m, 
     collect(DISTINCT {fact: fact.name, table: t.name, column: rf.column_name}) as DirectSources,
     collect(DISTINCT {metric: child.name, fact: fact2.name, table: t2.name, column: rf2.column_name}) as CompositeSourcesROW
RETURN 
    m.name as Metric,
    m.formula as Formula,
    DirectSources,
    CompositeSourcesROW as CompositeComponents;
```

---

## 6. Migration Planning

### Q: What tables must be migrated to move report "(Versão 0.0) - Entrada - Diretoria MD3"?

```cypher
// All tables needed for a specific report
MATCH (r:Report {name: '(Versão 0.0) - Entrada - Diretoria MD3'})-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FORM]->(f:Form)-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:Metric)-[:USES_FACT]->(fact:Fact)-[:READS_FROM]->(t2:Table)
WITH r, collect(DISTINCT t1) + collect(DISTINCT t2) as AllTables
UNWIND AllTables as t
WHERE t IS NOT NULL
RETURN DISTINCT 
    t.name as TableToMigrate,
    t.id as TableID
ORDER BY TableToMigrate;
```

**With column details:**

```cypher
// Tables with columns needed for report migration
MATCH (r:Report {name: '(Versão 0.0) - Entrada - Diretoria MD3'})-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FORM]->(f:Form)-[ut:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:Metric)-[:USES_FACT]->(fact:Fact)-[rf:READS_FROM]->(t2:Table)
WITH 
    collect(DISTINCT {table: t1.name, column: ut.column_name, usedBy: 'Attribute: ' + a.name}) as AttributeTables,
    collect(DISTINCT {table: t2.name, column: rf.column_name, usedBy: 'Metric: ' + m.name}) as MetricTables
UNWIND (AttributeTables + MetricTables) as tableInfo
RETURN DISTINCT 
    tableInfo.table as Table,
    tableInfo.column as Column,
    tableInfo.usedBy as UsedBy
ORDER BY Table, Column;
```

---

## 7. Dependency Analysis

### Q: Which reports can be migrated first with minimal dependencies?

**Reports with fewest table dependencies:**

```cypher
// Reports ranked by number of table dependencies
MATCH (r:Report)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FORM]->(f:Form)-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:Metric)-[:USES_FACT]->(fact:Fact)-[:READS_FROM]->(t2:Table)
WITH r, collect(DISTINCT t1) + collect(DISTINCT t2) as AllTables
WITH r, [t IN AllTables WHERE t IS NOT NULL] as Tables
RETURN 
    r.name as Report,
    size(Tables) as TableDependencyCount,
    [t IN Tables | t.name][0..5] as SampleTables
ORDER BY TableDependencyCount ASC, Report
LIMIT 20;
```

**Reports with no shared datasets:**

```cypher
// Reports that use unique datasets (easier to migrate)
MATCH (r:Report)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
WITH d, count(r) as ReportCount, collect(r.name)[0] as SingleReport
WHERE ReportCount = 1
RETURN 
    SingleReport as Report,
    d.name as UniqueDataset
ORDER BY Report
LIMIT 20;
```

**Migration groups by shared tables:**

```cypher
// Group reports by shared table dependencies
MATCH (t:Table)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH path = (t)<-[:USES_TABLE|READS_FROM]-()-[*1..5]-(r:Report)
WHERE (r)-[:BELONGS_TO]->(e)
WITH t, collect(DISTINCT r.name) as Reports
WHERE size(Reports) >= 2 AND size(Reports) <= 5
RETURN 
    t.name as SharedTable,
    size(Reports) as ReportCount,
    Reports as ReportsToMigrateTogethe r
ORDER BY ReportCount
LIMIT 20;
```

---

## 8. Advanced Analysis Queries

### Find circular dependencies in composite metrics:

```cypher
// Detect potential circular references
MATCH path = (m:Metric)-[:COMPOSED_OF*2..10]->(m)
WHERE (m)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
RETURN 
    m.name as Metric,
    length(path) as CircularDepth,
    [n IN nodes(path) | n.name] as CircularPath;
```

### Most complex reports (by relationship count):

```cypher
// Reports with most complex data model
MATCH (r:Report)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(a:Attribute)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:Metric)
RETURN 
    r.name as Report,
    count(DISTINCT d) as Datasets,
    count(DISTINCT a) as Attributes,
    count(DISTINCT m) as Metrics,
    (count(DISTINCT d) + count(DISTINCT a) + count(DISTINCT m)) as TotalComplexity
ORDER BY TotalComplexity DESC
LIMIT 20;
```

### Find tables with most column usage:

```cypher
// Tables with most distinct columns used
MATCH (t:Table)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (t)<-[rel:USES_TABLE|READS_FROM]-()
RETURN 
    t.name as Table,
    count(DISTINCT rel.column_name) as UniqueColumnsUsed,
    collect(DISTINCT rel.column_name)[0..10] as SampleColumns
ORDER BY UniqueColumnsUsed DESC
LIMIT 20;
```

### Impact radius (how many reports one table affects):

```cypher
// Tables with widest impact radius
MATCH (t:Table {name: 'FT_ORCM_ACOMP_VERBAS'})-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH path = (t)<-[:USES_TABLE|READS_FROM*1..1]-()-[*1..6]-(r:Report)
WHERE (r)-[:BELONGS_TO]->(e)
WITH t, collect(DISTINCT r) as AffectedReports, 
     collect(DISTINCT [n IN nodes(path) WHERE n:Dataset | n.name]) as IntermediateDatasets
RETURN 
    t.name as Table,
    size(AffectedReports) as ReportImpactCount,
    [r IN AffectedReports | r.name][0..10] as SampleAffectedReports,
    size(IntermediateDatasets) as IntermediateDatasetCount;
```

---

## 9. Performance Tips

### Create indexes for faster queries:

All necessary indexes should already be created by the `init_neo4j_schema.py` script, but you can verify:

```cypher
SHOW INDEXES;
```

### Use EXPLAIN to optimize queries:

```cypher
EXPLAIN
MATCH (t:Table {name: 'trans_TB_MD3_OBJETOS'})-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (t)<-[:USES_TABLE]-(f:Form)<-[:HAS_FORM]-(a:Attribute)
RETURN count(a);
```

### Use PROFILE to find bottlenecks:

```cypher
PROFILE
MATCH (t:Table {name: 'trans_TB_MD3_OBJETOS'})-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (t)<-[:USES_TABLE]-(f:Form)<-[:HAS_FORM]-(a:Attribute)
RETURN count(a);
```

---

## 10. Quick Reference Queries

**Count all entities:**

```cypher
MATCH (n)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
RETURN labels(n)[0] as Type, count(n) as Count
ORDER BY Count DESC;
```

**Sample data from each type:**

```cypher
// Sample reports
MATCH (r:Report)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
RETURN r.name
LIMIT 5;
```

**Find a specific entity:**

```cypher
// Find by name (fuzzy search)
MATCH (n)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
WHERE toLower(n.name) CONTAINS 'objetos'
RETURN labels(n)[0] as Type, n.name as Name
LIMIT 10;
```

---

## 📚 Additional Resources

- **GRAPHMODEL.md**: Complete graph schema documentation
- **Neo4j Browser**: http://localhost:7474
- **Neo4j Bloom**: Visual exploration tool (included)

---

**Pro Tip**: Save frequently used queries as "Favorites" in Neo4j Browser for quick access!

