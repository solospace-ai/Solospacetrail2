"""
SSRF Guard - Server-Side Request Forgery protection
"""
import socket
import ipaddress
from urllib.parse import urlparse
from typing import List, Set


class SSRFGuard:
    """Protects against Server-Side Request Forgery attacks."""
    
    def __init__(self, allowed_hosts: Set[str] = None):
        self.allowed_hosts = allowed_hosts or set()
        self.blocked_ip_ranges = [
            ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
            ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
            ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
            ipaddress.ip_network("127.0.0.0/8"),      # Loopback
            ipaddress.ip_network("169.254.0.0/16"),   # Link-local
            ipaddress.ip_network("0.0.0.0/8"),        # Current network
            ipaddress.ip_network("224.0.0.0/4"),      # Multicast
            ipaddress.ip_network("240.0.0.0/4"),      # Reserved
        ]
        self.blocked_domains = {
            "metadata.google.internal",
            "metadata.azure.com",
            "169.254.169.254",  # Cloud metadata endpoint
        }
    
    def is_safe_url(self, url: str) -> bool:
        """
        Check if a URL is safe to request.
        
        Args:
            url: URL to validate
            
        Returns:
            True if safe, False otherwise
        """
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ("http", "https"):
                return False
            
            hostname = parsed.hostname
            if not hostname:
                return False
            
            # Check if explicitly allowed
            if hostname in self.allowed_hosts:
                return True
            
            # Check blocked domains
            if hostname in self.blocked_domains:
                return False
            
            # Check for internal domain patterns
            if self._is_internal_domain(hostname):
                return False
            
            # Resolve and check IP addresses
            return self._check_ip_addresses(hostname)
            
        except Exception:
            return False
    
    def _is_internal_domain(self, hostname: str) -> bool:
        """Check if hostname matches internal domain patterns."""
        internal_patterns = [
            ".internal",
            ".local",
            ".lan",
            ".private",
            ".corp",
            ".intranet"
        ]
        
        hostname_lower = hostname.lower()
        return any(hostname_lower.endswith(pattern) for pattern in internal_patterns)
    
    def _check_ip_addresses(self, hostname: str) -> bool:
        """Resolve hostname and check if any IPs are blocked."""
        try:
            # Get all IP addresses for the hostname
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
            
            for info in addr_info:
                ip_str = info[4][0]
                
                try:
                    ip = ipaddress.ip_address(ip_str)
                    
                    # Check if IP is in blocked ranges
                    for blocked_range in self.blocked_ip_ranges:
                        if ip in blocked_range:
                            return False
                    
                    # Check if it's a private/reserved IP
                    if ip.is_private or ip.is_reserved or ip.is_loopback:
                        return False
                        
                except ValueError:
                    continue
            
            return True
            
        except socket.gaierror:
            # DNS resolution failed - be conservative and block
            return False
        except Exception:
            return False
    
    def validate_urls(self, urls: List[str]) -> List[str]:
        """
        Validate multiple URLs and return only safe ones.
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            List of safe URLs
        """
        return [url for url in urls if self.is_safe_url(url)]


# Global SSRF guard instance with default allowed hosts
ssrf_guard = SSRFGuard()
