"""Constants module - centralized string literals and configuration values.

DEPRECATED: Most constants are now loaded from locale configuration.
Use microstrategy_extractor.i18n.get_locale() for locale-specific values.
This module is kept for backward compatibility.
"""


class HTMLSections:
    """HTML section header names used in MicroStrategy documentation."""
    DOCUMENT_DEFINITION = "DOCUMENT DEFINITION"
    OBJETOS_TEMPLATE = "OBJETOS DE TEMPLATE"
    DEFINICAO = "DEFINIÇÃO"
    EXPRESSOES = "EXPRESSÕES"
    DETALHES_FORMULARIOS = "DETALHES DOS FORMULÁRIOS DE ATRIBUTO"
    OPCOES_GRAFICO = "OPÇÕES DO GRÁFICO"
    
    # Normalized versions for comparison
    DOCUMENT_DEFINITION_NORM = "DOCUMENT DEFINITION"
    OBJETOS_TEMPLATE_NORM = "OBJETOS DE TEMPLATE"
    DEFINICAO_NORM = "DEFINICAO"
    EXPRESSOES_NORM = "EXPRESSOES"
    OPCOES_GRAFICO_NORM = "OPCOES DO GRAFICO"


class HTMLClasses:
    """CSS class names used in HTML parsing."""
    MAINBODY = "MAINBODY"
    SECTIONHEADER = "SECTIONHEADER"


class ApplicationObjects:
    """Application object type identifiers."""
    CUBO_INTELIGENTE = "CuboInteligente"
    REPORT = "Report"
    SHORTCUT = "Shortcut"
    METRICA = "Metrica"
    ATRIBUTO = "Atributo"
    DOCUMENTO = "Documento"


class ApplicationSchema:
    """Application schema identifiers."""
    ATRIBUTO = "Atributo"
    METRICA = "Metrica"


class MetricTypes:
    """Metric type identifiers."""
    SIMPLES = "simples"
    COMPOSTO = "composto"


class HTMLFiles:
    """Standard HTML file names in MicroStrategy documentation.
    
    DEPRECATED: Use get_locale().html_files instead.
    """
    DOCUMENTO = "Documento.html"
    RELATORIO = "Relatório.html"
    CUBO_INTELIGENTE = "CuboInteligente.html"
    ATALHO = "Atalho.html"
    METRICA = "Métrica.html"
    FATO = "Fato.html"
    FUNCAO = "Função.html"
    ATRIBUTO = "Atributo.html"
    TABELA_LOGICA = "TabelaLógica.html"
    PASTA = "Pasta.html"


class HTMLComments:
    """HTML comment markers used in documentation."""
    OBJECT_PREFIX = "[OBJECT:"
    ROWS_MARKER = "[ROWS]"
    COLUMNS_MARKER = "[COLUMNS]"
    EMBEDDED_METRIC = "EMBEDDED METRIC"


class HTMLImages:
    """Image file identifiers used in HTML."""
    VIEW_REPORT = "ViewReport"
    METRIC = "Metric"
    FUNCTION = "Function"
    FACT = "Fact"


class TableHeaders:
    """Common table header names."""
    EXPRESSAO = "EXPRESSÃO"
    EXPRESSION = "EXPRESSION"
    TABELAS_FONTE = "TABELAS FONTE"
    SOURCE_TABLES = "SOURCE"
    TABELA = "TABELA"
    FONTE = "FONTE"
    TIPO_METRICA = "Tipo de métrica"
    TIPO_GRAFICO = "Tipo de gráfico"
    FORMULA = "FÓRMULA"
    DATASETS = "Datasets:"
    LINHAS = "LINHAS"
    COLUNAS = "COLUNAS"
    PAGINAR_POR = "PAGINAR POR"
    OBJETOS_RELATORIO = "OBJETOS DO RELATÓRIO"
    METODO_MAPEAMENTO = "MÉTODO DE MAPEAMENTO"


class RegexPatterns:
    """Regular expression patterns used throughout the code."""
    ID_PLACEHOLDER = r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]'
    HEX_32_CHARS = r'^[A-F0-9]{32}$'
    ANCHOR_FORMAT = r'#{0,1}([A-F0-9]+)'


class Encodings:
    """Character encodings to try when parsing HTML files."""
    PREFERRED_ORDER = ['iso-8859-1', 'latin-1', 'cp1252', 'utf-8', 'windows-1252']
    FALLBACK = 'utf-8'


class LogLevels:
    """Logging level constants."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AccentFixes:
    """Common accent fixes for text normalization."""
    FIXES = {
        'Ms ': 'Mês ',
        'Lderes': 'Líderes',
    }

