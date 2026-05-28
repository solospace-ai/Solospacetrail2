"""
Chat endpoints with SSE streaming
"""
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import ChatMessage, RouterRequest
from app.services.router import router as smart_router
from app.services.agent_executor import executor
from app.services.synthesizer import synthesizer
from app.models import RouteType

router = APIRouter()


async def chat_stream(
    query: str,
    session_id: str = None
) -> AsyncGenerator[str, None]:
    """Stream chat response using SSE format."""
    
    # First, classify the query
    router_response = await smart_router.route(RouterRequest(query=query))
    
    # Send routing info
    yield f"data: {json.dumps({'type': 'routing', 'data': router_response.model_dump()})}\n\n"
    
    if router_response.route_type == RouteType.TRIVIAL:
        # Direct response for trivial queries
        from app.services.llm_gateway import gateway
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Provide concise, direct answers."},
            {"role": "user", "content": query}
        ]
        
        async for chunk in gateway.chat_completion(
            messages=messages,
            model="gpt-4o-mini",
            provider="openai",
            stream=True
        ):
            if "choices" in chunk and len(chunk["choices"]) > 0:
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
    elif router_response.route_type == RouteType.TOOL_USE:
        # Single agent with tools
        # TODO: Implement single-agent execution
        yield f"data: {json.dumps({'type': 'error', 'message': 'TOOL_USE mode not yet implemented'})}\n\n"
        
    else:
        # COMPLEX - Multi-agent execution
        if not router_response.suggested_agents:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No agents suggested for complex query'})}\n\n"
            return
        
        # Execute agents and collect outputs
        agent_outputs = {}
        
        for agent_config in router_response.suggested_agents:
            yield f"data: {json.dumps({'type': 'agent_start', 'agent': agent_config.name})}\n\n"
            
            agent_output = ""
            async for event in executor.execute(
                agent=agent_config,
                user_query=query,
                max_turns=3
            ):
                yield f"data: {json.dumps({'type': 'agent_event', 'agent': agent_config.name, 'event': event})}\n\n"
                
                if event.get("type") == "final_answer":
                    agent_outputs[agent_config.name] = event.get("answer", "")
            
            yield f"data: {json.dumps({'type': 'agent_complete', 'agent': agent_config.name})}\n\n"
        
        # Synthesize final response
        yield f"data: {json.dumps({'type': 'synthesis_start'})}\n\n"
        
        async for chunk in synthesizer.synthesize(agent_outputs, query):
            if chunk.get("type") == "synthesis_chunk":
                yield f"data: {json.dumps({'type': 'content', 'content': chunk['content']})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/stream")
async def chat_endpoint(
    query: str,
    session_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Chat endpoint with SSE streaming."""
    return StreamingResponse(
        chat_stream(query, session_id),
        media_type="text/event-stream"
    )


@router.post("/")
async def chat_simple(
    message: ChatMessage,
    db: AsyncSession = Depends(get_db)
):
    """Simple chat endpoint (non-streaming)."""
    # TODO: Implement non-streaming chat
    return {"message": "Use /stream for streaming responses"}
