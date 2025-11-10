# Neo4j Migration Visual Queries

Simple visual queries for migration planning. Returns graphs you can explore.

**Environment ID**: `20250519221644`

---

## Question 6: What tables must be migrated to move report Y?

### Visual Query - See Complete Dependency Graph

**Example: Report `(Versão 0.0) - Entrada - Diretoria MD3`**

```cypher
// Show complete report structure with all tables
MATCH path = (r:Report {name: '(Versão 0.0) - Entrada - Diretoria MD3'})
             -[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH path1 = (r)-[:CONTAINS]->(d:Dataset)-[:HAS_ATTRIBUTE]->(a:Attribute)
              -[:HAS_FORM]->(f:Form)-[:USES_TABLE]->(t:Table)
RETURN r, d, a, f, t
LIMIT 200
UNION
MATCH path = (r:Report {name: '(Versão 0.0) - Entrada - Diretoria MD3'})
             -[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH path2 = (r)-[:CONTAINS]->(d:Dataset)-[:HAS_METRIC]->(m:Metric)
              -[:USES_FACT]->(fact:Fact)-[:READS_FROM]->(t:Table)
RETURN r, d, m, fact, t
LIMIT 200;
```

**What you'll see:**
- 🔵 Blue Report node in the center
- 🟡 Yellow Dataset nodes connected to the report
- 🟢 Green Attribute nodes
- 🔴 Pink Metric nodes
- 🟣 Purple Table nodes at the edges
- All relationships connecting them

**To explore:**
- Double-click any Table to see all its connections
- Click on relationships to see properties (like `column_name`)
- Right-click → Expand to see more

---

### Alternative: Simpler View (Tables Only)

```cypher
// Show just Report → Datasets → Tables
MATCH (r:Report {name: '(Versão 0.0) - Entrada - Diretoria MD3'})
      -[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE*1..2]->()-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC*1..2]->()-[:READS_FROM]->(t2:Table)
RETURN r, d, t1, t2
LIMIT 200;
```

---

### Get Table List (if you need just names)

```cypher
// Get list of tables to migrate
MATCH (r:Report {name: '(Versão 0.0) - Entrada - Diretoria MD3'})
      -[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(:Attribute)-[:HAS_FORM]->(:Form)-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(:Metric)-[:USES_FACT]->(:Fact)-[:READS_FROM]->(t2:Table)
WITH collect(DISTINCT t1.name) + collect(DISTINCT t2.name) as allTables
UNWIND allTables as tableName
WHERE tableName IS NOT NULL
RETURN DISTINCT tableName as TableToMigrate
ORDER BY tableName;
```

---

## Question 7: Which reports can be migrated first with minimal dependencies?

### Visual Query - Reports with Fewest Dependencies

```cypher
// Find reports with 5 or fewer tables
MATCH (r:Report)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE*1..2]->()-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC*1..2]->()-[:READS_FROM]->(t2:Table)
WITH r, d, 
     collect(DISTINCT t1) + collect(DISTINCT t2) as tables,
     count(DISTINCT t1) + count(DISTINCT t2) as tableCount
WHERE tableCount > 0 AND tableCount <= 5
RETURN r, d, tables[0] as sampleTable, tableCount
ORDER BY tableCount ASC
LIMIT 10;
```

**What you'll see:**
- Multiple Report nodes
- Their connected Datasets
- Sample Table connections
- Reports are ordered by complexity (simplest first)

---

### Show One Simple Report Completely

```cypher
// Pick the simplest report and show its full structure
MATCH (r:Report)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(:Attribute)-[:HAS_FORM]->(:Form)-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(:Metric)-[:USES_FACT]->(:Fact)-[:READS_FROM]->(t2:Table)
WITH r, d, 
     count(DISTINCT t1) + count(DISTINCT t2) as tableCount
ORDER BY tableCount ASC
LIMIT 1
MATCH path = (r)-[:CONTAINS]->(d)
OPTIONAL MATCH path1 = (d)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FORM]->(f:Form)-[:USES_TABLE]->(t:Table)
OPTIONAL MATCH path2 = (d)-[:HAS_METRIC]->(m:Metric)-[:USES_FACT]->(fact:Fact)-[:READS_FROM]->(t2:Table)
RETURN r, d, a, f, m, fact, t, t2
LIMIT 100;
```

---

### Compare Multiple Reports

```cypher
// Show 5 simplest reports side by side
MATCH (r:Report)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE*1..2]->()-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC*1..2]->()-[:READS_FROM]->(t2:Table)
WITH r, d,
     count(DISTINCT t1) + count(DISTINCT t2) as tableCount,
     collect(DISTINCT t1)[0] as sampleTable1,
     collect(DISTINCT t2)[0] as sampleTable2
WHERE tableCount > 0
ORDER BY tableCount ASC
LIMIT 5
RETURN r, d, sampleTable1, sampleTable2, tableCount;
```

---

### Get Migration Priority List

```cypher
// Ranked list of reports by complexity
MATCH (r:Report)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(:Attribute)-[:HAS_FORM]->(:Form)-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(:Metric)-[:USES_FACT]->(:Fact)-[:READS_FROM]->(t2:Table)
WITH r, 
     count(DISTINCT d) as datasetCount,
     count(DISTINCT t1) + count(DISTINCT t2) as tableCount
ORDER BY tableCount ASC, datasetCount ASC
RETURN 
    r.name as Report,
    datasetCount as Datasets,
    tableCount as TableDependencies,
    CASE 
        WHEN tableCount <= 3 THEN '✅ Easy'
        WHEN tableCount <= 10 THEN '⚠️ Medium'
        ELSE '❌ Complex'
    END as MigrationComplexity
LIMIT 20;
```

---

## 🎯 Quick Tests

### Test with your first report:

```cypher
// Show first report structure
MATCH (r:Report)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
WITH r LIMIT 1
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(a:Attribute)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:Metric)
OPTIONAL MATCH (a)-[:HAS_FORM]->(f:Form)-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (m)-[:USES_FACT]->(fact:Fact)-[:READS_FROM]->(t2:Table)
RETURN r, d, a, m, f, fact, t1, t2
LIMIT 100;
```

### Find a specific report by partial name:

```cypher
// Search for report
MATCH (r:Report)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
WHERE toLower(r.name) CONTAINS 'entrada'
RETURN r.name as ReportName
LIMIT 10;
```

Then use the full name in the queries above.

---

## 💡 Tips for Visual Exploration

1. **Start with the list query** to get table names
2. **Then use the visual query** to see the graph
3. **Double-click nodes** to expand and explore
4. **Right-click relationships** to see properties (column names)
5. **Use LIMIT** to control graph size (50-200 nodes works well)

---

## 🎨 Neo4j Browser Tips

**To make it look better:**

1. Click on a node color at the bottom
2. Choose a custom color
3. Pin important nodes by dragging them
4. Hide node types by clicking the label at the bottom

**To export:**

1. Click the download icon
2. Choose PNG or SVG
3. Save for documentation

---

## ⚡ Performance Notes

- If query is slow, reduce LIMIT
- Start with 50-100 nodes
- Gradually increase if needed
- Use PROFILE to check performance:

```cypher
PROFILE
MATCH (r:Report {name: 'YourReportName'})
      -[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
RETURN r, d;
```

---

**Ready to use!** Copy any query above into Neo4j Browser at http://localhost:7474 🚀

