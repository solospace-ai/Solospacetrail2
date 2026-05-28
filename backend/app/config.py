"""
Solospace Backend Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Solospace"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./solospace.db"
    CHROMA_DB_PATH: str = "./chroma_db"
    
    # AI Providers - API Keys (optional, can be set per-request)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    TOGETHER_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    FIREWORKS_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = "us-east-1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LM_STUDIO_BASE_URL: str = "http://localhost:1234"
    NVIDIA_NIM_API_KEY: Optional[str] = None
    DASHSCOPE_API_KEY: Optional[str] = None
    XAI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    CEREBRAS_API_KEY: Optional[str] = None
    
    # Default provider and model
    DEFAULT_PROVIDER: str = "openai"
    DEFAULT_MODEL: str = "gpt-4o-mini"
    FALLBACK_PROVIDER: str = "ollama"
    
    # Router model (fast, cheap for classification)
    ROUTER_MODEL: str = "gemini-2.0-flash-lite"
    
    # Agent execution limits
    MAX_AGENT_TURNS: int = 5
    MAX_TOOL_CALLS_PER_TURN: int = 3
    MAX_CONCURRENT_AGENTS: int = 10
    
    # Security
    SSRF_ALLOWED_HOSTS: List[str] = ["api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com"]
    CODE_EXECUTION_TIMEOUT: int = 30
    CODE_EXECUTION_MEMORY_LIMIT: str = "256M"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
