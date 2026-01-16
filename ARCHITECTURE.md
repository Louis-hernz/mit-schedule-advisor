# MIT Schedule Recommendation Tool - Architecture

## System Overview

A RAG-powered schedule recommendation tool for MIT students that combines LLM reasoning with constraint-based solving.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Lovable)                      │
│                    React + TypeScript                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Chat Interface  │  Schedule View  │  Profile Manager  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                  Backend (FastAPI + Python)                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              LLM Orchestration Layer                    │ │
│  │  - OpenAI GPT-4 API                                    │ │
│  │  - LangChain for prompt management                     │ │
│  │  - Function calling for solver integration             │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   RAG Pipeline                          │ │
│  │  - ChromaDB (vector store)                             │ │
│  │  - OpenAI embeddings (text-embedding-3-small)          │ │
│  │  - Document retrieval & ranking                        │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Schedule Solver Engine                     │ │
│  │  - Constraint satisfaction solver                       │ │
│  │  - Multi-objective optimization                         │ │
│  │  - Conflict detection & resolution                      │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  Data Layer                             │ │
│  │  - MIT Courses API client                              │ │
│  │  - MIT Course Catalog API client                       │ │
│  │  - Web scraper (course evaluations)                    │ │
│  │  - Caching layer (Redis)                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend (Lovable - React + TypeScript)

**Pages/Components:**
- **Chat Interface**: Main conversational UI for interacting with the RAG system
- **Schedule Visualizer**: Calendar view showing generated 4-year plan
- **Profile Setup**: Student information collection
- **Course Browser**: Search and explore MIT courses
- **Requirements Tracker**: Visual progress on major requirements

**State Management:**
- React Query for API state
- Zustand for local state (user profile, current schedule)

### 2. Backend API (FastAPI)

**Core Endpoints:**

```python
POST   /api/chat                    # Chat with LLM + RAG
POST   /api/schedule/generate       # Generate full 4-year schedule
GET    /api/schedule/{student_id}   # Get student's schedule
PUT    /api/schedule/{student_id}   # Update schedule
POST   /api/schedule/validate       # Validate schedule against rules
GET    /api/courses/search          # Search courses
GET    /api/courses/{course_id}     # Get course details
GET    /api/requirements/{major}    # Get major requirements
POST   /api/student/profile         # Create/update student profile
GET    /api/student/profile/{id}    # Get student profile
```

### 3. RAG Pipeline

**Document Sources:**
1. **Course Descriptions** (from mit-courses API)
   - Full course catalog with descriptions
   - Prerequisites, corequisites
   - Course numbers and titles

2. **Major Requirements** (from course catalog + scraped data)
   - Degree requirements by major
   - Distribution requirements (HASS, REST, etc.)
   - Sample 4-year plans

3. **Course Scheduling Info** (from mit-course-catalog API)
   - Term offerings (Fall/Spring/IAP)
   - Meeting times
   - Instructors

4. **MIT-Specific Knowledge Base**
   - Terminology (units, CI-H, REST, etc.)
   - Academic policies
   - Common student patterns

5. **Course Reviews** (scraped)
   - Difficulty ratings
   - Time commitment
   - Student recommendations

**Embedding Strategy:**
- Chunk documents by semantic units (course, requirement, policy)
- Metadata filtering (major, course level, term)
- Hybrid search (semantic + keyword)

**Retrieval Process:**
```python
1. User query → OpenAI embedding
2. ChromaDB similarity search with metadata filters
3. Rerank results by relevance
4. Include in LLM context with structured format
```

### 4. LLM Orchestration

**Prompt Structure:**
```
System: You are an MIT academic advisor assistant...
Context: [Retrieved course info, requirements, student profile]
Tools: [schedule_solver, validate_requirement, search_courses]
User Query: [Student's question/request]
```

**Function Calling Tools:**
1. `generate_schedule(constraints, preferences)` → Invoke solver
2. `validate_requirement(course, requirement)` → Check if course satisfies requirement
3. `search_courses(query, filters)` → Search course database
4. `get_course_details(course_id)` → Fetch full course info
5. `check_prerequisites(course_id, completed_courses)` → Validate prerequisites

### 5. Schedule Solver Engine

**Algorithm: Constraint Satisfaction + Optimization**

**Hard Constraints:**
- Major requirements must be satisfied
- Prerequisites must be taken before dependent courses
- No time conflicts within a term
- Credit limits (typically 48-60 units/term)
- Course offerings (not all courses every semester)

**Soft Constraints (Preferences):**
- Minimize early morning classes
- Balance workload across terms
- Front-load/back-load major requirements
- Prefer certain terms for certain courses
- Time for UROP/extracurriculars

