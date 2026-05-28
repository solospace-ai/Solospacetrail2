"""
Synthesizer - Aggregates agent outputs into cohesive final responses
"""
import json
from typing import Dict, Any, List, AsyncGenerator
from app.services.llm_gateway import gateway


SYNTHESIZER_PROMPT = """You are a synthesis engine that combines multiple agent outputs into a cohesive, well-structured response.

Agent outputs to synthesize:
{agent_outputs}

User's original query: {user_query}

Create a comprehensive, well-organized response that:
1. Directly addresses the user's query
2. Integrates insights from all agents
3. Resolves any contradictions between agents
4. Provides clear actionable information
5. Uses appropriate formatting (headings, lists, code blocks as needed)

Respond in a natural, helpful tone. Do not mention the agents or the synthesis process."""


class Synthesizer:
    """Aggregates and synthesizes outputs from multiple agents."""
    
    async def synthesize(
        self,
        agent_outputs: Dict[str, str],
        user_query: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Synthesize multiple agent outputs into a cohesive response.
        
        Args:
            agent_outputs: Dict mapping agent names to their outputs
            user_query: Original user query
            
        Yields:
            Streaming chunks of the synthesized response
        """
        # Format agent outputs
        formatted_outputs = []
        for agent_name, output in agent_outputs.items():
            formatted_outputs.append(f"### {agent_name}:\n{output}")
        
        prompt = SYNTHESIZER_PROMPT.format(
            agent_outputs="\n\n".join(formatted_outputs),
            user_query=user_query
        )
        
        messages = [
            {"role": "system", "content": "You are a synthesis engine. Create cohesive responses from multiple sources."},
            {"role": "user", "content": prompt}
        ]
        
        async for chunk in gateway.chat_completion(
            messages=messages,
            model="gpt-4o-mini",
            provider="openai",
            temperature=0.7,
            max_tokens=4096,
            stream=True
        ):
            if "choices" in chunk and len(chunk["choices"]) > 0:
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield {
                        "type": "synthesis_chunk",
                        "content": content
                    }
        
        yield {
            "type": "synthesis_complete"
        }
    
    async def summarize_context(self, conversation_history: List[Dict[str, str]]) -> str:
        """
        Summarize long conversation history to save tokens.
        
        Args:
            conversation_history: List of message dicts
            
        Returns:
            Summary string
        """
        if len(conversation_history) <= 6:
            return ""
        
        summary_prompt = """Summarize the following conversation history in 2-3 sentences, capturing key points and decisions made:

{history}

Summary:"""
        
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in conversation_history[-10:]  # Last 10 messages
        ])
        
        messages = [
            {"role": "user", "content": summary_prompt.format(history=history_text)}
        ]
        
        full_summary = ""
        async for chunk in gateway.chat_completion(
            messages=messages,
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
        
        return full_summary


# Global synthesizer instance
synthesizer = Synthesizer()
