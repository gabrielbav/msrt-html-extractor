"""Portuguese (Brazil) locale configuration for MicroStrategy documentation."""

from .base import Locale, HTMLFileNames, SectionHeaders, TableHeaders, HTMLComments, HTMLImages


PT_BR = Locale(
    code="pt-BR",
    name="Portuguese (Brazil)",
    html_files=HTMLFileNames(
        documento="Documento.html",
        relatorio="Relatório.html",
        cubo_inteligente="CuboInteligente.html",
        atalho="Atalho.html",
        metrica="Métrica.html",
        fato="Fato.html",
        funcao="Função.html",
        atributo="Atributo.html",
        tabela_logica="TabelaLógica.html",
        pasta="Pasta.html",
    ),
    section_headers=SectionHeaders(
        document_definition="DOCUMENT DEFINITION",
        objetos_template="OBJETOS DE TEMPLATE",
        definicao="DEFINIÇÃO",
        expressoes="EXPRESSÕES",
        detalhes_formularios="DETALHES DOS FORMULÁRIOS DE ATRIBUTO",
        opcoes_grafico="OPÇÕES DO GRÁFICO",
        # Normalized versions
        definicao_norm="DEFINICAO",
        expressoes_norm="EXPRESSOES",
        objetos_template_norm="OBJETOS DE TEMPLATE",
        opcoes_grafico_norm="OPCOES DO GRAFICO",
    ),
    table_headers=TableHeaders(
        expressao="EXPRESSÃO",
        expression="EXPRESSION",
        tabelas_fonte="TABELAS FONTE",
        source_tables="SOURCE",
        tabela="TABELA",
        fonte="FONTE",
        tipo_metrica="Tipo de métrica",
        tipo_grafico="Tipo de gráfico",
        formula="FÓRMULA",
        datasets="Datasets:",
        linhas="LINHAS",
        colunas="COLUNAS",
        paginar_por="PAGINAR POR",
        objetos_relatorio="OBJETOS DO RELATÓRIO",
        metodo_mapeamento="MÉTODO DE MAPEAMENTO",
        proprietario="Proprietário",
        controle_acesso="Controle de Acesso",
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

