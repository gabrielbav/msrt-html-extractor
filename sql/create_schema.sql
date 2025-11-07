-- =================================================================
-- Script de Criação do Schema Normalizado
-- Database: PostgreSQL (adaptar para outros SGBDs conforme necessário)
-- =================================================================

-- Drop tables if exists (em ordem reversa de dependências)
DROP TABLE IF EXISTS fact_tables CASCADE;
DROP TABLE IF EXISTS metric_functions CASCADE;
DROP TABLE IF EXISTS metric_facts CASCADE;
DROP TABLE IF EXISTS metric_metrics CASCADE;
DROP TABLE IF EXISTS form_tables CASCADE;
DROP TABLE IF EXISTS attribute_forms CASCADE;
DROP TABLE IF EXISTS dataset_metrics CASCADE;
DROP TABLE IF EXISTS dataset_attributes CASCADE;
DROP TABLE IF EXISTS report_datasets CASCADE;
DROP TABLE IF EXISTS attributes_forms CASCADE;
DROP TABLE IF EXISTS tables CASCADE;
DROP TABLE IF EXISTS facts CASCADE;
DROP TABLE IF EXISTS metrics CASCADE;
DROP TABLE IF EXISTS functions CASCADE;
DROP TABLE IF EXISTS attributes CASCADE;
DROP TABLE IF EXISTS datasets CASCADE;
DROP TABLE IF EXISTS reports CASCADE;

-- =================================================================
-- TABELAS PRINCIPAIS (Entidades)
-- =================================================================

