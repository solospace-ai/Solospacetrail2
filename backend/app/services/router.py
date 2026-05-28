"""
Smart Auto-Mode Router - Classifies queries and suggests agent teams
"""
import json
from typing import List, Optional, Dict, Any
from app.models import RouteType, RouterRequest, RouterResponse, AgentCreate, ToolConfig
from app.services.llm_gateway import gateway
from app.config import settings


ROUTER_PROMPT = """You are a query classifier for a multi-agent AI system. Analyze the user's request and classify it into one of three categories:

1. TRIVIAL - Simple greetings, facts, translations, basic questions that can be answered directly
2. TOOL_USE - Requests that need a single tool operation (web search, code execution, API call)
3. COMPLEX - Multi-step reasoning, multiple domains, requiring coordination of specialized agents

For COMPLEX requests, suggest a team of 3-5 specialized agents with distinct roles.

Respond in JSON format:
{
    "route_type": "TRIVIAL" | "TOOL_USE" | "COMPLEX",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of classification",
    "suggested_agents": [
        {
            "name": "agent_name",
            "icon": "emoji",
            "system_prompt": "Detailed system prompt for this agent",
            "objective": "Clear objective statement",
            "rules": ["rule1", "rule2"],
            "tools": [{"name": "tool_name", "enabled": true, "permission": "allowed"}],
            "dependencies": []
        }
    ]
}

User request: {query}
"""


class SmartRouter:
    """Intelligent request router that classifies queries and suggests agent teams."""
    
    def __init__(self):
        self.model = settings.ROUTER_MODEL
    
    async def route(self, request: RouterRequest) -> RouterResponse:
        """
        Classify a query and potentially suggest agent teams.
        
        Args:
            request: RouterRequest with query and optional context
            
        Returns:
            RouterResponse with classification and suggested agents
        """
        prompt = ROUTER_PROMPT.format(query=request.query)
        
        if request.context:
            prompt += f"\n\nContext: {request.context}"
        
        messages = [
            {"role": "system", "content": "You are a query classifier. Respond ONLY with valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        full_response = ""
        async for chunk in gateway.chat_completion(
            messages=messages,
            model=self.model,
            provider="google",  # Use fast model for routing
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=2000,
            stream=True,
            json_mode=True
        ):
            if "choices" in chunk and len(chunk["choices"]) > 0:
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    full_response += content
        
        try:
            # Parse JSON response
            result = json.loads(full_response)
            
            route_type = RouteType(result.get("route_type", "COMPLEX").lower())
            confidence = float(result.get("confidence", 0.8))
            reasoning = result.get("reasoning", "Classification based on query analysis")
            
            suggested_agents = None
            if route_type == RouteType.COMPLEX and "suggested_agents" in result:
                suggested_agents = self._parse_suggested_agents(result["suggested_agents"])
            
            return RouterResponse(
                route_type=route_type,
                confidence=confidence,
                reasoning=reasoning,
                suggested_agents=suggested_agents
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: treat as COMPLEX if parsing fails
            return RouterResponse(
                route_type=RouteType.COMPLEX,
                confidence=0.5,
                reasoning=f"Failed to parse router response: {str(e)}",
                suggested_agents=None
            )
    
    def _parse_suggested_agents(self, agents_data: List[Dict[str, Any]]) -> List[AgentCreate]:
        """Parse suggested agents from router response."""
        agents = []
        
        for agent_data in agents_data:
            tools = []
            for tool_data in agent_data.get("tools", []):
                tools.append(ToolConfig(
                    name=tool_data.get("name", "unknown"),
                    enabled=tool_data.get("enabled", True),
                    permission=tool_data.get("permission", "allowed")
                ))
            
            agent = AgentCreate(
                name=agent_data.get("name", "agent"),
                icon=agent_data.get("icon", "🤖"),
                system_prompt=agent_data.get("system_prompt", "You are a helpful assistant."),
                objective=agent_data.get("objective", "Help the user"),
                rules=agent_data.get("rules", []),
                tools=tools,
                dependencies=agent_data.get("dependencies", [])
            )
            agents.append(agent)
        
        return agents


# Global router instance
router = SmartRouter()
