"""
Student Profile API Endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict
from loguru import logger

from app.models.schemas import StudentProfile

router = APIRouter()

# In-memory storage (replace with database)
_students: Dict[str, StudentProfile] = {}


@router.post("/profile", response_model=StudentProfile)
async def create_profile(profile: StudentProfile) -> StudentProfile:
    """Create or update student profile"""
    try:
        _students[profile.id] = profile
        logger.info(f"Created/updated profile for student {profile.id}")
        return profile
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{student_id}", response_model=StudentProfile)
async def get_profile(student_id: str) -> StudentProfile:
    """Get student profile"""
    profile = _students.get(student_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return profile


@router.put("/profile/{student_id}", response_model=StudentProfile)
async def update_profile(student_id: str, profile: StudentProfile) -> StudentProfile:
    """Update student profile"""
    if student_id != profile.id:
        raise HTTPException(status_code=400, detail="Student ID mismatch")
    
    _students[student_id] = profile
    logger.info(f"Updated profile for student {student_id}")
    return profile


@router.delete("/profile/{student_id}")
async def delete_profile(student_id: str):
    """Delete student profile"""
    if student_id in _students:
        del _students[student_id]
        return {"message": "Profile deleted"}
    
    raise HTTPException(status_code=404, detail="Student not found")