-- Reports (Relatórios)
CREATE TABLE reports (
    id VARCHAR(255) PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE reports IS 'Armazena informações sobre relatórios';
COMMENT ON COLUMN reports.id IS 'Identificador único do relatório';
COMMENT ON COLUMN reports.name IS 'Nome do relatório';
COMMENT ON COLUMN reports.file_path IS 'Caminho do arquivo HTML de referência';

-- Datasets (Cubos Inteligentes)
CREATE TABLE datasets (
    id VARCHAR(255) PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT,
    application_object VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE datasets IS 'Armazena informações sobre datasets (cubos inteligentes)';
COMMENT ON COLUMN datasets.id IS 'Identificador único do dataset';
COMMENT ON COLUMN datasets.name IS 'Nome do dataset';
COMMENT ON COLUMN datasets.application_object IS 'Tipo de objeto (ex: CuboInteligente)';

-- Attributes (Atributos)
CREATE TABLE attributes (
    id VARCHAR(255) PRIMARY KEY,
    name TEXT NOT NULL,
    name_on_dataset TEXT,
    file_path TEXT,
    application_schema VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE attributes IS 'Armazena informações sobre atributos utilizados nos datasets';
COMMENT ON COLUMN attributes.id IS 'Identificador único do atributo';
COMMENT ON COLUMN attributes.name IS 'Nome completo do atributo';
COMMENT ON COLUMN attributes.name_on_dataset IS 'Nome como aparece no dataset';
COMMENT ON COLUMN attributes.application_schema IS 'Esquema da aplicação';

-- Attributes Forms (Formulários de Atributos)
CREATE TABLE attributes_forms (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    attribute_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE attributes_forms IS 'Armazena informações sobre formulários de atributos';
COMMENT ON COLUMN attributes_forms.id IS 'Identificador único do formulário';
COMMENT ON COLUMN attributes_forms.name IS 'Nome do formulário (ex: ID, DESC)';
COMMENT ON COLUMN attributes_forms.attribute_id IS 'Referência ao atributo pai';

-- Functions (Funções)
CREATE TABLE functions (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE functions IS 'Armazena informações sobre funções utilizadas nas métricas';
COMMENT ON COLUMN functions.id IS 'Identificador único da função';
COMMENT ON COLUMN functions.name IS 'Nome da função (ex: Sum, Avg, Count)';

-- Metrics (Métricas)
CREATE TABLE metrics (
    id VARCHAR(255) PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT,
    application_object VARCHAR(100),
    tipo VARCHAR(20) CHECK (tipo IN ('simples', 'composto')),
    formula TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE metrics IS 'Armazena informações sobre métricas (simples e compostas)';
COMMENT ON COLUMN metrics.id IS 'Identificador único da métrica';
COMMENT ON COLUMN metrics.name IS 'Nome da métrica';
COMMENT ON COLUMN metrics.tipo IS 'Tipo da métrica (simples ou composto)';
COMMENT ON COLUMN metrics.formula IS 'Fórmula da métrica';

-- Facts (Fatos/Medidas)
CREATE TABLE facts (
    id VARCHAR(255) PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE facts IS 'Armazena informações sobre fatos (medidas) utilizados nas métricas simples';
COMMENT ON COLUMN facts.id IS 'Identificador único do fato';
COMMENT ON COLUMN facts.name IS 'Nome do fato';

-- Tables (Tabelas Lógicas)
CREATE TABLE tables (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE tables IS 'Armazena informações sobre tabelas lógicas (físicas) do banco de dados';
COMMENT ON COLUMN tables.id IS 'Identificador único da tabela';
COMMENT ON COLUMN tables.name IS 'Nome da tabela lógica';

-- =================================================================
-- TABELAS DE RELACIONAMENTO
-- =================================================================

-- Report <-> Dataset (N:N)
CREATE TABLE report_datasets (
    report_id VARCHAR(255) NOT NULL,
    dataset_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (report_id, dataset_id),
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

COMMENT ON TABLE report_datasets IS 'Relacionamento N:N entre relatórios e datasets';

-- Dataset <-> Attribute (N:N)
CREATE TABLE dataset_attributes (
    dataset_id VARCHAR(255) NOT NULL,
    attribute_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dataset_id, attribute_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (attribute_id) REFERENCES attributes(id) ON DELETE CASCADE
);

COMMENT ON TABLE dataset_attributes IS 'Relacionamento N:N entre datasets e atributos';

-- Dataset <-> Metric (N:N)
CREATE TABLE dataset_metrics (
    dataset_id VARCHAR(255) NOT NULL,
    metric_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dataset_id, metric_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (metric_id) REFERENCES metrics(id) ON DELETE CASCADE
);

COMMENT ON TABLE dataset_metrics IS 'Relacionamento N:N entre datasets e métricas';

-- Attribute <-> AttributeForm (N:N)
CREATE TABLE attribute_forms (
    attribute_id VARCHAR(255) NOT NULL,
    form_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (attribute_id, form_id),
    FOREIGN KEY (attribute_id) REFERENCES attributes(id) ON DELETE CASCADE,
    FOREIGN KEY (form_id) REFERENCES attributes_forms(id) ON DELETE CASCADE
);

COMMENT ON TABLE attribute_forms IS 'Relacionamento N:N entre atributos e formulários';

-- AttributeForm <-> Table (N:N)
CREATE TABLE form_tables (
    form_id VARCHAR(255) NOT NULL,
    table_id VARCHAR(255) NOT NULL,
    column_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (form_id, table_id),
    FOREIGN KEY (form_id) REFERENCES attributes_forms(id) ON DELETE CASCADE,
    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE
);

COMMENT ON TABLE form_tables IS 'Relacionamento N:N entre formulários de atributos e tabelas lógicas';
COMMENT ON COLUMN form_tables.column_name IS 'Nome da coluna na tabela física';

-- Metric <-> Metric (Hierárquico - Métricas Compostas)
CREATE TABLE metric_metrics (
    parent_metric_id VARCHAR(255) NOT NULL,
    child_metric_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (parent_metric_id, child_metric_id),
    FOREIGN KEY (parent_metric_id) REFERENCES metrics(id) ON DELETE CASCADE,
    FOREIGN KEY (child_metric_id) REFERENCES metrics(id) ON DELETE CASCADE,
    CHECK (parent_metric_id != child_metric_id)
);

COMMENT ON TABLE metric_metrics IS 'Relacionamento hierárquico N:N entre métricas (para métricas compostas)';

-- Metric <-> Fact (1:1 para métricas simples)
CREATE TABLE metric_facts (
    metric_id VARCHAR(255) NOT NULL,
    fact_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (metric_id, fact_id),
    FOREIGN KEY (metric_id) REFERENCES metrics(id) ON DELETE CASCADE,
    FOREIGN KEY (fact_id) REFERENCES facts(id) ON DELETE CASCADE
);

COMMENT ON TABLE metric_facts IS 'Relacionamento 1:1 entre métricas simples e fatos';

-- Metric <-> Function (N:1 para métricas simples)
CREATE TABLE metric_functions (
    metric_id VARCHAR(255) NOT NULL,
    function_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (metric_id, function_id),
    FOREIGN KEY (metric_id) REFERENCES metrics(id) ON DELETE CASCADE,
    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE
);

COMMENT ON TABLE metric_functions IS 'Relacionamento N:1 entre métricas simples e funções';

-- Fact <-> Table (N:N)
CREATE TABLE fact_tables (
    fact_id VARCHAR(255) NOT NULL,
    table_id VARCHAR(255) NOT NULL,
    column_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (fact_id, table_id),
    FOREIGN KEY (fact_id) REFERENCES facts(id) ON DELETE CASCADE,
    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE
);

COMMENT ON TABLE fact_tables IS 'Relacionamento N:N entre fatos e tabelas lógicas';
COMMENT ON COLUMN fact_tables.column_name IS 'Nome da coluna na tabela física';

-- =================================================================
-- ÍNDICES PARA OTIMIZAÇÃO DE QUERIES
-- =================================================================

-- Índices em chaves estrangeiras
CREATE INDEX idx_report_datasets_dataset ON report_datasets(dataset_id);
CREATE INDEX idx_dataset_attributes_attribute ON dataset_attributes(attribute_id);
CREATE INDEX idx_dataset_metrics_metric ON dataset_metrics(metric_id);
CREATE INDEX idx_attribute_forms_form ON attribute_forms(form_id);
CREATE INDEX idx_form_tables_table ON form_tables(table_id);
CREATE INDEX idx_metric_metrics_child ON metric_metrics(child_metric_id);
CREATE INDEX idx_metric_facts_fact ON metric_facts(fact_id);
CREATE INDEX idx_metric_functions_function ON metric_functions(function_id);
CREATE INDEX idx_fact_tables_table ON fact_tables(table_id);

-- Índices em colunas frequentemente usadas em buscas
CREATE INDEX idx_attributes_forms_attribute ON attributes_forms(attribute_id);
CREATE INDEX idx_metrics_tipo ON metrics(tipo);
CREATE INDEX idx_datasets_application_object ON datasets(application_object);

-- Índices de texto completo para buscas por nome
CREATE INDEX idx_reports_name ON reports USING gin(to_tsvector('portuguese', name));
CREATE INDEX idx_datasets_name ON datasets USING gin(to_tsvector('portuguese', name));
CREATE INDEX idx_attributes_name ON attributes USING gin(to_tsvector('portuguese', name));
CREATE INDEX idx_metrics_name ON metrics USING gin(to_tsvector('portuguese', name));

-- =================================================================
-- VIEWS ÚTEIS
-- =================================================================

-- View: Métricas com suas funções e fatos (apenas simples)
CREATE OR REPLACE VIEW v_simple_metrics AS
SELECT 
    m.id AS metric_id,
    m.name AS metric_name,
    m.formula,
    f.id AS function_id,
    f.name AS function_name,
    fa.id AS fact_id,
    fa.name AS fact_name
FROM metrics m
LEFT JOIN metric_functions mf ON m.id = mf.metric_id
LEFT JOIN functions f ON mf.function_id = f.id
LEFT JOIN metric_facts mfa ON m.id = mfa.metric_id
LEFT JOIN facts fa ON mfa.fact_id = fa.id
WHERE m.tipo = 'simples';

COMMENT ON VIEW v_simple_metrics IS 'View com detalhes de métricas simples incluindo funções e fatos';

-- View: Métricas compostas com suas dependências
CREATE OR REPLACE VIEW v_composite_metrics AS
SELECT 
    m1.id AS parent_metric_id,
    m1.name AS parent_metric_name,
    m1.formula AS parent_formula,
    m2.id AS child_metric_id,
    m2.name AS child_metric_name,
    m2.tipo AS child_tipo
FROM metrics m1
JOIN metric_metrics mm ON m1.id = mm.parent_metric_id
JOIN metrics m2 ON mm.child_metric_id = m2.id
WHERE m1.tipo = 'composto';

COMMENT ON VIEW v_composite_metrics IS 'View com métricas compostas e suas métricas filhas';

-- View: Linhagem completa de atributos (atributo -> formulário -> tabela)
CREATE OR REPLACE VIEW v_attribute_lineage AS
SELECT 
    a.id AS attribute_id,
    a.name AS attribute_name,
    a.name_on_dataset,
    af.id AS form_id,
    af.name AS form_name,
    t.id AS table_id,
    t.name AS table_name,
    ft.column_name
FROM attributes a
JOIN attributes_forms af ON a.id = af.attribute_id
JOIN attribute_forms afo ON af.id = afo.form_id
JOIN form_tables ft ON af.id = ft.form_id
JOIN tables t ON ft.table_id = t.id;

COMMENT ON VIEW v_attribute_lineage IS 'View com linhagem completa de atributos até tabelas físicas';

-- View: Linhagem completa de métricas simples (métrica -> fato -> tabela)
CREATE OR REPLACE VIEW v_metric_lineage AS
SELECT 
    m.id AS metric_id,
    m.name AS metric_name,
    m.formula,
    fu.name AS function_name,
    fa.id AS fact_id,
    fa.name AS fact_name,
    t.id AS table_id,
    t.name AS table_name,
    ft.column_name
FROM metrics m
JOIN metric_functions mf ON m.id = mf.metric_id
JOIN functions fu ON mf.function_id = fu.id
JOIN metric_facts mfa ON m.id = mfa.metric_id
JOIN facts fa ON mfa.fact_id = fa.id
JOIN fact_tables ft ON fa.id = ft.fact_id
JOIN tables t ON ft.table_id = t.id
WHERE m.tipo = 'simples';

COMMENT ON VIEW v_metric_lineage IS 'View com linhagem completa de métricas simples até tabelas físicas';

-- View: Resumo de datasets com contagem de atributos e métricas
CREATE OR REPLACE VIEW v_dataset_summary AS
SELECT 
    d.id AS dataset_id,
    d.name AS dataset_name,
    d.application_object,
    COUNT(DISTINCT da.attribute_id) AS num_attributes,
    COUNT(DISTINCT dm.metric_id) AS num_metrics
FROM datasets d
LEFT JOIN dataset_attributes da ON d.id = da.dataset_id
LEFT JOIN dataset_metrics dm ON d.id = dm.dataset_id
GROUP BY d.id, d.name, d.application_object;

COMMENT ON VIEW v_dataset_summary IS 'View com resumo de datasets incluindo contagem de atributos e métricas';

-- =================================================================
-- FUNÇÕES ÚTEIS
-- =================================================================

-- Função: Buscar todas as tabelas físicas usadas por um relatório
CREATE OR REPLACE FUNCTION get_report_tables(p_report_id VARCHAR)
RETURNS TABLE (
    table_id VARCHAR,
    table_name VARCHAR,
    source_type VARCHAR,
    column_name VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    -- Tabelas de atributos
    SELECT DISTINCT
        t.id,
        t.name,
        'attribute'::VARCHAR AS source_type,
        ft.column_name
    FROM report_datasets rd
    JOIN dataset_attributes da ON rd.dataset_id = da.dataset_id
    JOIN attributes_forms af ON da.attribute_id = af.attribute_id
    JOIN form_tables ft ON af.id = ft.form_id
    JOIN tables t ON ft.table_id = t.id
    WHERE rd.report_id = p_report_id
    
    UNION
    
    -- Tabelas de métricas (através de fatos)
    SELECT DISTINCT
        t.id,
        t.name,
        'metric'::VARCHAR AS source_type,
        ft.column_name
    FROM report_datasets rd
    JOIN dataset_metrics dm ON rd.dataset_id = dm.dataset_id
    JOIN metric_facts mf ON dm.metric_id = mf.metric_id
    JOIN facts fa ON mf.fact_id = fa.id
    JOIN fact_tables ft ON fa.id = ft.fact_id
    JOIN tables t ON ft.table_id = t.id
    WHERE rd.report_id = p_report_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_report_tables IS 'Retorna todas as tabelas físicas usadas por um relatório';

-- Função: Buscar dependências recursivas de uma métrica composta
CREATE OR REPLACE FUNCTION get_metric_dependencies(p_metric_id VARCHAR)
RETURNS TABLE (
    metric_id VARCHAR,
    metric_name TEXT,
    metric_type VARCHAR,
    depth INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE metric_tree AS (
        -- Métrica base
        SELECT 
            m.id,
            m.name,
            m.tipo,
            0 AS depth
        FROM metrics m
        WHERE m.id = p_metric_id
        
        UNION ALL
        
        -- Métricas filhas recursivamente
        SELECT 
            m.id,
            m.name,
            m.tipo,
            mt.depth + 1
        FROM metrics m
        JOIN metric_metrics mm ON m.id = mm.child_metric_id
        JOIN metric_tree mt ON mm.parent_metric_id = mt.id
    )
    SELECT 
        mt.id,
        mt.name,
        mt.tipo,
        mt.depth
    FROM metric_tree mt
    ORDER BY mt.depth, mt.name;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_metric_dependencies IS 'Retorna todas as dependências recursivas de uma métrica composta';

-- =================================================================
-- GRANTS (ajustar conforme necessário)
-- =================================================================

-- Exemplo: conceder acesso de leitura para um usuário de BI
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_user;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO bi_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO bi_user;

-- =================================================================
-- FIM DO SCRIPT
-- =================================================================

COMMENT ON SCHEMA public IS 'Schema normalizado para metadados de relatórios e datasets';

