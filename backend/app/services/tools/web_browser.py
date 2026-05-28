"""
Web Browser Tool - Fetch and parse web pages with SSRF protection
"""
import httpx
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from app.config import settings


class WebBrowserTool:
    """Web browser tool for fetching and parsing web pages."""
    
    name = "web_browser"
    description = "Fetch and extract text content from a web page URL"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.allowed_schemes = {"http", "https"}
    
    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is safe to fetch (SSRF protection)."""
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in self.allowed_schemes:
                return False
            
            # Block private IP ranges
            hostname = parsed.hostname
            if not hostname:
                return False
            
            # Block localhost and private networks
            if hostname in ("localhost", "127.0.0.1", "::1"):
                return False
            
            if hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("172."):
                return False
            
            # Block internal domains
            if hostname.endswith(".internal") or hostname.endswith(".local"):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def execute(
        self,
        url: str,
        extract_links: bool = False,
        max_length: int = 10000
    ) -> Dict[str, Any]:
        """
        Fetch and parse a web page.
        
        Args:
            url: URL to fetch
            extract_links: Whether to extract links from the page
            max_length: Maximum characters of text to return
            
        Returns:
            Dict with page content and metadata
        """
        # SSRF check
        if not self._is_safe_url(url):
            return {
                "success": False,
                "error": "URL blocked for security reasons (SSRF protection)",
                "url": url
            }
        
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                follow_redirects=True,
                timeout=30.0
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Remove script and style elements
                for element in soup(["script", "style", "meta", "link", "noscript"]):
                    element.decompose()
                
                # Extract title
                title = ""
                if soup.title:
                    title = soup.title.string or ""
                
                # Extract main text content
                text_content = soup.get_text(separator='\n', strip=True)
                
                # Truncate if needed
                if len(text_content) > max_length:
                    text_content = text_content[:max_length] + "\n\n[Content truncated...]"
                
                result = {
                    "success": True,
                    "url": url,
                    "title": title,
                    "content": text_content,
                    "status_code": response.status_code,
                    "content_length": len(text_content)
                }
                
                # Extract links if requested
                if extract_links:
                    links = []
                    for link in soup.find_all('a', href=True)[:50]:
                        links.append({
                            "text": link.get_text(strip=True),
                            "href": link['href']
                        })
                    result["links"] = links
                
                return result
                
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code}",
                "url": url
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
                "url": {
                    "type": "string",
                    "description": "The URL to fetch"
                },
                "extract_links": {
                    "type": "boolean",
                    "description": "Whether to extract links from the page",
                    "default": False
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum characters to return",
                    "default": 10000
                }
            },
            "required": ["url"]
        }
