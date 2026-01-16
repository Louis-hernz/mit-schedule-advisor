# MIT Schedule Advisor - Implementation Guide

## What We've Built So Far

### ✅ Completed Components

1. **Project Architecture** (`ARCHITECTURE.md`)
   - Complete system design
   - Component breakdown
   - Data models
   - Deployment strategy

2. **Data Models** (`backend/app/models/schemas.py`)
   - Course, Requirement, Schedule models
   - Student profile management
   - Chat and API request/response models
   - Validation logic

3. **Configuration** (`backend/app/core/config.py`)
   - Environment-based settings
   - API configurations
   - RAG and solver parameters

4. **MIT API Clients** (`backend/app/services/mit_api.py`)
   - MITCoursesClient - fetch course catalog
   - MITCourseCatalogClient - fetch term schedules
   - Retry logic and error handling

5. **RAG Service** (`backend/app/services/rag/rag_service.py`)
   - ChromaDB integration
   - OpenAI embeddings
   - Document indexing and retrieval
   - Multi-collection querying

## Next Steps

### Phase 1: Complete Core Backend (Priority: HIGH)

#### 1.1 Schedule Solver Engine
**File**: `backend/app/services/solver/schedule_solver.py`

```python
class ScheduleSolver:
    """
    Constraint satisfaction solver for schedule generation
    
    Implementation approach:
    - Use OR-Tools CP-SAT solver for constraint programming
    - Model as optimization problem with hard/soft constraints
    - Backtracking search with forward checking
    """
    
    def solve(
        self,
        student_profile: StudentProfile,
        requirements: List[Requirement],
        available_courses: List[Course],
        preferences: Dict[str, float]
    ) -> Schedule:
        """
        Main solving method
        
        Steps:
        1. Load all requirements for major
        2. Build constraint model
        3. Add hard constraints (prereqs, conflicts, requirements)
        4. Add soft constraints (preferences)
        5. Solve with timeout
        6. Convert solution to Schedule object
        """
        pass
    
    def validate_schedule(
        self,
        schedule: Schedule,
        requirements: List[Requirement]
    ) -> ScheduleValidation:
        """Validate a schedule against all requirements"""
        pass
```

**Key constraints to implement**:
- Prerequisites must be satisfied
- No time conflicts within terms
- Credit limits per term
- All major requirements met
- Course offerings respected

#### 1.2 LLM Orchestration Service
**File**: `backend/app/services/llm_service.py`

```python
class LLMService:
    """
    Orchestrates LLM interactions with RAG and function calling
    """
    
    async def chat(
        self,
        message: str,
        student_profile: StudentProfile,
        conversation_history: List[ChatMessage],
        current_schedule: Optional[Schedule] = None
    ) -> ChatResponse:
        """
        Process chat message with RAG context
        
        Steps:
        1. Query RAG for relevant context
        2. Build prompt with context + student info
        3. Call OpenAI with function definitions
        4. Handle function calls (e.g., invoke solver)
        5. Return response with any schedule updates
        """
        pass
    
    async def explain_schedule(
        self,
        schedule: Schedule,
        student_profile: StudentProfile
    ) -> str:
        """Generate natural language explanation of schedule"""
        pass
    
    async def answer_requirement_question(
        self,
        question: str,
        student_profile: StudentProfile
    ) -> str:
        """Answer questions about requirements using RAG"""
        pass
```

**Function definitions for OpenAI**:
- `generate_schedule`: Invoke solver
- `validate_requirement`: Check if course satisfies requirement  
- `search_courses`: Query course database
- `check_prerequisites`: Validate prerequisites

#### 1.3 Web Scraper
**File**: `backend/app/services/scraper/course_evaluations_scraper.py`

```python
class CourseEvaluationsScraper:
    """
    Scrape MIT course evaluations and reviews
    
    Target sources:
    - MIT Course Evaluations (if public)
    - MIT OpenCourseWare
    - Reddit r/MIT (carefully!)
    """
    
    async def scrape_course_reviews(
        self,
        course_id: str
    ) -> Dict[str, Any]:
        """
        Scrape reviews for a course
        
        Returns:
        {
            "difficulty_rating": 4.2,
            "time_commitment_hours": 15.5,
            "student_rating": 4.7,
            "reviews": ["Great class!", "Very challenging"],
            "common_terms": ["hard", "rewarding", "project-heavy"]
        }
        """
        pass
```

**Important**: Respect robots.txt and rate limits!

