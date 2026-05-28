"""
Web Search Tool - DuckDuckGo HTML search
"""
import httpx
from typing import Dict, Any, List
from bs4 import BeautifulSoup


class WebSearchTool:
    """Web search tool using DuckDuckGo HTML interface."""
    
    name = "web_search"
    description = "Search the web for current information using DuckDuckGo"
    
    def __init__(self):
        self.base_url = "https://html.duckduckgo.com/html/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    async def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Execute a web search.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            Dict with search results
        """
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                response = await client.post(
                    self.base_url,
                    data={"q": query},
                    timeout=30.0
                )
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')
                results = []
                
                for result in soup.select('.result')[:max_results]:
                    title_elem = result.select_one('.result__title')
                    snippet_elem = result.select_one('.result__snippet')
                    url_elem = result.select_one('.result__url')
                    
                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True)
                        url = url_elem.get('href', '') if url_elem else ''
                        
                        # Clean up DuckDuckGo redirect URLs
                        if url.startswith('//'):
                            url = 'https:' + url
                        
                        results.append({
                            "title": title,
                            "snippet": snippet,
                            "url": url
                        })
                
                return {
                    "success": True,
                    "query": query,
                    "results": results,
                    "count": len(results)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the tool's input schema."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
