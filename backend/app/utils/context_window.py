"""
Context window management - Smart summarization for long conversations
"""
from typing import List, Dict, Any
from app.services.llm_gateway import gateway


class ContextWindowManager:
    """Manages context windows with smart summarization."""
    
    def __init__(self, max_turns: int = 6):
        self.max_turns = max_turns
    
    async def summarize_if_needed(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """
        Summarize conversation if it exceeds max turns.
        
        Args:
            messages: Conversation history
            system_prompt: System prompt to preserve
            
        Returns:
            Potentially summarized message list
        """
        # Count user/assistant turns (excluding system)
        turns = sum(1 for m in messages if m["role"] in ("user", "assistant"))
        
        if turns <= self.max_turns:
            return messages
        
        # Need to summarize - keep system prompt and recent turns
        recent_messages = messages[-self.max_turns:]
        
        # Summarize older messages
        old_messages = messages[1:self.max_turns * -1]  # Exclude system and recent
        
        if old_messages:
            summary = await self._summarize_messages(old_messages)
            
            # Create new message list with summary
            new_messages = [messages[0]]  # System prompt
            new_messages.append({
                "role": "system",
                "content": f"[Conversation Summary]\n{summary}"
            })
            new_messages.extend(recent_messages)
            
            return new_messages
        
        return messages
    
    async def _summarize_messages(self, messages: List[Dict[str, str]]) -> str:
        """Summarize a list of messages."""
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in messages
        ])
        
        prompt = f"""Summarize the following conversation history in 2-3 sentences, capturing key information, decisions, and conclusions:

{history_text}

Summary:"""
        
        full_summary = ""
        async for chunk in gateway.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            provider="openai",
            temperature=0.3,
            max_tokens=500,
            stream=True
        ):
            if "choices" in chunk and len(chunk["choices"]) > 0:
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    full_summary += content
        
        return full_summary.strip()
    
    def truncate_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 8000
    ) -> List[Dict[str, str]]:
        """
        Truncate messages to fit within token limit.
        
        Simple approach: remove oldest messages first.
        
        Args:
            messages: Message list
            max_tokens: Maximum tokens allowed
            
        Returns:
            Truncated message list
        """
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        total_chars = sum(len(m["content"]) for m in messages)
        
        if total_chars <= max_chars:
            return messages
        
        # Remove oldest non-system messages first
        result = [m for m in messages if m["role"] == "system"]
        non_system = [m for m in messages if m["role"] != "system"]
        
        # Add from newest to oldest until we hit limit
        current_chars = sum(len(m["content"]) for m in result)
        
        for msg in reversed(non_system):
            msg_chars = len(msg["content"])
            if current_chars + msg_chars <= max_chars:
                result.insert(len(result) - sum(1 for m in result if m["role"] == "system"), msg)
                current_chars += msg_chars
            else:
                break
        
        return result


# Global context manager instance
context_manager = ContextWindowManager()
