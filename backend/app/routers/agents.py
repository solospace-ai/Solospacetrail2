"""
Agent management endpoints
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import AgentModel, AgentCreate, AgentUpdate, AgentResponse

router = APIRouter()


@router.post("/session/{session_id}", response_model=AgentResponse)
async def create_agent(
    session_id: str,
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent in a session."""
    agent_id = str(uuid.uuid4())
    
    # Convert tools to JSON-serializable format
    tools_json = [
        {
            "name": t.name,
            "enabled": t.enabled,
            "permission": t.permission.value,
            "config": t.config
        }
        for t in agent_data.tools
    ]
    
    agent = AgentModel(
        id=agent_id,
        session_id=session_id,
        name=agent_data.name,
        icon=agent_data.icon or "🤖",
        system_prompt=agent_data.system_prompt,
        objective=agent_data.objective,
        rules=agent_data.rules,
        tools=tools_json,
        dependencies=agent_data.dependencies
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    return AgentResponse(
        id=agent.id,
        session_id=agent.session_id,
        name=agent.name,
        icon=agent.icon,
        system_prompt=agent.system_prompt,
        objective=agent.objective,
        rules=agent.rules,
        tools=agent_data.tools,
        dependencies=agent.dependencies,
        status=agent.status,
        execution_level=agent.execution_level,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )


@router.get("/session/{session_id}", response_model=List[AgentResponse])
async def list_agents(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all agents in a session."""
    result = await db.execute(
        select(AgentModel).where(AgentModel.session_id == session_id)
    )
    agents = result.scalars().all()
    
    return [
        AgentResponse(
            id=a.id,
            session_id=a.session_id,
            name=a.name,
            icon=a.icon,
            system_prompt=a.system_prompt,
            objective=a.objective,
            rules=a.rules,
            tools=[],  # Would need proper deserialization
            dependencies=a.dependencies,
            status=a.status,
            execution_level=a.execution_level,
            created_at=a.created_at,
            updated_at=a.updated_at
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific agent."""
    result = await db.execute(
        select(AgentModel).where(AgentModel.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse(
        id=agent.id,
        session_id=agent.session_id,
        name=agent.name,
        icon=agent.icon,
        system_prompt=agent.system_prompt,
        objective=agent.objective,
        rules=agent.rules,
        tools=[],
        dependencies=agent.dependencies,
        status=agent.status,
        execution_level=agent.execution_level,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an agent."""
    result = await db.execute(
        select(AgentModel).where(AgentModel.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields
    if agent_data.name is not None:
        agent.name = agent_data.name
    if agent_data.icon is not None:
        agent.icon = agent_data.icon
    if agent_data.system_prompt is not None:
        agent.system_prompt = agent_data.system_prompt
    if agent_data.objective is not None:
        agent.objective = agent_data.objective
    if agent_data.rules is not None:
        agent.rules = agent_data.rules
    if agent_data.status is not None:
        agent.status = agent_data.status.value
    
    await db.commit()
    await db.refresh(agent)
    
    return AgentResponse(
        id=agent.id,
        session_id=agent.session_id,
        name=agent.name,
        icon=agent.icon,
        system_prompt=agent.system_prompt,
        objective=agent.objective,
        rules=agent.rules,
        tools=[],
        dependencies=agent.dependencies,
        status=agent.status,
        execution_level=agent.execution_level,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an agent."""
    result = await db.execute(
        select(AgentModel).where(AgentModel.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    await db.delete(agent)
    await db.commit()
    
    return {"message": "Agent deleted", "id": agent_id}
