"""
Memory Tool - Vector-based cross-session memory using ChromaDB
"""
import hashlib
from typing import Dict, Any, List, Optional
from app.database import get_chroma_collection


class MemoryTool:
    """Vector-based memory tool for cross-session recall."""
    
    name = "memory"
    description = "Store and retrieve information across sessions using vector embeddings"
    
    def __init__(self, collection_name: str = "agent_memory"):
        self.collection_name = collection_name
    
    def _get_collection(self):
        """Get the ChromaDB collection."""
        return get_chroma_collection(self.collection_name)
    
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store content in memory with vector embedding.
        
        Args:
            content: Text content to store
            metadata: Optional metadata dict
            session_id: Optional session ID for filtering
            
        Returns:
            Dict with storage result
        """
        try:
            collection = self._get_collection()
            
            # Generate unique ID from content hash
            doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
            
            # Prepare metadata
            doc_metadata = metadata or {}
            if session_id:
                doc_metadata["session_id"] = session_id
            
            # Add to collection (ChromaDB handles embeddings automatically)
            collection.add(
                documents=[content],
                metadatas=[doc_metadata],
                ids=[doc_id]
            )
            
            return {
                "success": True,
                "id": doc_id,
                "content_length": len(content),
                "metadata": doc_metadata
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search(
        self,
        query: str,
        n_results: int = 5,
        session_id: Optional[str] = None,
        min_similarity: float = 0.7
    ) -> Dict[str, Any]:
        """
        Search memory for relevant content.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            session_id: Optional session ID filter
            min_similarity: Minimum similarity threshold
            
        Returns:
            Dict with search results
        """
        try:
            collection = self._get_collection()
            
            # Build where clause for filtering
            where_clause = None
            if session_id:
                where_clause = {"session_id": session_id}
            
            # Query collection
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            
            if results and results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    distance = results["distances"][0][i] if results.get("distances") else None
                    similarity = 1 - distance if distance is not None else None
                    
                    # Skip low similarity results
                    if similarity is not None and similarity < min_similarity:
                        continue
                    
                    formatted_results.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "similarity": similarity
                    })
            
            return {
                "success": True,
                "query": query,
                "results": formatted_results,
                "count": len(formatted_results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    async def delete(self, doc_id: str) -> Dict[str, Any]:
        """Delete a document from memory by ID."""
        try:
            collection = self._get_collection()
            collection.delete(ids=[doc_id])
            
            return {
                "success": True,
                "deleted_id": doc_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def clear(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Clear memory, optionally filtered by session."""
        try:
            collection = self._get_collection()
            
            if session_id:
                # Delete only documents from this session
                results = collection.get(where={"session_id": session_id})
                if results and results.get("ids"):
                    collection.delete(ids=results["ids"])
            else:
                # Clear all
                collection.delete(where={})
            
            return {
                "success": True,
                "session_filter": session_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the tool's input schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["store", "search", "delete", "clear"]
                },
                "content": {
                    "type": "string",
                    "description": "Content to store (for 'store' action)"
                },
                "query": {
                    "type": "string",
                    "description": "Search query (for 'search' action)"
                },
                "doc_id": {
                    "type": "string",
                    "description": "Document ID (for 'delete' action)"
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of results (for 'search' action)",
                    "default": 5
                },
                "session_id": {
                    "type": "string",
                    "description": "Optional session ID filter"
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata for stored content"
                }
            },
            "required": ["action"]
        }
