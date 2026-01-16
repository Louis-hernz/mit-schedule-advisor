# MIT Schedule Advisor 🎓

An AI-powered 4-year schedule recommendation system for MIT students, combining Large Language Models (LLMs) with Retrieval-Augmented Generation (RAG) and constraint-based optimization.

## Features

- 💬 **Conversational Interface**: Chat with an AI advisor about your academic plans
- 📚 **Smart RAG System**: Answers questions about courses, requirements, and MIT policies
- 🧩 **Constraint Solver**: Generates valid 4-year schedules considering all requirements
- ⚡ **Real-time Validation**: Checks prerequisites, time conflicts, and degree requirements
- 🎯 **Personalized Optimization**: Balances workload based on your preferences
- 📊 **Schedule Visualization**: Interactive calendar view of your 4-year plan

## Architecture

```
Frontend (Lovable/React) ←→ Backend (FastAPI) ←→ MIT APIs
                                    ↓
                              RAG (ChromaDB)
                                    ↓
                              LLM (OpenAI GPT-4)
                                    ↓
                           Solver (OR-Tools)
```

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **LangChain**: LLM orchestration and RAG
- **ChromaDB**: Vector database for embeddings
- **OpenAI API**: GPT-4 and embeddings
- **OR-Tools**: Constraint programming solver
- **Redis**: Caching layer

### Frontend
- **Lovable**: No-code React development
- **TypeScript**: Type-safe frontend code
- **Tailwind CSS**: Styling
- **React Query**: API state management

### Deployment
- **Railway**: Backend hosting
- **Lovable**: Frontend hosting

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (for ChromaDB and Redis)
- OpenAI API key
- MIT API access (optional, for production data)

### Backend Setup

1. **Clone and navigate to backend**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

5. **Start required services**:
   ```bash
   # ChromaDB
   docker run -d -p 8000:8000 chromadb/chroma
   
   # Redis
   docker run -d -p 6379:6379 redis
   ```

6. **Initialize data** (loads MIT courses into RAG):
   ```bash
   python -m scripts.init_data
   ```

7. **Run the server**:
   ```bash
   uvicorn app.main:app --reload
   ```

   API will be available at `http://localhost:8000`
   API docs at `http://localhost:8000/docs`

### Frontend Setup

1. **Create project on Lovable**:
   - Go to https://lovable.dev
   - Create new project: "MIT Schedule Advisor"

2. **Connect to backend**:
   - Set `VITE_API_URL` to your backend URL
   - For local development: `http://localhost:8000`

3. **Deploy and test**:
   - Lovable auto-deploys on save
   - Access your app at the provided Lovable URL

## Project Structure

```
mit-schedule-advisor/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── endpoints/      # API route handlers
│   │   ├── core/               # Configuration
│   │   ├── models/             # Pydantic models
│   │   ├── services/
│   │   │   ├── rag/           # RAG pipeline
│   │   │   ├── solver/        # Schedule solver
│   │   │   └── scraper/       # Web scraper
│   │   └── utils/             # Helper functions
│   ├── tests/                 # Unit tests
│   ├── scripts/               # Utility scripts
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  # Lovable project
├── ARCHITECTURE.md           # Detailed system design
└── IMPLEMENTATION_GUIDE.md   # Step-by-step guide
```

## API Endpoints

### Chat
- `POST /api/chat` - Send message to AI advisor

### Schedule
- `POST /api/schedule/generate` - Generate 4-year schedule
- `GET /api/schedule/{student_id}` - Get student's schedule
- `POST /api/schedule/validate` - Validate schedule

### Courses
- `GET /api/courses/search` - Search courses
- `GET /api/courses/{course_id}` - Get course details

### Student
- `POST /api/student/profile` - Create student profile
- `GET /api/student/profile/{id}` - Get student profile

## Usage Examples

### 1. Chat with AI Advisor

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What courses should I take for the 6-3 major?",
    "student_id": "student_123"
  }'
```

### 2. Generate Schedule

```bash
curl -X POST http://localhost:8000/api/schedule/generate \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student_123",
    "optimization_goals": ["minimize_mornings", "balance_workload"],
    "constraints": {"max_units_per_term": 54}
  }'
```

### 3. Search Courses

```bash
curl "http://localhost:8000/api/courses/search?q=algorithms&department=6"
```

## Development

### Running Tests

```bash
cd backend
pytest
```

### Adding New Requirements

Edit `backend/requirements.txt` and run:
```bash
pip install -r requirements.txt
```

### Database Migrations

To reset the RAG database:
```bash
python -m scripts.reset_rag
```

### Debugging

Enable debug mode in `.env`:
```bash
DEBUG=True
```

Logs will show detailed information about:
- API requests/responses
- RAG retrieval process
- Solver decisions
- LLM interactions

## Deployment

### Backend (Railway)

1. **Install Railway CLI**:
   ```bash
   npm install -g @railway/cli
   ```

2. **Login and initialize**:
   ```bash
   railway login
   railway init
   ```

3. **Add environment variables** in Railway dashboard:
   - Copy all variables from `.env.example`
   - Add your production values

4. **Deploy**:
   ```bash
   railway up
   ```

5. **Add services**:
   - Redis: Use Railway Redis plugin
   - ChromaDB: Deploy as separate service

### Frontend (Lovable)

Frontend is automatically deployed by Lovable on every save.

Update the `VITE_API_URL` to point to your Railway backend URL.

## Configuration

Key settings in `.env`:

```bash
# Must configure
OPENAI_API_KEY=sk-...           # Required
MIT_COURSES_API_KEY=...         # Optional for testing

# Can customize
RAG_TOP_K=5                     # Number of retrieved documents
SOLVER_TIMEOUT_SECONDS=30       # Max solving time
DEFAULT_MAX_UNITS_PER_TERM=60   # Credit limit
```

## Troubleshooting

### ChromaDB Connection Error

```bash
# Make sure ChromaDB is running
docker ps | grep chroma

# Restart if needed
docker restart <chroma-container-id>
```

### Redis Connection Error

```bash
# Check Redis status
docker ps | grep redis

# Test connection
redis-cli ping
```

### OpenAI API Errors

- Check your API key in `.env`
- Verify you have credits: https://platform.openai.com/usage
- Check rate limits

### Slow Schedule Generation

- Reduce `SOLVER_MAX_TERMS`
- Increase `SOLVER_TIMEOUT_SECONDS`
- Simplify optimization goals

## Contributing

This is a course project, but suggestions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Resources

- [Architecture Document](./ARCHITECTURE.md)
- [Implementation Guide](./IMPLEMENTATION_GUIDE.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Lovable Documentation](https://docs.lovable.dev/)

## License

MIT License - See LICENSE file for details

## Contact

For questions or issues, please open an issue on GitHub.

## Acknowledgments

- MIT for providing course data APIs
- Anthropic for Claude (used in development)
- OpenAI for GPT-4 and embeddings
- The open-source community

---

Built with ❤️ for MIT students
