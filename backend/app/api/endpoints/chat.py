"""
Chat API Endpoint
"""
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from app.models.schemas import ChatRequest, ChatResponse, StudentProfile
from app.services.llm_service import LLMService

router = APIRouter()

# In-memory storage for demo (replace with database later)
_student_profiles = {}
_student_schedules = {}


def get_llm_service() -> LLMService:
    """Dependency injection for LLM service"""
    return LLMService()


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    llm_service: LLMService = Depends(get_llm_service)
) -> ChatResponse:
    """
    Chat with the AI advisor
    
    Processes user messages with RAG context and function calling
    """
    try:
        # Get student profile (in production, fetch from database)
        student_profile = _student_profiles.get(request.student_id)
        
        if not student_profile:
            # Create default profile
            student_profile = StudentProfile(
                id=request.student_id,
                major="6-3",  # Default
                year=2,
                semester="spring",
                completed_courses=[],
                in_progress_courses=[]
            )
            _student_profiles[request.student_id] = student_profile
        
        # Get current schedule if any
        current_schedule = _student_schedules.get(request.student_id) if request.include_schedule else None
        
        # Process chat message
        response = await llm_service.chat(
            message=request.message,
            student_profile=student_profile,
            conversation_history=request.conversation_history,
            current_schedule=current_schedule
        )
        
        # Update schedule if modified
        if response.updated_schedule:
            _student_schedules[request.student_id] = response.updated_schedule
        
        logger.info(f"Chat processed for student {request.student_id}")
        return response
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{student_id}")
async def get_chat_history(student_id: str):
    """Get chat history for a student (placeholder)"""
    # TODO: Implement chat history storage
    return {"student_id": student_id, "history": []}