**Optimization Objectives:**
- User-specified priorities (weighted)
- Minimize total difficulty spikes
- Maximize schedule flexibility
- Prefer highly-rated courses

**Implementation:**
```python
class ScheduleSolver:
    def solve(self, 
             student_profile: StudentProfile,
             constraints: List[Constraint],
             preferences: Dict[str, float]) -> Schedule:
        """
        Uses backtracking with forward checking
        and constraint propagation
        """
        pass
```

### 6. Data Layer

**API Clients:**

```python
class MITCoursesClient:
    base_url = "https://mit-courses-v1.cloudhub.io/courses/v1"
    
    async def get_all_courses(self) -> List[Course]:
        """Fetch all courses from catalog"""
        
class MITCourseCatalogClient:
    base_url = "https://mit-course-catalog-v2.cloudhub.io/coursecatalog/v2"
    
    async def get_term_subjects(self, term: str) -> List[Subject]:
        """Get all subjects offered in a term"""
        
    async def get_subject_details(self, term: str, subject_id: str) -> Subject:
        """Get detailed info for a specific subject"""
```

**Web Scraper:**
- Target: MIT Course Evaluations (if publicly accessible)
- Backup: MIT OpenCourseWare for course info
- Store: Structured JSON in ChromaDB with metadata

**Caching Strategy:**
- Redis for API responses (24hr TTL for course data)
- ChromaDB for embeddings (persistent)
- In-memory cache for frequent queries

## Data Models

```python
from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum

class Term(str, Enum):
    FALL = "fall"
    IAP = "iap"
    SPRING = "spring"

class CourseLevel(str, Enum):
    UNDERGRAD = "U"
    GRAD = "G"

class Course(BaseModel):
    id: str  # e.g., "6.006"
    title: str
    description: str
    units: int
    level: CourseLevel
    prerequisites: List[str]
    corequisites: List[str]
    terms_offered: List[Term]
    meets_requirements: List[str]  # e.g., ["REST", "CI-M"]
    
class ScheduledCourse(BaseModel):
    course: Course
    term: str  # e.g., "2024FA"
    year: int
    semester: Term
    meeting_times: List[MeetingTime]
    
class MeetingTime(BaseModel):
    days: List[str]  # ["Monday", "Wednesday", "Friday"]
    start_time: str
    end_time: str
    location: Optional[str]

class StudentProfile(BaseModel):
    id: str
    major: str  # e.g., "6-3"
    year: int  # 1-4
    semester: Term
    completed_courses: List[str]
    in_progress_courses: List[str]
    preferences: Dict[str, any]  # flexible preferences
    
class Requirement(BaseModel):
    id: str
    major: str
    description: str
    rule_type: str  # "specific_course", "category", "units"
    courses_allowed: Optional[List[str]]
    category: Optional[str]
    units_required: Optional[int]
    
class Schedule(BaseModel):
    student_id: str
    terms: List[ScheduledTerm]
    total_units: int
    requirements_satisfied: Dict[str, bool]
    warnings: List[str]
    
class ScheduledTerm(BaseModel):
    year: int
    semester: Term
    courses: List[ScheduledCourse]
    total_units: int
```

## RAG Implementation Strategy

### Document Preparation

1. **Fetch all courses** from MIT Courses API
2. **Fetch term schedules** from MIT Course Catalog API for recent terms
3. **Scrape course evaluations** (if available)
4. **Create embeddings** for:
   - Course descriptions
   - Requirement descriptions
   - MIT policy documents
   - Course reviews

### ChromaDB Collections

```python
# Collection 1: Courses
{
    "id": "6.006",
    "document": "Introduction to Algorithms. Studies efficient algorithms...",
    "metadata": {
        "course_id": "6.006",
        "title": "Introduction to Algorithms",
        "level": "U",
        "department": "6",
        "units": 12,
        "terms_offered": ["fall", "spring"]
    }
}

# Collection 2: Requirements
{
    "id": "6-3-foundation-1",
    "document": "Foundation requirement: Students must complete 6.006...",
    "metadata": {
        "major": "6-3",
        "requirement_type": "foundation",
        "category": "algorithms"
    }
}

# Collection 3: MIT Knowledge
{
    "id": "rest-requirement",
    "document": "REST (Restricted Elective in Science and Technology)...",
    "metadata": {
        "type": "policy",
        "category": "general_requirements"
    }
}
```

### Query Pipeline

