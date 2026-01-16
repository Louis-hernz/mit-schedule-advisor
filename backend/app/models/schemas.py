"""
MIT Schedule Advisor - Data Models
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import time


class Term(str, Enum):
    """Academic term enumeration"""
    FALL = "fall"
    IAP = "iap"
    SPRING = "spring"
    SUMMER = "summer"


class CourseLevel(str, Enum):
    """Course level enumeration"""
    UNDERGRAD = "U"
    GRAD = "G"
    BOTH = "U/G"


class DayOfWeek(str, Enum):
    """Days of the week"""
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"


class RequirementType(str, Enum):
    """Types of degree requirements"""
    SPECIFIC_COURSE = "specific_course"
    CATEGORY = "category"
    UNITS = "units"
    ELECTIVE = "elective"


class MeetingTime(BaseModel):
    """Course meeting time information"""
    days: List[DayOfWeek]
    start_time: str
    end_time: str
    location: Optional[str] = None
    
    def conflicts_with(self, other: 'MeetingTime') -> bool:
        """Check if this meeting time conflicts with another"""
        # Check if any days overlap
        if not any(day in other.days for day in self.days):
            return False
        
        # Parse times
        start1 = self._parse_time(self.start_time)
        end1 = self._parse_time(self.end_time)
        start2 = self._parse_time(other.start_time)
        end2 = self._parse_time(other.end_time)
        
        # Check time overlap
        return start1 < end2 and start2 < end1
    
    @staticmethod
    def _parse_time(time_str: str) -> int:
        """Convert time string to minutes since midnight"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return hour * 60 + minute
        except:
            return 0


class Course(BaseModel):
    """Course information from MIT Courses API"""
    id: str = Field(..., description="Course number (e.g., '6.006')")
    title: str
    description: str
    units: int = Field(..., description="Total units (typically 12 for full courses)")
    level: CourseLevel
    prerequisites: List[str] = Field(default_factory=list)
    corequisites: List[str] = Field(default_factory=list)
    terms_offered: List[Term] = Field(default_factory=list)
    meets_requirements: List[str] = Field(
        default_factory=list,
        description="Requirements this course satisfies (e.g., ['REST', 'CI-M'])"
    )
    department: str = Field(..., description="Department number (e.g., '6')")
    
    # Optional fields from scraping
    difficulty_rating: Optional[float] = None
    time_commitment_hours: Optional[float] = None
    student_rating: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "6.006",
                "title": "Introduction to Algorithms",
                "description": "Introduction to mathematical modeling of computational problems...",
                "units": 12,
                "level": "U",
                "prerequisites": ["6.100A"],
                "corequisites": [],
                "terms_offered": ["fall", "spring"],
                "meets_requirements": ["REST"],
                "department": "6"
            }
        }


class ScheduledCourse(BaseModel):
    """A course scheduled in a specific term"""
    course: Course
    term: str = Field(..., description="Term identifier (e.g., '2024FA')")
    year: int
    semester: Term
    meeting_times: List[MeetingTime] = Field(default_factory=list)
    instructor: Optional[str] = None
    section: Optional[str] = None
    
    def has_time_conflict(self, other: 'ScheduledCourse') -> bool:
        """Check if this course has time conflicts with another"""
        if self.term != other.term:
            return False
        
        for mt1 in self.meeting_times:
            for mt2 in other.meeting_times:
                if mt1.conflicts_with(mt2):
                    return True
        return False


class ScheduledTerm(BaseModel):
    """All courses in a specific term"""
    year: int
    semester: Term
    courses: List[ScheduledCourse] = Field(default_factory=list)
    
    @property
    def total_units(self) -> int:
        """Calculate total units for this term"""
        return sum(c.course.units for c in self.courses)
    
    @property
    def term_id(self) -> str:
        """Get term identifier (e.g., '2024FA')"""
        semester_codes = {
            Term.FALL: "FA",
            Term.IAP: "IA",
            Term.SPRING: "SP",
            Term.SUMMER: "SU"
        }
        return f"{self.year}{semester_codes[self.semester]}"
    
    def has_conflicts(self) -> List[tuple[str, str]]:
        """Check for time conflicts in this term"""
        conflicts = []
        for i, course1 in enumerate(self.courses):
            for course2 in self.courses[i+1:]:
                if course1.has_time_conflict(course2):
                    conflicts.append((course1.course.id, course2.course.id))
        return conflicts