#### 1.4 FastAPI Application
**File**: `backend/app/main.py`

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.api.endpoints import chat, courses, schedule, student

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"])
app.include_router(student.router, prefix="/api/student", tags=["student"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**API Endpoints to implement**:

```python
# backend/app/api/endpoints/chat.py
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with LLM + RAG"""
    pass

# backend/app/api/endpoints/schedule.py
@router.post("/generate", response_model=ScheduleGenerationResponse)
async def generate_schedule(request: ScheduleGenerationRequest):
    """Generate 4-year schedule"""
    pass

@router.post("/validate", response_model=ScheduleValidation)
async def validate_schedule(schedule: Schedule):
    """Validate a schedule"""
    pass

# backend/app/api/endpoints/courses.py
@router.get("/search")
async def search_courses(q: str, department: Optional[str] = None):
    """Search courses"""
    pass

@router.get("/{course_id}")
async def get_course(course_id: str):
    """Get course details"""
    pass

# backend/app/api/endpoints/student.py
@router.post("/profile", response_model=StudentProfile)
async def create_profile(profile: StudentProfile):
    """Create student profile"""
    pass

@router.get("/profile/{student_id}")
async def get_profile(student_id: str):
    """Get student profile"""
    pass
```

### Phase 2: Data Pipeline & Population

#### 2.1 Data Initialization Script
**File**: `backend/scripts/init_data.py`

```python
"""
Script to initialize RAG database with MIT course data
"""
import asyncio
from app.services.mit_api import MITCoursesClient, MITCourseCatalogClient
from app.services.rag.rag_service import RAGService
from app.services.scraper.course_evaluations_scraper import CourseEvaluationsScraper

async def init_course_data():
    """Fetch and index all MIT courses"""
    courses_client = MITCoursesClient()
    rag_service = RAGService()
    
    try:
        # Fetch all courses
        print("Fetching courses from MIT API...")
        courses = await courses_client.get_all_courses()
        print(f"Found {len(courses)} courses")
        
        # Add to RAG
        print("Adding courses to vector database...")
        await rag_service.add_courses_batch(courses)
        print("Done!")
        
    finally:
        await courses_client.close()

async def scrape_and_index_reviews():
    """Scrape course reviews and add to RAG"""
    scraper = CourseEvaluationsScraper()
    rag_service = RAGService()
    
    # Scrape reviews for popular courses
    popular_courses = ["6.006", "6.046", "18.06", "8.01", "8.02"]
    
    for course_id in popular_courses:
        try:
            reviews = await scraper.scrape_course_reviews(course_id)
            # Add to knowledge base
            await rag_service.add_knowledge(
                doc_id=f"reviews_{course_id}",
                text=f"Course {course_id} reviews: {reviews}",
                metadata={"type": "reviews", "course_id": course_id}
            )
        except Exception as e:
            print(f"Error scraping {course_id}: {e}")

async def init_mit_knowledge():
    """Add MIT-specific knowledge to RAG"""
    rag_service = RAGService()
    
    knowledge_docs = [
        {
            "id": "rest_requirement",
            "text": "REST (Restricted Elective in Science and Technology): Students must complete 2 subjects from the REST requirement list...",
            "metadata": {"type": "policy", "category": "requirements"}
        },
        {
            "id": "ci_requirement",
            "text": "CI-H (Communication Intensive - Humanities): All students must complete 4 CI subjects, at least 2 of which must be CI-H...",
            "metadata": {"type": "policy", "category": "requirements"}
        },
        # Add more MIT knowledge...
    ]
    
    for doc in knowledge_docs:
        await rag_service.add_knowledge(
            doc_id=doc["id"],
            text=doc["text"],
            metadata=doc["metadata"]
        )

if __name__ == "__main__":
    asyncio.run(init_course_data())
    asyncio.run(scrape_and_index_reviews())
    asyncio.run(init_mit_knowledge())
```

Run with:
```bash
cd backend
python -m scripts.init_data
```

### Phase 3: Frontend Development (Lovable)

#### 3.1 Setup Lovable Project

1. Go to https://lovable.dev
2. Create new project: "MIT Schedule Advisor"
3. Set up project structure:

```
/src
  /components
    /chat
      ChatInterface.tsx
      MessageBubble.tsx
      InputBar.tsx
    /schedule
      ScheduleView.tsx
      TermCard.tsx
      CourseCard.tsx
    /profile
      ProfileSetup.tsx
      PreferencesForm.tsx
    /courses
      CourseBrowser.tsx
      CourseDetails.tsx
  /lib
    api.ts           # API client
    types.ts         # TypeScript types
  /pages
    index.tsx        # Main chat page
    schedule.tsx     # Schedule view
    profile.tsx      # Profile setup
```

#### 3.2 API Client
**File**: `frontend/src/lib/api.ts`

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  chat: {
    send: async (message: string, studentId: string, history: ChatMessage[]) => {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, student_id: studentId, conversation_history: history })
      });
      return response.json();
    }
  },
  
  schedule: {
    generate: async (studentId: string, goals: string[], constraints: any) => {
      const response = await fetch(`${API_BASE_URL}/api/schedule/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, optimization_goals: goals, constraints })
      });
      return response.json();
    },
    
    get: async (studentId: string) => {
      const response = await fetch(`${API_BASE_URL}/api/schedule/${studentId}`);
      return response.json();
    }
  },
  
  courses: {
    search: async (query: string, filters?: any) => {
      const params = new URLSearchParams({ q: query, ...filters });
      const response = await fetch(`${API_BASE_URL}/api/courses/search?${params}`);
      return response.json();
    }
  },
  
  student: {
    createProfile: async (profile: StudentProfile) => {
      const response = await fetch(`${API_BASE_URL}/api/student/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile)
      });
      return response.json();
    }
  }
};
```

#### 3.3 Main Chat Component
**File**: `frontend/src/components/chat/ChatInterface.tsx`

```typescript
import { useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { InputBar } from './InputBar';
import { api } from '@/lib/api';

export function ChatInterface({ studentId }: { studentId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async (message: string) => {
    // Add user message
    const userMsg = { role: 'user', content: message };
    setMessages(prev => [...prev, userMsg]);
    
    setIsLoading(true);
    try {
      // Call API
      const response = await api.chat.send(message, studentId, messages);
      
      // Add assistant response
      const assistantMsg = { role: 'assistant', content: response.message };
      setMessages(prev => [...prev, assistantMsg]);
      
      // If schedule was updated, show it
      if (response.updated_schedule) {
        // Navigate to schedule view or show inline
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {isLoading && <div>Thinking...</div>}
      </div>
      <InputBar onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
```

### Phase 4: Testing & Deployment

#### 4.1 Backend Tests
**File**: `backend/tests/test_solver.py`

```python
import pytest
from app.services.solver.schedule_solver import ScheduleSolver
from app.models.schemas import StudentProfile, Course, Term

def test_schedule_generation():
    """Test basic schedule generation"""
    solver = ScheduleSolver()
    
    profile = StudentProfile(
        id="test_student",
        major="6-3",
        year=1,
        semester=Term.FALL,
        completed_courses=[]
    )
    
    # Mock requirements and courses
    requirements = [...]
    courses = [...]
    
    schedule = solver.solve(profile, requirements, courses, {})
    
    assert schedule is not None
    assert len(schedule.terms) > 0
    assert schedule.total_units >= 180  # Typical degree requirement
```

#### 4.2 Environment Setup
**File**: `backend/.env.example`

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# MIT APIs
MIT_COURSES_API_KEY=
MIT_CATALOG_API_KEY=

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Redis
REDIS_URL=redis://localhost:6379

# Settings
DEBUG=True
OPENAI_MODEL=gpt-4-turbo-preview
```

#### 4.3 Railway Deployment

1. **Create Railway Project**
   ```bash
   railway init
   railway add
   ```

2. **Add Services**
   - Backend API (from GitHub)
   - Redis (Railway plugin)
   - ChromaDB (Docker deployment)

3. **Set Environment Variables** in Railway dashboard

4. **Deploy**
   ```bash
   railway up
   ```

5. **Configure Frontend** in Lovable to point to Railway URL

## Development Workflow

### 1. Set Up Environment

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Copy and configure .env
cp .env.example .env
# Edit .env with your API keys

# Start ChromaDB (Docker)
docker run -p 8000:8000 chromadb/chroma

# Start Redis (Docker)
docker run -p 6379:6379 redis

# Run backend
uvicorn app.main:app --reload
```

### 2. Initialize Data

```bash
python -m scripts.init_data
```

### 3. Test API

```bash
# Run tests
pytest

# Manual testing
curl http://localhost:8000/health
```

### 4. Develop Frontend

In Lovable:
1. Connect to backend API
2. Build chat interface
3. Add schedule visualization
4. Test end-to-end

## Key Implementation Tips

### For Solver
- Start with simple greedy algorithm
- Add constraints incrementally
- Use OR-Tools for production
- Cache computed schedules

### For RAG
- Index courses incrementally
- Use metadata filtering heavily
- Implement smart reranking
- Cache embeddings

### For LLM
- Keep prompts concise
- Use function calling for structured tasks
- Include relevant context only
- Handle rate limits gracefully

### For Frontend
- Use React Query for API state
- Implement optimistic updates
- Add loading skeletons
- Handle errors gracefully

## Timeline Estimate

- **Week 1**: Complete solver + LLM service
- **Week 2**: API endpoints + data pipeline
- **Week 3**: Frontend development
- **Week 4**: Testing + deployment

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [ChromaDB Docs](https://docs.trychroma.com/)
- [OpenAI API](https://platform.openai.com/docs)
- [OR-Tools](https://developers.google.com/optimization)
- [Lovable Docs](https://docs.lovable.dev/)
- [Railway Docs](https://docs.railway.app/)

## Questions?

If you run into issues:
1. Check logs (`loguru` automatically logs to console)
2. Verify API keys in `.env`
3. Ensure all services (ChromaDB, Redis) are running
4. Test components individually before integration
