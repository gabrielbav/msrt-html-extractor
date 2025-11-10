# Neo4j Visual Graph Queries

Simple queries that return **graph visualizations** in Neo4j Browser. Each query returns nodes and relationships you can navigate visually.

**Environment ID**: `20250519221644`

---

## 1️⃣ If I change table X, what reports will be affected?

**Example: Table `trans_TB_MD3_OBJETOS`**

```cypher
MATCH path = (r:Report)-[:CONTAINS]->(d:Dataset)-[:HAS_ATTRIBUTE]->(a:Attribute)
             -[:HAS_FORM]->(f:Form)-[:USES_TABLE]->(t:Table {name: 'trans_TB_MD3_OBJETOS'})
WHERE (r)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
RETURN path
LIMIT 100;
```

**Navigate**: Click on any node to explore its properties and connections.

---

## 2️⃣ If I change column name X, what metrics will break?

**Example: Column `VL_REALIZADO`**

```cypher
MATCH path = (r:Report)-[:CONTAINS]->(d:Dataset)-[:HAS_METRIC]->(m:Metric)
             -[:USES_FACT]->(f:Fact)-[rf:READS_FROM]->(t:Table)
WHERE rf.column_name = 'VL_REALIZADO'
  AND (r)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
RETURN path
LIMIT 50;
```

**What to look for**: The `READS_FROM` relationship has the `column_name` property.

---

## 3️⃣ What tables are no longer used by any active report?

```cypher
MATCH (t:Table)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
WHERE NOT EXISTS {
    MATCH (t)<-[:USES_TABLE|READS_FROM]-()-[*1..5]-(r:Report)
    WHERE (r)-[:BELONGS_TO]->(e)
}
RETURN t
LIMIT 50;
```

**Result**: Isolated table nodes with no connections to reports.

---

## 4️⃣ Which datasets or tables are shared by multiple reports?

**Most shared datasets:**

```cypher
MATCH path = (r:Report)-[:CONTAINS]->(d:Dataset)
WHERE (r)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
WITH d, count(DISTINCT r) as reportCount
WHERE reportCount > 1
MATCH path = (r:Report)-[:CONTAINS]->(d)
RETURN path
LIMIT 100;
```

**Visualization**: You'll see one Dataset node connected to multiple Report nodes.

---

## 5️⃣ Where does metric X come from?

**Example: Metric `DA`**

```cypher
MATCH path = (m:Metric {name: 'DA'})-[:USES_FUNCTION]->(func:Function)
WHERE (m)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
RETURN path
UNION
MATCH path = (m:Metric {name: 'DA'})-[:USES_FACT]->(f:Fact)-[:READS_FROM]->(t:Table)
WHERE (m)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
RETURN path;
```

**Shows**: Metric → Function + Metric → Fact → Table path.

---

## 6️⃣ What tables must be migrated to move report Y?

**Example: Report `(Versão 0.0) - Entrada - Diretoria MD3`**

```cypher
MATCH (r:Report {name: '(Versão 0.0) - Entrada - Diretoria MD3'})
      -[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH path = (r)-[:CONTAINS]->(d:Dataset)-[:HAS_ATTRIBUTE]->(:Attribute)
             -[:HAS_FORM]->(:Form)-[:USES_TABLE]->(t:Table)
RETURN path
LIMIT 100
UNION
MATCH (r:Report {name: '(Versão 0.0) - Entrada - Diretoria MD3'})
      -[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH path = (r)-[:CONTAINS]->(d:Dataset)-[:HAS_METRIC]->(:Metric)
             -[:USES_FACT]->(:Fact)-[:READS_FROM]->(t:Table)
RETURN path
LIMIT 100;
```

**Shows**: Complete dependency tree from Report to all Tables.

---

## 7️⃣ Which reports can be migrated first with minimal dependencies?

