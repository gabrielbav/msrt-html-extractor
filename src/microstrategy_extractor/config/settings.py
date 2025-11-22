"""Configuration management for the MicroStrategy extractor."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from microstrategy_extractor.core.constants import LogLevels


@dataclass
class Config:
    """Central configuration for the extractor application."""
    
    # Input paths
    base_path: Path
    
    # Output paths
    output_json_path: Optional[Path] = None
    
    # Cache settings
    cache_enabled: bool = True
    cache_size_limit: int = 1000  # Maximum items in cache
    
    # Logging settings
    log_level: str = LogLevels.INFO
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_date_format: str = '%Y-%m-%d %H:%M:%S'
    verbose: bool = False
    
    # Performance settings
    parallel_enabled: bool = False
    max_workers: int = 4
    
    # HTML file names (for override if needed)
    html_files: dict = field(default_factory=lambda: {
        'documento': 'Documento.html',
        'relatorio': 'Relatório.html',
        'cubo_inteligente': 'CuboInteligente.html',
        'atalho': 'Atalho.html',
        'metrica': 'Métrica.html',
        'fato': 'Fato.html',
        'funcao': 'Função.html',
        'atributo': 'Atributo.html',
        'tabela_logica': 'TabelaLógica.html',
    })
    
    @classmethod
    def from_env(cls) -> 'Config':
        """
        Create configuration from environment variables.
        
        Returns:
            Config instance with values from environment
        """
        return cls(
            base_path=Path(os.getenv("BASE_PATH", "RAW_DATA")),
            output_json_path=Path(os.getenv("OUTPUT_JSON", "output.json")) if os.getenv("OUTPUT_JSON") else None,
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            cache_size_limit=int(os.getenv("CACHE_SIZE_LIMIT", "1000")),
            log_level=os.getenv("LOG_LEVEL", LogLevels.INFO),
            verbose=os.getenv("VERBOSE", "false").lower() == "true",
            parallel_enabled=os.getenv("PARALLEL_ENABLED", "false").lower() == "true",
            max_workers=int(os.getenv("MAX_WORKERS", "4")),
        )
    
    @classmethod
    def from_args(cls, args) -> 'Config':
        """
        Create configuration from command-line arguments.
        
        Args:
            args: Parsed argument namespace from argparse
            
        Returns:
            Config instance with values from arguments
        """
        return cls(
            base_path=Path(args.base_path),
            output_json_path=Path(args.output_json) if hasattr(args, 'output_json') and args.output_json else None,
            verbose=getattr(args, 'verbose', False),
            log_level=LogLevels.DEBUG if getattr(args, 'verbose', False) else LogLevels.INFO,
        )
    
    def get_html_file_path(self, file_key: str) -> Path:
        """
        Get full path to an HTML file.
        
        Args:
            file_key: Key in html_files dict (e.g., 'documento', 'metrica')
            
        Returns:
            Full path to the HTML file
        """
        filename = self.html_files.get(file_key)
        if not filename:
            raise ValueError(f"Unknown HTML file key: {file_key}")
        return self.base_path / filename
    
    def validate(self) -> list[str]:
        """
        Validate configuration settings.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.base_path:
            errors.append("base_path is required")
        elif not self.base_path.exists():
            errors.append(f"base_path does not exist: {self.base_path}")
        elif not self.base_path.is_dir():
            errors.append(f"base_path is not a directory: {self.base_path}")
        
        # Check if Documento.html exists
        documento_path = self.get_html_file_path('documento')
        if not documento_path.exists():
            errors.append(f"Documento.html not found in: {self.base_path}")
        
        if self.cache_size_limit < 1:
            errors.append("cache_size_limit must be positive")
        
        if self.max_workers < 1:
            errors.append("max_workers must be positive")
        
        if self.log_level not in [LogLevels.DEBUG, LogLevels.INFO, LogLevels.WARNING, LogLevels.ERROR, LogLevels.CRITICAL]:
            errors.append(f"Invalid log_level: {self.log_level}")
        
        return errors


# Default configuration for backward compatibility
def get_default_config(base_path: Path) -> Config:
    """
    Get default configuration with specified base path.
    
    Args:
        base_path: Base path for HTML files
        
    Returns:
        Config instance with defaults
    """
    return Config(base_path=base_path)

