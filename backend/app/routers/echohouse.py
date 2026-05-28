"""
EchoHouse - Social Simulation Mode endpoints
"""
import json
from typing import AsyncGenerator, List, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import EchoHouseRequest, EchoHouseResponse, EchoHouseCastMember
from app.services.llm_gateway import gateway

router = APIRouter()


ECHOHOUSE_CAST_PROMPT = """Based on the following personal situation, generate a cast of 3-4 characters who would provide diverse perspectives in a conversation about this issue.

User's situation: {user_problem}

Generate characters with different viewpoints (e.g., supportive friend, critical observer, practical advisor, emotional supporter).

Respond in JSON format:
{{
    "cast": [
        {{
            "name": "Character Name",
            "role": "Their role/perspective",
            "perspective": "How they view situations",
            "personality_traits": ["trait1", "trait2"]
        }}
    ]
}}
"""

ECHOHOUSE_CONVERSATION_PROMPT = """Simulate a conversation round between these characters about the user's situation.

Characters:
{characters}

User's situation: {user_problem}

Previous conversation:
{previous_conversation}

Write a natural conversation where each character speaks once, sharing their perspective. Format as JSON:
{{
    "dialogue": [
        {{"character": "Name", "text": "What they say"}}
    ]
}}
"""

ECHOHOUSE_INSIGHT_PROMPT = """Based on this simulated conversation, provide therapeutic insights for the user.

User's situation: {user_problem}

Conversation transcript:
{conversation}

Provide insightful analysis covering:
1. Patterns observed
2. Unmet needs identified  
3. Constructive suggestions

Respond in a compassionate, helpful tone."""


async def echohouse_stream(
    request: EchoHouseRequest
) -> AsyncGenerator[str, None]:
    """Stream EchoHouse simulation using SSE format."""
    
    # Step 1: Generate cast if not provided
    cast = request.custom_cast or []
    
    if not cast:
        yield f"data: {json.dumps({'type': 'generating_cast'})}\n\n"
        
        prompt = ECHOHOUSE_CAST_PROMPT.format(user_problem=request.user_problem)
        full_response = ""
        
        async for chunk in gateway.chat_completion(
            messages=[
                {"role": "system", "content": "Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o-mini",
            provider="openai",
            stream=True,
            json_mode=True
        ):
            if "choices" in chunk and len(chunk["choices"]) > 0:
                content = chunk["choices"][0].get("delta", {}).get("content", "")
                if content:
                    full_response += content
        
        try:
            result = json.loads(full_response)
            cast_data = result.get("cast", [])
            cast = [EchoHouseCastMember(**c) for c in cast_data]
            
            yield f"data: {json.dumps({'type': 'cast_generated', 'cast': [c.model_dump() for c in cast]})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return
    
    # Step 2: Run conversation rounds
    previous_conversation = ""
    all_dialogues = []
    
    for round_num in range(request.rounds):
        yield f"data: {json.dumps({'type': 'round_start', 'round': round_num + 1})}\n\n"
        
        characters_text = "\n".join([
            f"- {c.name} ({c.role}): {c.perspective}"
            for c in cast
        ])
        
        prompt = ECHOHOUSE_CONVERSATION_PROMPT.format(
            characters=characters_text,
            user_problem=request.user_problem,
            previous_conversation=previous_conversation or "None yet"
        )
        
        full_response = ""
        async for chunk in gateway.chat_completion(
            messages=[
                {"role": "system", "content": "Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o-mini",
            provider="openai",
            stream=True,
            json_mode=True
        ):
            if "choices" in chunk and len(chunk["choices"]) > 0:
                content = chunk["choices"][0].get("delta", {}).get("content", "")
                if content:
                    full_response += content
        
        try:
            result = json.loads(full_response)
            dialogue = result.get("dialogue", [])
            all_dialogues.append(dialogue)
            
            yield f"data: {json.dumps({'type': 'round_complete', 'round': round_num + 1, 'dialogue': dialogue})}\n\n"
            
            # Update conversation history
            previous_conversation = "\n".join([
                f"{d['character']}: {d['text']}"
                for d in dialogue
            ])
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    # Step 3: Generate insight
    yield f"data: {json.dumps({'type': 'generating_insight'})}\n\n"
    
    conversation_text = "\n\n".join([
        f"Round {i+1}:\n" + "\n".join([f"{d['character']}: {d['text']}" for d in dialogue])
        for i, dialogue in enumerate(all_dialogues)
    ])
    
    prompt = ECHOHOUSE_INSIGHT_PROMPT.format(
        user_problem=request.user_problem,
        conversation=conversation_text
    )
    
    full_insight = ""
    async for chunk in gateway.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        provider="openai",
        stream=True
    ):
        if "choices" in chunk and len(chunk["choices"]) > 0:
            content = chunk["choices"][0].get("delta", {}).get("content", "")
            if content:
                full_insight += content
                yield f"data: {json.dumps({'type': 'insight_chunk', 'content': content})}\n\n"
    
    yield f"data: {json.dumps({'type': 'complete', 'insight': full_insight})}\n\n"


@router.post("/stream")
async def echohouse_endpoint(request: EchoHouseRequest):
    """EchoHouse social simulation with streaming."""
    return StreamingResponse(
        echohouse_stream(request),
        media_type="text/event-stream"
    )


@router.post("/")
async def echohouse_simple(request: EchoHouseRequest):
    """Simple EchoHouse endpoint (non-streaming)."""
    # Collect all streamed data
    result = {
        "cast": [],
        "conversations": [],
        "insight": ""
    }
    
    async for line in echohouse_stream(request):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if data.get("type") == "cast_generated":
                    result["cast"] = data.get("cast", [])
                elif data.get("type") == "round_complete":
                    result["conversations"].append({
                        "round": data.get("round"),
                        "dialogue": data.get("dialogue", [])
                    })
                elif data.get("type") == "complete":
                    result["insight"] = data.get("insight", "")
            except:
                continue
    
    return result