```cypher
MATCH (r:Report)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH (r)-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH path1 = (d)-[:HAS_ATTRIBUTE]->(:Attribute)-[:HAS_FORM]->(:Form)-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH path2 = (d)-[:HAS_METRIC]->(:Metric)-[:USES_FACT]->(:Fact)-[:READS_FROM]->(t2:Table)
WITH r, d, 
     count(DISTINCT t1) + count(DISTINCT t2) as tableCount,
     collect(path1) + collect(path2) as paths
WHERE tableCount <= 5
RETURN r, d, paths
LIMIT 20;
```

**Shows**: Reports with fewest table dependencies (≤5 tables).

---

## 🎯 Bonus Queries

### Show complete report structure

```cypher
MATCH path = (r:Report {name: '(Versão 0.0) - Entrada - Diretoria MD3'})
             -[:CONTAINS]->(d:Dataset)
             -[:HAS_ATTRIBUTE|HAS_METRIC]->(entity)
WHERE (r)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
RETURN path
LIMIT 100;
```

### Trace composite metric breakdown

```cypher
MATCH path = (m:Metric)-[:COMPOSED_OF*1..3]->(component:Metric)
WHERE m.tipo = 'composto'
  AND (m)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
RETURN path
LIMIT 50;
```

### Find most connected table

```cypher
MATCH (t:Table)-[:BELONGS_TO]->(e:Environment {id: '20250519221644'})
MATCH path = (t)<-[:USES_TABLE|READS_FROM]-(entity)
WITH t, count(path) as connections
ORDER BY connections DESC
LIMIT 1
MATCH fullPath = (t)<-[:USES_TABLE|READS_FROM]-(entity)-[*1..3]-(r:Report)
RETURN fullPath
LIMIT 100;
```

### Show table usage across reports

**Example: `FT_ORCM_ACOMP_VERBAS`**

```cypher
MATCH (t:Table {name: 'FT_ORCM_ACOMP_VERBAS'})-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH path = (t)<-[:USES_TABLE|READS_FROM]-()-[*1..4]-(r:Report)
RETURN path
LIMIT 100;
```

---

## 🎨 Visualization Tips

### In Neo4j Browser:

1. **Expand nodes**: Double-click any node to see its connections
2. **Pin nodes**: Drag nodes to organize the layout
3. **Relationship details**: Click on edges to see properties (like `column_name`)
4. **Filter by type**: Click node labels in the bottom panel to hide/show types
5. **Change colors**: Right-click node → Style → Change color

### Neo4j Bloom:

1. Open Bloom from Neo4j Browser sidebar
2. Search for any report, table, or metric by name
3. Use "Expand" to explore connections
4. Create custom perspectives with color schemes

### Suggested Color Scheme:

- **Report**: Blue (`#5DADE2`)
- **Dataset**: Yellow (`#F4D03F`)
- **Attribute**: Green (`#52BE80`)
- **Metric**: Pink (`#EC7063`)
- **Fact**: Orange (`#E67E22`)
- **Function**: Light Green (`#A9DFBF`)
- **Table**: Purple (`#AF7AC5`)
- **Form**: Light Blue (`#85C1E2`)
- **Environment**: Gray (`#95A5A6`)

---

## 📖 Quick Reference

### Find anything by name:

```cypher
MATCH (n)-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
WHERE toLower(n.name) CONTAINS 'your_search_term'
RETURN n
LIMIT 20;
```

### Explore from a node:

```cypher
MATCH (n {name: 'YourNodeName'})-[:BELONGS_TO]->(:Environment {id: '20250519221644'})
MATCH path = (n)-[*1..2]-(connected)
RETURN path
LIMIT 100;
```

### Show all relationship types:

```cypher
MATCH ()-[r]->()
RETURN DISTINCT type(r) as RelationshipType;
```

---

## 💡 Pro Tips

1. **Use LIMIT**: Always limit results for visual queries (50-100 nodes max)
2. **Path queries**: Use `MATCH path = ...` and `RETURN path` for best visualizations
3. **Combine paths**: Use `UNION` to show multiple relationship paths
4. **Click to explore**: Double-click nodes in the visualization to expand
5. **Save favorites**: Star queries you use frequently in Neo4j Browser

---

**Next steps**: Open Neo4j Browser at http://localhost:7474 and paste any query above! 🚀

