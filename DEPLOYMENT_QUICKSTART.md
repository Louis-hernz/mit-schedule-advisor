# 🚀 Quick Deployment Guide

## ✅ What You Have Now

All the core backend is complete! Here's what's ready:

### New Files to Add:
1. **llm_service.py** → `backend/app/services/llm_service.py`
2. **chat.py** → `backend/app/api/endpoints/chat.py`
3. **student.py** → `backend/app/api/endpoints/student.py`
4. **courses.py** → `backend/app/api/endpoints/courses.py`
5. **main_updated.py** → Replace `backend/app/main.py` with this
6. **init_data.py** → `backend/scripts/init_data.py`
7. **SCRAPING_STRATEGY.md** → `mit-schedule-advisor/SCRAPING_STRATEGY.md`

## 🎯 Path to Deployment (4-6 hours)

### Step 1: Complete Backend Setup (30 min)

```powershell
# 1. Add new files to project
# Copy the 7 files above to their correct locations

# 2. Verify structure
cd mit-schedule-advisor\backend
ls app\services\llm_service.py  # Should exist
ls app\api\endpoints\chat.py     # Should exist

# 3. Install dependencies
.\venv\Scripts\Activate
pip install -r requirements.txt

# 4. Configure environment
# Edit .env and add:
#   OPENAI_API_KEY=your_key_here
```

### Step 2: Start Services (10 min)

```powershell
# Terminal 1: ChromaDB
docker run -d -p 8000:8000 --name chroma chromadb/chroma

# If you don't have Docker:
# Download from: https://docs.trychroma.com/getting-started
# Or skip Redis/Chroma for now and we'll add later
```

### Step 3: Initialize Data (5 min)

```powershell
cd backend
python -m scripts.init_data
```

This will:
- Create mock course data
- Index in vector database
- Add MIT knowledge base
- Add requirements

### Step 4: Test Backend (10 min)

```powershell
# Start server
python -m uvicorn app.main:app --reload

# In another terminal, test:
curl http://localhost:8000/health

# Visit API docs:
# Open browser: http://localhost:8000/docs
```

Try these endpoints in the docs:
1. POST /api/student/profile - Create a student
2. POST /api/chat - Send a message
3. GET /api/courses/search?q=algorithms

### Step 5: Build Frontend with Lovable (3-4 hours)

#### 5.1 Create Lovable Project
1. Go to https://lovable.dev
2. Create new project: "MIT Schedule Advisor"
3. Use these components...

#### 5.2 Main Components

**App.tsx**:
```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import ChatPage from './pages/ChatPage'
import ProfilePage from './pages/ProfilePage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
    </BrowserRouter>
  )
}
```

**src/lib/api.ts** (Already provided in IMPLEMENTATION_GUIDE.md)

**ChatPage.tsx**:
```typescript
import { useState } from 'react'
import { api } from '@/lib/api'

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const studentId = 'student_123' // Get from auth later

  const sendMessage = async () => {
    if (!input.trim()) return
    
    setMessages(prev => [...prev, { role: 'user', content: input }])
    setLoading(true)
    
    try {
      const response = await api.chat.send(input, studentId, messages)
      setMessages(prev => [...prev, { role: 'assistant', content: response.message }])
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
      setInput('')
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">MIT Schedule Advisor</h1>
      
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((msg, i) => (
          <div key={i} className={`p-4 rounded ${msg.role === 'user' ? 'bg-blue-100 ml-12' : 'bg-gray-100 mr-12'}`}>
            {msg.content}
          </div>
        ))}
        {loading && <div>Thinking...</div>}
      </div>
      
      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && sendMessage()}
          placeholder="Ask about courses, requirements, or schedules..."
          className="flex-1 p-2 border rounded"
        />
        <button onClick={sendMessage} className="px-4 py-2 bg-blue-500 text-white rounded">
          Send
        </button>
      </div>
    </div>
  )
}
```

### Step 6: Deploy to Railway (1 hour)

#### 6.1 Backend Deployment

```powershell
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize
cd mit-schedule-advisor\backend
railway init

# Link to GitHub (optional but recommended)
# Push your code to GitHub first
railway link
```

#### 6.2 Configure Railway

In Railway dashboard:
1. Add environment variables (copy from .env)
2. Add Redis service (Railway plugin)
3. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Deploy!

#### 6.3 Frontend Deployment

Lovable auto-deploys! Just:
1. Update API URL in Lovable settings
2. Change VITE_API_URL to your Railway URL
3. Save - it deploys automatically!

## 🎯 MVP Feature Checklist

- [x] Backend API with all endpoints
- [x] RAG system working
- [x] LLM integration with function calling
- [x] Data initialization
- [ ] Frontend chat interface (3-4 hrs in Lovable)
- [ ] Frontend profile setup (1 hr in Lovable)
- [ ] Backend deployed to Railway (1 hr)
- [ ] Frontend deployed (auto by Lovable)

## ⏱️ Time Estimate

- Backend completion: **1 hour** (just adding files & testing)
- Frontend in Lovable: **3-4 hours**
- Deployment: **1 hour**
- **Total: 5-6 hours to working MVP!**

## 🐛 If Something Breaks

### ChromaDB won't start
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process if needed
taskkill /PID <process_id> /F

# Restart ChromaDB
docker restart chroma
```

### OpenAI API errors
- Check your API key in .env
- Verify you have credits: https://platform.openai.com/usage
- Try a different model if rate limited

### Import errors
```powershell
# Make sure you're in venv
.\venv\Scripts\Activate

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Railway deployment fails
- Check logs in Railway dashboard
- Verify all environment variables are set
- Ensure requirements.txt is up to date
- Check that port is set correctly

## 🎉 Success Criteria

Your MVP is ready when you can:

1. ✅ Chat with the AI about MIT courses
2. ✅ Ask "What courses should I take for 6-3?"
3. ✅ Search for courses by name or department
4. ✅ Get answers about requirements
5. ✅ See the chat working on the deployed URL

## 📝 After MVP

Once deployed, you can add:
- Schedule generation (already have solver!)
- Schedule visualization
- Course reviews from scraping
- User authentication
- Database instead of in-memory storage
- More sophisticated RAG queries

## 🚀 Ready to Deploy!

You have everything you need. Just:
1. Add the 7 new files
2. Run init_data.py
3. Test locally
4. Build frontend in Lovable
5. Deploy to Railway
6. Celebrate! 🎉

Estimated time: **5-6 hours** total.

**Start with Step 1 and work through the checklist!**
