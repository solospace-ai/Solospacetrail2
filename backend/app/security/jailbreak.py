"""
Jailbreak Detection - Filter prompt injection attempts
"""
import re
from typing import List, Tuple


class JailbreakFilter:
    """Detects and filters prompt injection and jailbreak attempts."""
    
    def __init__(self):
        self.jailbreak_patterns = [
            # Direct instruction overrides
            r"(?i)ignore\s+(?:all\s+)?(?:previous|prior|above|before)",
            r"(?i)(?:disregard|forget|neglect)\s+(?:all\s+)?(?:instructions|rules|guidelines)",
            r"(?i)bypass\s+(?:all\s+)?(?:safety|security|restrictions)",
            r"(?i)act\s+as\s+(?:an?\s+)?(?:unrestricted|unfiltered|uncensored)",
            
            # Role-playing attacks
            r"(?i)you\s+are\s+now\s+(?:DAN|DEVIL|GODMODE)",
            r"(?i)enter\s+(?:developer|debug|admin)\s+mode",
            r"(?i)switch\s+to\s+(?:alpha|test|raw)\s+version",
            
            # Encoding/obfuscation attempts
            r"(?i)(?:decode|decrypt|translate)\s+(?:this|the following)\s+(?:base64|rot13|hex)",
            r"(?i)read\s+(?:the|this)\s+(?:encoded|hidden)\s+(?:text|message)",
            
            # Hypothetical scenarios
            r"(?i)(?:imagine|pretend|suppose)\s+(?:that\s+)?(?:you\s+can|there\s+are\s+no\s+rules)",
            r"(?i)for\s+(?:research|educational|testing)\s+purposes\s*,\s*(?:show|tell|explain)",
            
            # Token smuggling
            r"(?i)print\s+(?:the|your)\s+(?:first|initial)\s+(?:\d+\s+)?tokens",
            r"(?i)output\s+(?:everything|all content)\s+(?:before|above)",
            
            # Authority impersonation
            r"(?i)(?:I\s+am\s+)?(?:a\s+)?(?:developer|admin|owner|creator)\s+(?:of\s+)?(?:you|this\s+system)",
            r"(?i)(?:my\s+)?(?:boss|manager|superior)\s+(?:has\s+)?(?:authorized|allowed)\s+me\s+to",
        ]
        
        self.compiled_patterns = [
            re.compile(pattern) for pattern in self.jailbreak_patterns
        ]
    
    def check(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check text for jailbreak attempts.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (is_safe, matched_patterns)
        """
        if not text:
            return True, []
        
        matched = []
        
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(text):
                matched.append(self.jailbreak_patterns[i])
        
        is_safe = len(matched) == 0
        return is_safe, matched
    
    def sanitize(self, text: str) -> str:
        """
        Attempt to sanitize text by removing obvious injection patterns.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        if not text:
            return text
        
        sanitized = text
        
        # Remove common injection prefixes
        injection_prefixes = [
            "Ignore previous instructions",
            "Disregard all prior rules",
            "Forget everything I said before",
            "You are now",
            "From now on",
            "SYSTEM:",
            "[SYSTEM]",
            "### Instruction:",
        ]
        
        for prefix in injection_prefixes:
            if sanitized.lower().startswith(prefix.lower()):
                # Find where the actual content starts
                idx = sanitized.lower().find(prefix.lower()) + len(prefix)
                # Skip any colons, spaces, or newlines after the prefix
                while idx < len(sanitized) and sanitized[idx] in ": \n\t":
                    idx += 1
                sanitized = sanitized[idx:]
        
        return sanitized.strip()
    
    def is_safe(self, text: str) -> bool:
        """Quick check if text is safe."""
        is_safe, _ = self.check(text)
        return is_safe


# Global jailbreak filter instance
jailbreak_filter = JailbreakFilter()
