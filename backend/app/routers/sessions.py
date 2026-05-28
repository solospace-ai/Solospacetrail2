"""
Session management endpoints
"""
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import SessionModel, SessionCreate, SessionResponse, AgentModel
from app.services.router import router as smart_router
from app.models import RouterRequest

router = APIRouter()


@router.post("/", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    
    # Generate title if not provided
    title = session_data.title or f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    
    # Create session
    session = SessionModel(
        id=session_id,
        title=title,
        metadata_json={"auto_generate": session_data.auto_generate_agents}
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # If auto-generate is enabled and there's an initial query, generate agents
    if session_data.auto_generate_agents and session_data.initial_query:
        # Use smart router to classify and suggest agents
        router_response = await smart_router.route(
            RouterRequest(query=session_data.initial_query)
        )
        
        # TODO: Create agents from router_response.suggested_agents
    
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        agents=[],
        edges=[]
    )


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all sessions."""
    result = await db.execute(select(SessionModel).order_by(SessionModel.updated_at.desc()))
    sessions = result.scalars().all()
    
    return [
        SessionResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific session with its agents."""
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Load agents
    agents_result = await db.execute(
        select(AgentModel).where(AgentModel.session_id == session_id)
    )
    agents = agents_result.scalars().all()
    
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a session."""
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await db.delete(session)
    await db.commit()
    
    return {"message": "Session deleted", "id": session_id}
