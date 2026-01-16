"""
MIT Schedule Advisor - Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "MIT Schedule Advisor"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # API Keys
    OPENAI_API_KEY: str
    MIT_COURSES_API_KEY: str = ""
    MIT_CATALOG_API_KEY: str = ""
    
    # OpenAI Settings
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 2000
    
    # API Endpoints
    MIT_COURSES_API_URL: str = "https://mit-courses-v1.cloudhub.io/courses/v1"
    MIT_CATALOG_API_URL: str = "https://mit-course-catalog-v2.cloudhub.io/coursecatalog/v2"
    
    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_COURSES: str = "mit_courses"
    CHROMA_COLLECTION_REQUIREMENTS: str = "mit_requirements"
    CHROMA_COLLECTION_KNOWLEDGE: str = "mit_knowledge"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 86400  # 24 hours
    
    # RAG Settings
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.7
    RAG_RERANK: bool = True
    
    # Solver Settings
    SOLVER_TIMEOUT_SECONDS: int = 30
    SOLVER_MAX_TERMS: int = 8  # 4 years
    DEFAULT_MAX_UNITS_PER_TERM: int = 60
    DEFAULT_MIN_UNITS_PER_TERM: int = 36
    
    # Scraping
    SCRAPER_USER_AGENT: str = "MIT-Schedule-Advisor/0.1.0"
    SCRAPER_DELAY_SECONDS: float = 1.0
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://*.lovable.app",
        "https://*.railway.app"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
