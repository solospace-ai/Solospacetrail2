"""
Pydantic models and SQLAlchemy ORM models for Solospace
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


# ============== Enums ==============

class AgentStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"
    COMPLETED = "completed"


class ToolPermission(str, Enum):
    ALLOWED = "allowed"
    ASK_USER = "ask_user"
    DENIED = "denied"


class RouteType(str, Enum):
    TRIVIAL = "trivial"
    TOOL_USE = "tool_use"
    COMPLEX = "complex"


class ExecutionLevel(str, Enum):
    """Execution level for parallel agent execution."""
    LEVEL_0 = "level_0"
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    LEVEL_4 = "level_4"


# ============== Pydantic Models (Request/Response) ==============

class ProviderConfig(BaseModel):
    """Configuration for an AI provider."""
    provider: str
    api_key: Optional[str] = None
    model: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = True


class ToolConfig(BaseModel):
    """Configuration for an agent tool."""
    name: str
    enabled: bool = True
    permission: ToolPermission = ToolPermission.ALLOWED
    config: Optional[Dict[str, Any]] = None


class AgentCreate(BaseModel):
    """Request model for creating an agent."""
    name: str
    icon: Optional[str] = "🤖"
    system_prompt: str
    objective: str
    rules: List[str] = []
    tools: List[ToolConfig] = []
    dependencies: List[str] = []  # List of agent IDs this agent depends on
    provider_config: Optional[ProviderConfig] = None


class AgentUpdate(BaseModel):
    """Request model for updating an agent."""
    name: Optional[str] = None
    icon: Optional[str] = None
    system_prompt: Optional[str] = None
    objective: Optional[str] = None
    rules: Optional[List[str]] = None
    tools: Optional[List[ToolConfig]] = None
    dependencies: Optional[List[str]] = None
    status: Optional[AgentStatus] = None


class AgentResponse(BaseModel):
    """Response model for an agent."""
    id: str
    session_id: str
    name: str
    icon: str
    system_prompt: str
    objective: str
    rules: List[str]
    tools: List[ToolConfig]
    dependencies: List[str]
    status: AgentStatus
    execution_level: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EdgeCreate(BaseModel):
    """Request model for creating an edge between agents."""
    source_id: str
    target_id: str


class SessionCreate(BaseModel):
    """Request model for creating a session."""
    title: Optional[str] = None
    initial_query: Optional[str] = None
    auto_generate_agents: bool = True


class SessionResponse(BaseModel):
    """Response model for a session."""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    agents: List[AgentResponse] = []
    edges: List[Dict[str, str]] = []
    
    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    """Chat message model."""
    role: Literal["user", "assistant", "system", "agent"]
    content: str
    agent_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RouterRequest(BaseModel):
    """Request for the smart router."""
    query: str
    context: Optional[str] = None


class RouterResponse(BaseModel):
    """Response from the smart router."""
    route_type: RouteType
    confidence: float
    reasoning: str
    suggested_agents: Optional[List[AgentCreate]] = None


class ToolApprovalRequest(BaseModel):
    """Request for tool approval."""
    agent_id: str
    tool_name: str
    tool_input: Dict[str, Any]
    approval_id: str


class ToolApprovalResponse(BaseModel):
    """Response for tool approval."""
    approved: bool
    approval_id: str


class EchoHouseCastMember(BaseModel):
    """Cast member for EchoHouse simulation."""
    name: str
    role: str
    perspective: str
    personality_traits: List[str] = []


class EchoHouseRequest(BaseModel):
    """Request for EchoHouse simulation."""
    user_problem: str
    custom_cast: Optional[List[EchoHouseCastMember]] = None
    rounds: int = 3


class EchoHouseResponse(BaseModel):
    """Response from EchoHouse simulation."""
    cast: List[EchoHouseCastMember]
    conversations: List[Dict[str, Any]]
    insight: str


# ============== SQLAlchemy ORM Models ==============

class SessionModel(Base):
    """SQLAlchemy model for chat sessions."""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)
    
    # Relationships
    agents = relationship("AgentModel", back_populates="session", cascade="all, delete-orphan")
    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan")
    checkpoints = relationship("CheckpointModel", back_populates="session", cascade="all, delete-orphan")


class AgentModel(Base):
    """SQLAlchemy model for AI agents."""
    __tablename__ = "agents"
    
    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    name = Column(String(100), nullable=False)
    icon = Column(String(10), default="🤖")
    system_prompt = Column(Text, nullable=False)
    objective = Column(Text, nullable=False)
    rules = Column(JSON, default=list)
    tools = Column(JSON, default=list)
    dependencies = Column(JSON, default=list)
    status = Column(String(20), default=AgentStatus.IDLE.value)
    execution_level = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("SessionModel", back_populates="agents")
    logs = relationship("AgentLogModel", back_populates="agent", cascade="all, delete-orphan")


class AgentLogModel(Base):
    """SQLAlchemy model for agent execution logs."""
    __tablename__ = "agent_logs"
    
    id = Column(String(36), primary_key=True, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    turn = Column(Integer, default=0)
    thought = Column(Text, nullable=True)
    action = Column(String(100), nullable=True)
    action_input = Column(JSON, nullable=True)
    observation = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent = relationship("AgentModel", back_populates="logs")


class MessageModel(Base):
    """SQLAlchemy model for chat messages."""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    agent_id = Column(String(36), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("SessionModel", back_populates="messages")


class CheckpointModel(Base):
    """SQLAlchemy model for execution checkpoints (resume capability)."""
    __tablename__ = "checkpoints"
    
    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    agent_id = Column(String(36), nullable=True)
    state = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("SessionModel", back_populates="checkpoints")


class ToolApprovalModel(Base):
    """SQLAlchemy model for pending tool approvals."""
    __tablename__ = "tool_approvals"
    
    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    agent_id = Column(String(36), nullable=False)
    tool_name = Column(String(100), nullable=False)
    tool_input = Column(JSON, nullable=False)
    approved = Column(Boolean, default=False)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SemanticCacheModel(Base):
    """SQLAlchemy model for semantic caching of prompts."""
    __tablename__ = "semantic_cache"
    
    id = Column(String(36), primary_key=True, index=True)
    prompt_hash = Column(String(64), unique=True, index=True, nullable=False)
    response = Column(Text, nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=1)
