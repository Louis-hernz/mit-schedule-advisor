"""
MIT Schedule Advisor - MIT API Clients
"""
import httpx
from typing import List, Optional, Dict, Any
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.models.schemas import Course, Term, CourseLevel, MeetingTime, DayOfWeek

settings = get_settings()


class MITCoursesClient:
    """
    Client for MIT Courses API
    Retrieves course catalog information
    """
    
    def __init__(self):
        self.base_url = settings.MIT_COURSES_API_URL
        self.api_key = settings.MIT_COURSES_API_KEY
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers=self._get_headers()
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including API key if available"""
        headers = {
            "Accept": "application/json",
            "User-Agent": settings.SCRAPER_USER_AGENT
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_all_courses(self) -> List[Course]:
        """
        Fetch all courses from the catalog
        
        Returns:
            List of Course objects
        """
        try:
            logger.info("Fetching all courses from MIT Courses API")
            response = await self.client.get("/courses")
            response.raise_for_status()
            
            data = response.json()
            courses = []
            
            # Parse API response to Course objects
            # Note: Adjust parsing based on actual API response structure
            for item in data.get("courses", []):
                course = self._parse_course(item)
                if course:
                    courses.append(course)
            
            logger.info(f"Retrieved {len(courses)} courses")
            return courses
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching courses: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching courses: {e}")
            raise
    
    async def get_course(self, course_id: str) -> Optional[Course]:
        """
        Fetch a specific course by ID
        
        Args:
            course_id: Course number (e.g., "6.006")
        
        Returns:
            Course object or None if not found
        """
        try:
            logger.info(f"Fetching course {course_id}")
            response = await self.client.get(f"/courses/{course_id}")
            response.raise_for_status()
            
            data = response.json()
            return self._parse_course(data)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Course {course_id} not found")
                return None
            raise
        except Exception as e:
            logger.error(f"Error fetching course {course_id}: {e}")
            raise
    
    async def search_courses(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        level: Optional[CourseLevel] = None,
        **kwargs
    ) -> List[Course]:
        """
        Search for courses with filters
        
        Args:
            query: Search query string
            department: Department number (e.g., "6")
            level: Course level (U/G)
            **kwargs: Additional query parameters
        
        Returns:
            List of matching courses
        """
        try:
            params = {}
            if query:
                params["q"] = query
            if department:
                params["department"] = department
            if level:
                params["level"] = level.value
            params.update(kwargs)
            
            logger.info(f"Searching courses with params: {params}")
            response = await self.client.get("/courses", params=params)
            response.raise_for_status()
            
            data = response.json()
            courses = []
            for item in data.get("courses", []):
                course = self._parse_course(item)
                if course:
                    courses.append(course)
            
            return courses
            
        except Exception as e:
            logger.error(f"Error searching courses: {e}")
            raise
    
    def _parse_course(self, data: Dict[str, Any]) -> Optional[Course]:
        """
        Parse API response data into Course object
        
        Note: This is a template - adjust based on actual API response structure
        """
        try:
            # Extract course number and department
            course_id = data.get("course_id") or data.get("number")
            if not course_id:
                return None
            
            # Parse department from course_id (e.g., "6.006" -> "6")
            department = course_id.split(".")[0] if "." in course_id else course_id.split("-")[0]
            
            # Parse prerequisites
            prereqs = []
            prereq_data = data.get("prerequisites", "") or ""
            if isinstance(prereq_data, list):
                prereqs = prereq_data
            elif isinstance(prereq_data, str):
                # Simple parsing - may need more sophisticated logic
                prereqs = [p.strip() for p in prereq_data.split(",") if p.strip()]
            
            # Parse terms offered
            terms_offered = []
            terms_data = data.get("terms", []) or []
            for term in terms_data:
                term_lower = term.lower()
                if "fall" in term_lower:
                    terms_offered.append(Term.FALL)
                if "spring" in term_lower:
                    terms_offered.append(Term.SPRING)
                if "iap" in term_lower:
                    terms_offered.append(Term.IAP)
            
            # Parse level
            level_str = data.get("level", "U")
            try:
                level = CourseLevel(level_str)
            except ValueError:
                level = CourseLevel.UNDERGRAD
            
            return Course(
                id=course_id,
                title=data.get("title", ""),
                description=data.get("description", ""),
                units=int(data.get("units", 12)),
                level=level,
                prerequisites=prereqs,
                corequisites=data.get("corequisites", []) or [],
                terms_offered=list(set(terms_offered)),
                meets_requirements=data.get("requirements", []) or [],
                department=department
            )
            
        except Exception as e:
            logger.warning(f"Error parsing course data: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class MITCourseCatalogClient:
    """
    Client for MIT Course Catalog API
    Retrieves term-specific scheduling information
    """
    
    def __init__(self):
        self.base_url = settings.MIT_CATALOG_API_URL
        self.api_key = settings.MIT_CATALOG_API_KEY
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers=self._get_headers()
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "Accept": "application/json",
            "User-Agent": settings.SCRAPER_USER_AGENT
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_term_subjects(self, term: str) -> List[Dict[str, Any]]:
        """
        Get all subjects offered in a specific term
        
        Args:
            term: Term identifier (e.g., "2024FA")
        
        Returns:
            List of subject data dictionaries
        """
        try:
            logger.info(f"Fetching subjects for term {term}")
            response = await self.client.get(f"/terms/{term}/subjects")
            response.raise_for_status()
            
            data = response.json()
            subjects = data.get("subjects", []) or []
            
            logger.info(f"Retrieved {len(subjects)} subjects for term {term}")
            return subjects
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching term subjects: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching term subjects: {e}")
            raise
    
    async def get_subject_details(
        self,
        term: str,
        subject_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific subject in a term
        
        Args:
            term: Term identifier (e.g., "2024FA")
            subject_id: Subject/course identifier
        
        Returns:
            Subject details dictionary or None if not found
        """
        try:
            logger.info(f"Fetching subject {subject_id} for term {term}")
            response = await self.client.get(f"/terms/{term}/subjects/{subject_id}")
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Subject {subject_id} not found for term {term}")
                return None
            raise
        except Exception as e:
            logger.error(f"Error fetching subject details: {e}")
            raise
    
    def parse_meeting_times(self, subject_data: Dict[str, Any]) -> List[MeetingTime]:
        """
        Parse meeting times from subject data
        
        Args:
            subject_data: Subject data from API
        
        Returns:
            List of MeetingTime objects
        """
        meeting_times = []
        
        try:
            # Parse based on actual API structure
            meetings = subject_data.get("meetings", []) or []
            
            for meeting in meetings:
                days_str = meeting.get("days", "")
                days = self._parse_days(days_str)
                
                if days:
                    meeting_time = MeetingTime(
                        days=days,
                        start_time=meeting.get("start_time", ""),
                        end_time=meeting.get("end_time", ""),
                        location=meeting.get("location")
                    )
                    meeting_times.append(meeting_time)
        
        except Exception as e:
            logger.warning(f"Error parsing meeting times: {e}")
        
        return meeting_times
    
    @staticmethod
    def _parse_days(days_str: str) -> List[DayOfWeek]:
        """
        Parse day codes to DayOfWeek enum
        
        Args:
            days_str: String like "MWF" or "TR"
        
        Returns:
            List of DayOfWeek values
        """
        day_map = {
            "M": DayOfWeek.MONDAY,
            "T": DayOfWeek.TUESDAY,
            "W": DayOfWeek.WEDNESDAY,
            "R": DayOfWeek.THURSDAY,
            "F": DayOfWeek.FRIDAY
        }
        
        days = []
        for char in days_str.upper():
            if char in day_map:
                days.append(day_map[char])
        
        return days
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_clients():
        """Test the API clients"""
        courses_client = MITCoursesClient()
        catalog_client = MITCourseCatalogClient()
        
        try:
            # Test fetching courses
            courses = await courses_client.get_all_courses()
            print(f"Found {len(courses)} courses")
            
            if courses:
                print(f"\nFirst course: {courses[0].id} - {courses[0].title}")
            
            # Test fetching term subjects
            term = "2024FA"
            subjects = await catalog_client.get_term_subjects(term)
            print(f"\nFound {len(subjects)} subjects for {term}")
            
        finally:
            await courses_client.close()
            await catalog_client.close()
    
    asyncio.run(test_clients())
