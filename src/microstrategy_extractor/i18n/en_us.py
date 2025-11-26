"""English (United States) locale configuration for MicroStrategy documentation."""

from .base import Locale, HTMLFileNames, SectionHeaders, TableHeaders, HTMLComments, HTMLImages


EN_US = Locale(
    code="en-US",
    name="English (United States)",
    html_files=HTMLFileNames(
        documento="Document.html",
        relatorio="Report.html",
        cubo_inteligente="IntelligentCube.html",
        atalho="Shortcut.html",
        metrica="Metric.html",
        fato="Fact.html",
        funcao="Function.html",
        atributo="Attribute.html",
        tabela_logica="LogicalTable.html",
        pasta="Folder.html",
    ),
    section_headers=SectionHeaders(
        document_definition="DOCUMENT DEFINITION",
        objetos_template="TEMPLATE OBJECTS",
        definicao="DEFINITION",
        expressoes="EXPRESSIONS",
        detalhes_formularios="ATTRIBUTE FORM DETAILS",
        opcoes_grafico="CHART OPTIONS",
        # Normalized versions
        definicao_norm="DEFINITION",
        expressoes_norm="EXPRESSIONS",
        objetos_template_norm="TEMPLATE OBJECTS",
        opcoes_grafico_norm="CHART OPTIONS",
    ),
    table_headers=TableHeaders(
        expressao="EXPRESSION",
        expression="EXPRESSION",
        tabelas_fonte="SOURCE TABLES",
        source_tables="SOURCE",
        tabela="TABLE",
        fonte="SOURCE",
        tipo_metrica="Metric Type",
        tipo_grafico="Chart Type",
        formula="FORMULA",
        datasets="Datasets:",
        linhas="ROWS",
        colunas="COLUMNS",
        paginar_por="PAGE BY",
        objetos_relatorio="REPORT OBJECTS",
        metodo_mapeamento="MAPPING METHOD",
        proprietario="Owner",
        controle_acesso="Access Control",
    ),
    html_comments=HTMLComments(
        object_prefix="[OBJECT:",
        rows_marker="[ROWS]",
        columns_marker="[COLUMNS]",
        embedded_metric="EMBEDDED METRIC",
    ),
    html_images=HTMLImages(
        view_report="ViewReport",
        metric="Metric",
        function="Function",
        fact="Fact",
    ),
)

