"""Text normalization utilities for handling encoding issues and text comparison."""

import unicodedata
from typing import Optional
from constants import AccentFixes


class TextNormalizer:
    """Unified text normalization for HTML parsing and comparison."""
    
    @staticmethod
    def for_comparison(text: str) -> str:
        """
        Normalize text for comparison, handling encoding issues.
        
        Removes accents and normalizes unicode to handle encoding problems
        in HTML files (e.g., 'EXPRESSÃO' vs 'EXPRESSÃ\\x83O').
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text (no accents, uppercase)
        """
        if not text:
            return ''
        # Normalize unicode and remove accents for comparison
        normalized = unicodedata.normalize('NFKD', text)
        # Remove combining characters (accents)
        ascii_text = ''.join(c for c in normalized if not unicodedata.combining(c))
        return ascii_text.upper()
    
    @staticmethod
    def normalize_unicode(text: str) -> str:
        """
        Normalize unicode representation without removing accents.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized unicode text
        """
        if not text:
            return ''
        return unicodedata.normalize('NFKD', text)
    
    @staticmethod
    def remove_accents(text: str) -> str:
        """
        Remove accents from text while preserving case.
        
        Args:
            text: Text with potential accents
            
        Returns:
            Text without accents
        """
        if not text:
            return ''
        normalized = unicodedata.normalize('NFKD', text)
        return ''.join(c for c in normalized if not unicodedata.combining(c))
    
    @staticmethod
    def normalize_for_matching(text: str) -> str:
        """
        Normalize text for fuzzy matching (lowercase, no accents, stripped).
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text for matching
        """
        if not text:
            return ''
        # Normalize unicode
        normalized = unicodedata.normalize('NFKD', text)
        # Remove combining characters (accents)
        no_accents = ''.join(c for c in normalized if not unicodedata.combining(c))
        # Lowercase and strip
        return no_accents.lower().strip()
    
    @staticmethod
    def fix_common_accents(text: str) -> str:
        """
        Fix common accent issues in text due to HTML encoding problems.
        
        Note: This is a minimal fallback. The correct approach is to use the name
        directly from the HTML file (Atributo.html, Métrica.html) which already
        has the correct encoding.
        
        Args:
            text: Text with potential encoding issues
            
        Returns:
            Text with common fixes applied
        """
        if not text:
            return ''
        
        result = text
        for wrong, correct in AccentFixes.FIXES.items():
            result = result.replace(wrong, correct)
        
        return result
    
    @classmethod
    def compare_texts(cls, text1: str, text2: str, 
                     case_sensitive: bool = False,
                     accent_sensitive: bool = False) -> bool:
        """
        Compare two texts with configurable sensitivity.
        
        Args:
            text1: First text
            text2: Second text
            case_sensitive: Whether to consider case differences
            accent_sensitive: Whether to consider accent differences
            
        Returns:
            True if texts match according to sensitivity settings
        """
        if not text1 or not text2:
            return text1 == text2
        
        # Apply normalizations based on sensitivity
        if not accent_sensitive:
            text1 = cls.remove_accents(text1)
            text2 = cls.remove_accents(text2)
        
        if not case_sensitive:
            text1 = text1.lower()
            text2 = text2.lower()
        
        return text1.strip() == text2.strip()
    
    @classmethod
    def find_best_match(cls, target: str, candidates: list[str], 
                       threshold: float = 0.8) -> Optional[str]:
        """
        Find the best matching string from candidates.
        
        Args:
            target: String to match
            candidates: List of candidate strings
            threshold: Minimum similarity threshold (0-1)
            
        Returns:
            Best matching candidate or None if no good match
        """
        if not target or not candidates:
            return None
        
        target_norm = cls.normalize_for_matching(target)
        target_words = set(target_norm.split())
        
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            candidate_norm = cls.normalize_for_matching(candidate)
            
            # Exact match
            if target_norm == candidate_norm:
                return candidate
            
            # Check if target is contained in candidate
            if target_norm in candidate_norm:
                score = len(target_norm) / len(candidate_norm)
                # Bonus for starting with target
                if candidate_norm.startswith(target_norm):
                    score += 0.5
            else:
                # Word-based similarity
                candidate_words = set(candidate_norm.split())
                common_words = target_words.intersection(candidate_words)
                if not common_words:
                    continue
                score = len(common_words) / max(len(target_words), len(candidate_words))
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate
        
        return best_match


# Convenience functions for backward compatibility
def normalize_for_comparison(text: str) -> str:
    """Convenience wrapper for TextNormalizer.for_comparison()."""
    return TextNormalizer.for_comparison(text)


def fix_common_accents(text: str) -> str:
    """Convenience wrapper for TextNormalizer.fix_common_accents()."""
    return TextNormalizer.fix_common_accents(text)

