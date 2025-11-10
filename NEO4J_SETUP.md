# Neo4j Setup Guide - Quick Reference

This is a quick start guide for setting up and using Neo4j with your MicroStrategy data.

## 📋 Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ with pip
- MicroStrategy data extracted to `output.json`

## 🚀 Quick Start (3 Steps)

### Step 1: Start Neo4j

```bash
# Start Neo4j container
docker-compose up -d

# Verify it's running
docker-compose ps

# Check logs (optional)
docker-compose logs -f neo4j
```

**Access Neo4j Browser**: http://localhost:7474
- Username: `neo4j`
- Password: `microstrategy2024` (change in `.env` if needed)

### Step 2: Initialize Schema

```bash
# Install dependencies
pip install neo4j python-dotenv

# Create constraints and indexes
python scripts/init_neo4j_schema.py
```

Expected output:
```
✓ Connected to Neo4j
✓ Created 8/8 constraints
✓ Created 9/9 indexes
✓ Schema initialization complete!
```

### Step 3: Load Data

```bash
# Load your data with an environment identifier
python scripts/load_to_neo4j.py \
  --json-file output.json \
  --environment-id prod-2024-11 \
  --environment-name "Production"
```

**That's it!** Your data is now in Neo4j.

## 🔍 Verify Data Loading

Open Neo4j Browser (http://localhost:7474) and run:

```cypher
// Count all nodes by type
MATCH (n)
RETURN labels(n)[0] as NodeType, count(n) as Count
ORDER BY Count DESC;

// View environment summary
MATCH (e:Environment)
RETURN e.name, e.id, e.created_at;

// Find a sample report
MATCH (r:Report)
RETURN r.name, r.id
LIMIT 5;
```

## 📝 Common Operations

### Update Existing Data

```bash
# Re-run with same environment ID to update
python scripts/load_to_neo4j.py \
  --json-file output_updated.json \
  --environment-id prod-2024-11 \
  --environment-name "Production"
```

### Load Multiple Environments

```bash
# Production
python scripts/load_to_neo4j.py \
  --json-file prod_data.json \
  --environment-id prod-2024-11 \
  --environment-name "Production"

# Development
python scripts/load_to_neo4j.py \
  --json-file dev_data.json \
  --environment-id dev-2024-11 \
  --environment-name "Development"
```

### Load Specific Entities Only

```bash
# Load only reports and datasets
python scripts/load_to_neo4j.py \
  --json-file output.json \
  --environment-id test \
  --environment-name "Test" \
  --entities reports,datasets
```

Available entities: `all`, `reports`, `datasets`, `attributes`, `metrics`, `facts`, `tables`

### Dry Run (Preview Without Loading)

```bash
python scripts/load_to_neo4j.py \
  --json-file output.json \
  --environment-id test \
  --environment-name "Test" \
  --dry-run
```

## 🔎 Useful Cypher Queries

### 1. Find Reports Using a Specific Table

```cypher
MATCH (r:Report)-[:CONTAINS]->(d:Dataset)-[:HAS_ATTRIBUTE]->
      (a:Attribute)-[:HAS_FORM]->(f:Form)-[:USES_TABLE]->
      (t:Table {name: 'YOUR_TABLE_NAME'})
RETURN DISTINCT r.name as Report, r.id as ReportID;
```

### 2. Trace Metric Lineage

```cypher
MATCH path = (m:Metric {name: 'YOUR_METRIC_NAME'})-[:COMPOSED_OF*]->(component:Metric)
RETURN component.name, component.tipo, component.formula, length(path) as Depth
ORDER BY Depth;
```

### 3. Environment Statistics

```cypher
MATCH (e:Environment)
OPTIONAL MATCH (n)-[:BELONGS_TO]->(e)
RETURN e.name as Environment, 
       labels(n)[0] as NodeType, 
       count(n) as Count
ORDER BY e.name, Count DESC;
```

### 4. Find All Tables Used by a Report

```cypher
MATCH (r:Report {name: 'YOUR_REPORT_NAME'})-[:CONTAINS]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FORM]->(f:Form)-[:USES_TABLE]->(t1:Table)
OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:Metric)-[:USES_FACT]->(fact:Fact)-[:READS_FROM]->(t2:Table)
WITH r, collect(DISTINCT t1.name) + collect(DISTINCT t2.name) as AllTables
UNWIND AllTables as TableName
RETURN DISTINCT TableName
ORDER BY TableName;
```

### 5. Delete Environment Data

```cypher
// Delete all data for a specific environment
MATCH (e:Environment {id: 'dev-2024-11'})
OPTIONAL MATCH (n)-[:BELONGS_TO]->(e)
DETACH DELETE e, n;
```

## 🎨 Neo4j Bloom (Visual Exploration)

Neo4j Bloom is included in the Docker setup. Access it through Neo4j Browser:

1. Open http://localhost:7474
2. Click on "Neo4j Bloom" in the left sidebar
3. Create a new perspective
4. Start exploring your graph visually!

**Suggested node colors:**
- Reports: Blue
- Datasets: Yellow
- Attributes: Green
- Metrics: Pink
- Facts: Orange
- Tables: Purple
- Environment: Gray

## 🛠️ Troubleshooting

### Neo4j Won't Start

```bash
# Check logs
docker-compose logs neo4j

# Stop and remove containers
docker-compose down

# Start fresh
docker-compose up -d
```

### Connection Refused

Make sure Neo4j is fully started:
```bash
docker-compose ps
# Should show "healthy" status
```

Wait 30 seconds after starting and try again.

### Out of Memory

Edit `.env` file and increase memory:
```bash
NEO4J_HEAP_MAX=4G
NEO4J_PAGECACHE=1G
```

Then restart:
```bash
docker-compose restart neo4j
```

### Clear All Data and Start Over

```cypher
// In Neo4j Browser
MATCH (n) DETACH DELETE n;
```

Then re-initialize and reload:
```bash
python scripts/init_neo4j_schema.py
python scripts/load_to_neo4j.py --json-file output.json --environment-id prod --environment-name "Production"
```

## 📚 Documentation

- **[GRAPHMODEL.md](GRAPHMODEL.md)**: Complete graph schema, constraints, indexes, and query examples
- **[README.md](README.md)**: Full project documentation including Neo4j section
- **Neo4j Documentation**: https://neo4j.com/docs/

## 🔐 Security Note

**Change the default password!**

Edit `.env` (create from example if needed):
```bash
NEO4J_PASSWORD=your_secure_password_here
```

Restart Neo4j:
```bash
docker-compose restart neo4j
```

## 📞 Support

For issues:
1. Check Docker logs: `docker-compose logs neo4j`
2. Verify Neo4j is healthy: `docker-compose ps`
3. Test connection: `python scripts/init_neo4j_schema.py`
4. Review error messages in script output

---

**Happy Graph Querying! 🎉**

