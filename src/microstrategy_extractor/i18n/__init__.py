"""Internationalization support for MicroStrategy extractor."""

from typing import Optional, Dict
from .base import Locale
from .pt_br import PT_BR
from .en_us import EN_US

# Registry of available locales
_LOCALE_REGISTRY: Dict[str, Locale] = {
    "pt-BR": PT_BR,
    "pt_BR": PT_BR,  # Alternative format
    "pt": PT_BR,     # Short form
    "en-US": EN_US,
    "en_US": EN_US,  # Alternative format
    "en": EN_US,     # Short form
}

# Current active locale (default to Portuguese/Brazilian)
_current_locale: Locale = PT_BR


def get_locale() -> Locale:
    """
    Get the current active locale.
    
    Returns:
        Current Locale instance
    """
    return _current_locale


def set_locale(locale: Locale) -> None:
    """
    Set the current locale using a Locale instance.
    
    Args:
        locale: Locale instance to set as current
    """
    global _current_locale
    _current_locale = locale


def set_locale_by_code(code: str) -> None:
    """
    Set the current locale by locale code.
    
    Args:
        code: Locale code (e.g., 'pt-BR', 'en-US')
        
    Raises:
        ValueError: If locale code is not found in registry
    """
    global _current_locale
    
    if code not in _LOCALE_REGISTRY:
        available = ", ".join(_LOCALE_REGISTRY.keys())
        raise ValueError(f"Unknown locale code: '{code}'. Available locales: {available}")
    
    _current_locale = _LOCALE_REGISTRY[code]


def register_locale(locale: Locale) -> None:
    """
    Register a custom locale in the registry.
    
    This allows users to add their own locale configurations.
    
    Args:
        locale: Locale instance to register
    """
    _LOCALE_REGISTRY[locale.code] = locale


def get_available_locales() -> list[str]:
    """
    Get list of available locale codes.
    
    Returns:
        List of registered locale codes
    """
    return list(set(_LOCALE_REGISTRY.values()))


def get_locale_codes() -> list[str]:
    """
    Get list of all registered locale code variants.
    
    Returns:
        List of all locale code keys in registry
    """
    return list(_LOCALE_REGISTRY.keys())


# Re-export base classes for convenience
from .base import (
    HTMLFileNames,
    SectionHeaders,
    TableHeaders,
    HTMLComments,
    HTMLImages,
)

__all__ = [
    "Locale",
    "HTMLFileNames",
    "SectionHeaders",
    "TableHeaders",
    "HTMLComments",
    "HTMLImages",
    "get_locale",
    "set_locale",
    "set_locale_by_code",
    "register_locale",
    "get_available_locales",
    "get_locale_codes",
    "PT_BR",
    "EN_US",
]