class Requirement(BaseModel):
    """Degree requirement definition"""
    id: str
    major: str = Field(..., description="Major code (e.g., '6-3')")
    description: str
    rule_type: RequirementType
    
    # For specific course requirements
    courses_allowed: Optional[List[str]] = None
    
    # For category requirements
    category: Optional[str] = None
    units_required: Optional[int] = None
    courses_required: Optional[int] = None
    
    # For flexible requirements
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "6-3-foundation-algorithms",
                "major": "6-3",
                "description": "Foundation requirement in algorithms",
                "rule_type": "specific_course",
                "courses_allowed": ["6.006", "6.046"],
                "metadata": {"category": "foundation"}
            }
        }


class StudentProfile(BaseModel):
    """Student profile and academic history"""
    id: str
    name: Optional[str] = None
    major: str = Field(..., description="Major code (e.g., '6-3', '2-A')")
    minor: Optional[str] = None
    year: int = Field(..., ge=1, le=5, description="Current year (1-5)")
    semester: Term = Field(..., description="Current semester")
    
    # Academic history
    completed_courses: List[str] = Field(
        default_factory=list,
        description="List of completed course IDs"
    )
    in_progress_courses: List[str] = Field(default_factory=list)
    
    # Preferences
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible preferences dictionary"
    )
    
    # Optimization goals (weighted 0-1)
    optimization_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "minimize_mornings": 0.5,
            "balance_workload": 0.8,
            "front_load_major": 0.3,
            "maximize_ratings": 0.6
        }
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "student_123",
                "name": "Alex",
                "major": "6-3",
                "year": 2,
                "semester": "spring",
                "completed_courses": ["6.100A", "18.01", "8.01"],
                "in_progress_courses": ["6.006", "18.02"],
                "preferences": {
                    "avoid_fridays": True,
                    "prefer_afternoon": True,
                    "max_units_per_term": 54
                },
                "optimization_weights": {
                    "minimize_mornings": 0.7,
                    "balance_workload": 0.9
                }
            }
        }


class Schedule(BaseModel):
    """Complete 4-year schedule"""
    student_id: str
    terms: List[ScheduledTerm] = Field(default_factory=list)
    
    @property
    def total_units(self) -> int:
        """Calculate total units across all terms"""
        return sum(term.total_units for term in self.terms)
    
    @property
    def all_courses(self) -> List[str]:
        """Get list of all course IDs in schedule"""
        courses = []
        for term in self.terms:
            courses.extend([c.course.id for c in term.courses])
        return courses
    
    def get_term(self, year: int, semester: Term) -> Optional[ScheduledTerm]:
        """Get a specific term from the schedule"""
        for term in self.terms:
            if term.year == year and term.semester == semester:
                return term
        return None
    
    def validate(self) -> 'ScheduleValidation':
        """Validate schedule against all constraints"""
        # Will be implemented in solver service
        pass


class ScheduleValidation(BaseModel):
    """Results of schedule validation"""
    is_valid: bool
    requirements_satisfied: Dict[str, bool]
    missing_requirements: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class ChatMessage(BaseModel):
    """Chat message for LLM interaction"""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Request to chat endpoint"""
    message: str
    student_id: str
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    include_schedule: bool = Field(
        default=True,
        description="Whether to include current schedule in context"
    )


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    message: str
    function_calls: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Any function calls made during response"
    )
    retrieved_documents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="RAG documents used in response"
    )
    updated_schedule: Optional[Schedule] = None


class ScheduleGenerationRequest(BaseModel):
    """Request to generate a schedule"""
    student_id: str
    optimization_goals: List[str] = Field(
        default_factory=list,
        description="Priority goals like 'minimize_mornings', 'front_load_major'"
    )
    constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional constraints like max_units_per_term"
    )
    fixed_courses: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Courses that must be in specific terms (term_id: [course_ids])"
    )


class ScheduleGenerationResponse(BaseModel):
    """Response from schedule generation"""
    schedule: Schedule
    validation: ScheduleValidation
    generation_time_seconds: float
    optimization_score: float
    explanation: str = Field(
        ...,
        description="LLM-generated explanation of schedule decisions"
    )
