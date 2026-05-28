"""
Agent Executor - Implements ReAct loop for autonomous agent execution
"""
import json
import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from app.models import AgentCreate, ToolConfig, ToolPermission
from app.services.llm_gateway import gateway
from app.config import settings
from app.services.tools.web_search import WebSearchTool
from app.services.tools.web_browser import WebBrowserTool
from app.services.tools.code_executor import CodeExecutorTool
from app.services.tools.api_connector import APIConnectorTool
from app.services.tools.memory import MemoryTool


REACT_SYSTEM_PROMPT = """You are an autonomous AI agent with access to tools. Follow the ReAct (Reasoning + Acting) pattern:

1. THOUGHT: Analyze the current situation and what you need to do
2. ACTION: Choose a tool to use (or FINAL_ANSWER if you're done)
3. OBSERVATION: Review the tool output
4. Repeat until you have a complete answer

Available tools:
{tools_description}

Format your responses as JSON:
{{
    "thought": "Your reasoning about what to do next",
    "action": "tool_name or FINAL_ANSWER",
    "action_input": {{"param1": "value1"}}  // omit if FINAL_ANSWER
}}

Rules:
- Think step by step
- Use tools when needed
- Don't make up information
- Admit when you don't know something
- Respect tool
- Maximum {max_turns} turns per task

Current objective: {objective}
"""


class AgentExecutor:
    """Executes agents using the ReAct pattern with tool usage."""
    
    def __init__(self):
        self.tools = {
            "web_search": WebSearchTool(),
            "web_browser": WebBrowserTool(),
            "code_executor": CodeExecutorTool(
                timeout=settings.CODE_EXECUTION_TIMEOUT
            ),
            "api_connector": APIConnectorTool(),
            "memory": MemoryTool()
        }
    
    async def execute(
        self,
        agent: AgentCreate,
        user_query: str,
        context: Optional[str] = None,
        max_turns: int = 5,
        approval_callback: Optional[callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute an agent with ReAct loop.
        
        Args:
            agent: Agent definition
            user_query: User's query/task
            context: Optional context from previous agents
            max_turns: Maximum ReAct turns
            approval_callback: Optional callback for tool approval
            
        Yields:
            Events: thought, action, observation, final_answer, error
        """
        # Build system prompt
        tools_description = self._build_tools_description(agent.tools)
        system_prompt = REACT_SYSTEM_PROMPT.format(
            tools_description=tools_description,
            max_turns=max_turns,
            objective=agent.objective
        )
        
        # Initialize conversation history
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_query}" + (f"\n\nContext:\n{context}" if context else "")}
        ]
        
        turn = 0
        while turn < max_turns:
            turn += 1
            
            # Get LLM response
            full_response = ""
            try:
                async for chunk in gateway.chat_completion(
                    messages=messages,
                    model="gpt-4o-mini",
                    provider="openai",
                    temperature=0.7,
                    max_tokens=2000,
                    stream=True,
                    json_mode=True
                ):
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_response += content
                
                # Parse response
                try:
                    response_data = json.loads(full_response)
                except json.JSONDecodeError:
                    response_data = {
                        "thought": full_response,
                        "action": "FINAL_ANSWER",
                        "action_input": {}
                    }
                
                thought = response_data.get("thought", "")
                action = response_data.get("action", "FINAL_ANSWER")
                action_input = response_data.get("action_input", {})
                
                # Emit thought event
                yield {
                    "type": "thought",
                    "turn": turn,
                    "thought": thought,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Check if we're done
                if action == "FINAL_ANSWER":
                    yield {
                        "type": "final_answer",
                        "answer": action_input.get("answer", thought) if isinstance(action_input, dict) else thought,
                        "turn": turn,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    return
                
                # Execute tool
                if action in self.tools:
                    tool_config = self._get_tool_config(agent.tools, action)
                    
                    # Check permissions
                    if tool_config and tool_config.permission == ToolPermission.DENIED:
                        yield {
                            "type": "error",
                            "error": f"Tool '{action}' is denied for this agent",
                            "turn": turn,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        continue
                    
                    # Request approval if needed
                    if tool_config and tool_config.permission == ToolPermission.ASK_USER:
                        if approval_callback:
                            approval_id = str(uuid.uuid4())
                            approved = await approval_callback(
                                agent_id=agent.name,
                                tool_name=action,
                                tool_input=action_input,
                                approval_id=approval_id
                            )
                            if not approved:
                                yield {
                                    "type": "tool_denied",
                                    "tool": action,
                                    "approval_id": approval_id,
                                    "turn": turn,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                                messages.append({
                                    "role": "assistant",
                                    "content": json.dumps(response_data)
                                })
                                messages.append({
                                    "role": "user",
                                    "content": f"Tool '{action}' was denied by the user. Choose a different action."
                                })
                                continue
                    
                    # Execute the tool
                    yield {
                        "type": "action",
                        "action": action,
                        "input": action_input,
                        "turn": turn,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    tool = self.tools[action]
                    try:
                        observation = await tool.execute(**action_input)
                        
                        yield {
                            "type": "observation",
                            "action": action,
                            "observation": observation,
                            "turn": turn,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        # Add to conversation history
                        messages.append({
                            "role": "assistant",
                            "content": json.dumps(response_data)
                        })
                        messages.append({
                            "role": "user",
                            "content": f"Observation from {action}: {json.dumps(observation)}"
                        })
                        
                    except Exception as e:
                        yield {
                            "type": "tool_error",
                            "action": action,
                            "error": str(e),
                            "turn": turn,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        messages.append({
                            "role": "user",
                            "content": f"Tool '{action}' failed: {str(e)}. Try a different approach."
                        })
                else:
                    # Unknown tool
                    yield {
                        "type": "error",
                        "error": f"Unknown tool: {action}",
                        "turn": turn,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    messages.append({
                        "role": "user",
                        "content": f"Unknown tool '{action}'. Available tools: {list(self.tools.keys())}"
                    })
                    
            except Exception as e:
                yield {
                    "type": "error",
                    "error": str(e),
                    "turn": turn,
                    "timestamp": datetime.utcnow().isoformat()
                }
                break
        
        # Max turns reached without final answer
        yield {
            "type": "max_turns_reached",
            "message": f"Maximum {max_turns} turns reached without completing the task",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _build_tools_description(self, tool_configs: List[ToolConfig]) -> str:
        """Build description of available tools."""
        descriptions = []
        
        for tool_config in tool_configs:
            if tool_config.enabled and tool_config.name in self.tools:
                tool = self.tools[tool_config.name]
                schema = tool.get_schema()
                descriptions.append(
                    f"- {tool.name}: {tool.description}\n  Schema: {json.dumps(schema)}"
                )
        
        return "\n".join(descriptions) if descriptions else "No tools available"
    
    def _get_tool_config(self, tool_configs: List[ToolConfig], tool_name: str) -> Optional[ToolConfig]:
        """Get tool configuration by name."""
        for config in tool_configs:
            if config.name == tool_name:
                return config
        return None


# Global executor instance
executor = AgentExecutor()