```python
async def query_rag(
    query: str,
    student_profile: StudentProfile,
    k: int = 5
) -> List[Document]:
    """
    1. Generate embedding for query
    2. Search ChromaDB with metadata filters
    3. Rerank by relevance
    4. Return top-k documents
    """
    
    # Add context from student profile
    filters = {
        "major": student_profile.major,
        "level": "U" if student_profile.year <= 4 else "G"
    }
    
    results = chroma_collection.query(
        query_embeddings=[embed(query)],
        n_results=k * 2,  # Over-fetch for reranking
        where=filters
    )
    
    # Rerank based on student context
    reranked = rerank_results(results, student_profile)
    
    return reranked[:k]
```

## LLM Integration

### System Prompt Template

```
You are an expert MIT academic advisor helping students plan their 4-year schedule.

CONTEXT:
Student: {student_name}, {major}, Year {year}
Completed: {completed_courses}
Requirements remaining: {remaining_requirements}

RELEVANT INFORMATION:
{rag_context}

CAPABILITIES:
- Answer questions about course requirements
- Explain whether specific courses satisfy requirements
- Generate and optimize 4-year schedules
- Validate schedules against all constraints
- Provide advice on course selection

When generating schedules, ALWAYS use the schedule_solver tool.
When validating requirements, use structured rules first, then explain with RAG context.
Be specific and cite course numbers when relevant.
```

### Function Calling Examples

```python
# Function 1: Generate Schedule
{
    "name": "generate_schedule",
    "description": "Generate a complete 4-year schedule for the student",
    "parameters": {
        "type": "object",
        "properties": {
            "optimization_goals": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Priority goals, e.g., ['minimize_mornings', 'front_load_major']"
            },
            "constraints": {
                "type": "object",
                "description": "Additional constraints like max_units_per_term"
            }
        }
    }
}

# Function 2: Validate Requirement
{
    "name": "validate_requirement",
    "description": "Check if a course satisfies a specific requirement",
    "parameters": {
        "type": "object",
        "properties": {
            "course_id": {"type": "string"},
            "requirement_id": {"type": "string"}
        }
    }
}
```

## Deployment Architecture (Railway)

```yaml
# railway.toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"

[[services]]
name = "api"
source = "backend"

[[services]]
name = "chromadb"
source = "chromadb/chromadb"
```

**Services:**
1. **Backend API** - Main FastAPI application
2. **ChromaDB** - Vector database (can use Railway volume)
3. **Redis** - Caching layer (Railway Redis addon)

**Environment Variables:**
```
OPENAI_API_KEY=...
MIT_COURSES_API_KEY=...
MIT_CATALOG_API_KEY=...
REDIS_URL=...
CHROMA_HOST=...
```

## Development Phases

### Phase 1: Data Pipeline (Week 1)
- [ ] Set up API clients for MIT APIs
- [ ] Implement web scraper for course evaluations
- [ ] Process and structure data
- [ ] Set up ChromaDB and create embeddings
- [ ] Test data retrieval

### Phase 2: RAG System (Week 1-2)
- [ ] Implement RAG query pipeline
- [ ] Create prompt templates
- [ ] Integrate OpenAI API
- [ ] Test retrieval quality
- [ ] Add metadata filtering

### Phase 3: Solver Engine (Week 2)
- [ ] Implement constraint satisfaction solver
- [ ] Add requirement validation logic
- [ ] Build optimization framework
- [ ] Test with sample schedules

### Phase 4: API Development (Week 2-3)
- [ ] Build FastAPI backend
- [ ] Implement all endpoints
- [ ] Add function calling integration
- [ ] Test LLM + Solver integration

### Phase 5: Frontend (Week 3)
- [ ] Set up Lovable project
- [ ] Build chat interface
- [ ] Create schedule visualizer
- [ ] Add profile management

### Phase 6: Deployment (Week 3-4)
- [ ] Set up Railway project
- [ ] Configure environment
- [ ] Deploy and test
- [ ] Monitor and optimize

## Success Metrics

1. **RAG Quality:**
   - Relevant context retrieval >90%
   - Accurate requirement interpretation >95%

2. **Solver Performance:**
   - Generate valid schedule in <10 seconds
   - Satisfy all hard constraints 100%
   - User satisfaction with preferences >80%

3. **User Experience:**
   - Chat response time <3 seconds
   - Schedule generation <10 seconds
   - User adoption and retention

## Future Enhancements

1. **Advanced Features:**
   - Course recommendation based on interests
   - GPA prediction
   - Career path optimization
   - Friend schedule coordination

2. **Data Improvements:**
   - Real historical enrollment data
   - Professor ratings integration
   - Live course availability

3. **AI Enhancements:**
   - Fine-tuned model on MIT data
   - Multi-agent reasoning
   - Proactive schedule suggestions
