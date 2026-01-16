"""
Courses API Endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from loguru import logger

from app.models.schemas import Course, CourseLevel
from app.services.mit_api import MITCoursesClient
from app.services.rag.rag_service import RAGService

router = APIRouter()


@router.get("/search")
async def search_courses(
    q: str = Query(..., description="Search query"),
    department: Optional[str] = Query(None, description="Department number (e.g., '6')"),
    level: Optional[CourseLevel] = Query(None, description="Course level (U/G)"),
    limit: int = Query(10, ge=1, le=50, description="Max results")
):
    """
    Search for courses using RAG
    """
    try:
        rag_service = RAGService()
        
        # Build filters
        filters = {}
        if department:
            filters["department"] = department
        if level:
            filters["level"] = level.value
        
        # Search using RAG
        results = await rag_service.query_courses(
            query=q,
            k=limit
        )
        
        # Format results
        courses = []
        for doc in results:
            courses.append({
                "id": doc["metadata"].get("course_id"),
                "title": doc["metadata"].get("title"),
                "department": doc["metadata"].get("department"),
                "units": doc["metadata"].get("units"),
                "description": doc["document"][:200] + "...",
                "similarity": doc["similarity"]
            })
        
        return {
            "query": q,
            "results": courses,
            "count": len(courses)
        }
    
    except Exception as e:
        logger.error(f"Error searching courses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{course_id}")
async def get_course(course_id: str):
    """
    Get detailed information about a specific course
    """
    try:
        # Try MIT API first
        mit_client = MITCoursesClient()
        
        try:
            course = await mit_client.get_course(course_id)
            
            if course:
                return course
        finally:
            await mit_client.close()
        
        # Fall back to RAG search
        rag_service = RAGService()
        results = await rag_service.query_courses(
            query=f"course {course_id}",
            k=1
        )
        
        if results:
            return {
                "id": results[0]["metadata"].get("course_id"),
                "info": results[0]["document"],
                "metadata": results[0]["metadata"]
            }
        
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching course {course_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/department/{dept}")
async def get_department_courses(
    dept: str,
    level: Optional[CourseLevel] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get all courses in a department
    """
    try:
        rag_service = RAGService()
        
        results = await rag_service.query_courses(
            query=f"department {dept} courses",
            k=limit
        )
        
        # Filter by department in metadata
        dept_courses = [
            {
                "id": doc["metadata"].get("course_id"),
                "title": doc["metadata"].get("title"),
                "units": doc["metadata"].get("units"),
                "level": doc["metadata"].get("level")
            }
            for doc in results
            if doc["metadata"].get("department") == dept
        ]
        
        if level:
            dept_courses = [c for c in dept_courses if c["level"] == level.value]
        
        return {
            "department": dept,
            "courses": dept_courses,
            "count": len(dept_courses)
        }
    
    except Exception as e:
        logger.error(f"Error fetching department courses: {e}")
        raise HTTPException(status_code=500, detail=str(e))
