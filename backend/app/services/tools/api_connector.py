"""
API Connector Tool - HTTP API calls with SSRF protection
"""
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlparse


class APIConnectorTool:
    """HTTP API connector tool for making GET/POST requests."""
    
    name = "api_connector"
    description = "Make HTTP requests to external APIs (GET/POST)"
    
    def __init__(self):
        self.allowed_schemes = {"http", "https"}
        self.blocked_hosts = {
            "localhost", "127.0.0.1", "::1",
            "metadata.google.internal",
            "169.254.169.254"  # Cloud metadata
        }
    
    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is safe to call (SSRF protection)."""
        try:
            parsed = urlparse(url)
            
            if parsed.scheme not in self.allowed_schemes:
                return False
            
            hostname = parsed.hostname
            if not hostname:
                return False
            
            if hostname in self.blocked_hosts:
                return False
            
            if hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("172."):
                return False
            
            if hostname.endswith(".internal") or hostname.endswith(".local"):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def execute(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Make an HTTP request.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            url: Target URL
            headers: Optional HTTP headers
            json_payload: Optional JSON payload for POST/PUT/PATCH
            params: Optional query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Dict with response data
        """
        # SSRF check
        if not self._is_safe_url(url):
            return {
                "success": False,
                "error": "URL blocked for security reasons (SSRF protection)",
                "url": url
            }
        
        # Validate method
        method = method.upper()
        if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            return {
                "success": False,
                "error": f"Unsupported HTTP method: {method}",
                "url": url
            }
        
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                kwargs = {
                    "params": params,
                    "headers": headers or {}
                }
                
                if json_payload and method in ("POST", "PUT", "PATCH"):
                    kwargs["json"] = json_payload
                
                response = await client.request(method, url, **kwargs)
                
                return {
                    "success": True,
                    "url": url,
                    "method": method,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text,
                    "content_length": len(response.content)
                }
                
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code}",
                "url": url,
                "status_code": e.response.status_code
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": f"Request error: {str(e)}",
                "url": url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the tool's input schema."""
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
                },
                "url": {
                    "type": "string",
                    "description": "Target URL"
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers",
                    "additionalProperties": {"type": "string"}
                },
                "json_payload": {
                    "type": "object",
                    "description": "Optional JSON payload for POST/PUT/PATCH"
                },
                "params": {
                    "type": "object",
                    "description": "Optional query parameters",
                    "additionalProperties": {"type": "string"}
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                    "default": 30
                }
            },
            "required": ["method", "url"]
        }
