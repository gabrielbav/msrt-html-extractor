"""Base locale structure for internationalization support."""

from dataclasses import dataclass


@dataclass
class HTMLFileNames:
    """HTML file names used in MicroStrategy documentation."""
    documento: str
    relatorio: str
    cubo_inteligente: str
    atalho: str
    metrica: str
    fato: str
    funcao: str
    atributo: str
    tabela_logica: str
    pasta: str


@dataclass
class SectionHeaders:
    """HTML section header names used in MicroStrategy documentation."""
    document_definition: str
    objetos_template: str
    definicao: str
    expressoes: str
    detalhes_formularios: str
    opcoes_grafico: str
    
    # Normalized versions (without accents) for comparison
    definicao_norm: str
    expressoes_norm: str
    objetos_template_norm: str
    opcoes_grafico_norm: str


@dataclass
class TableHeaders:
    """Common table header names used in MicroStrategy documentation."""
    expressao: str
    expression: str  # Alternative name
    tabelas_fonte: str
    source_tables: str  # Alternative name
    tabela: str
    fonte: str
    tipo_metrica: str
    tipo_grafico: str
    formula: str
    datasets: str
    linhas: str
    colunas: str
    paginar_por: str
    objetos_relatorio: str
    metodo_mapeamento: str
    proprietario: str
    controle_acesso: str


@dataclass
class HTMLComments:
    """HTML comment markers used in documentation."""
    object_prefix: str
    rows_marker: str
    columns_marker: str
    embedded_metric: str


@dataclass
class HTMLImages:
    """Image file identifiers used in HTML."""
    view_report: str
    metric: str
    function: str
    fact: str


@dataclass
class Locale:
    """Complete locale configuration for MicroStrategy documentation parsing."""
    code: str
    name: str
    html_files: HTMLFileNames
    section_headers: SectionHeaders
    table_headers: TableHeaders
    html_comments: HTMLComments
    html_images: HTMLImages

