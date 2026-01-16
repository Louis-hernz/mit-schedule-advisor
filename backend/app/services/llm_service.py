"""
MIT Schedule Advisor - LLM Service
Orchestrates LLM interactions with RAG and function calling
"""
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from loguru import logger

from app.core.config import get_settings
from app.models.schemas import (
    ChatMessage, ChatRequest, ChatResponse,
    StudentProfile, Schedule, Course
)
from app.services.rag.rag_service import RAGService
from app.services.solver.schedule_solver import ScheduleSolver

settings = get_settings()


class LLMService:
    """
    Orchestrates LLM interactions for the schedule advisor
    Combines RAG retrieval with function calling
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.rag_service = RAGService()
        self.solver = ScheduleSolver()
    
    async def chat(
        self,
        message: str,
        student_profile: StudentProfile,
        conversation_history: List[ChatMessage],
        current_schedule: Optional[Schedule] = None
    ) -> ChatResponse:
        """
        Process a chat message with RAG context and function calling
        
        Args:
            message: User's message
            student_profile: Student information
            conversation_history: Previous messages
            current_schedule: Student's current schedule if any
        
        Returns:
            ChatResponse with LLM reply and any actions taken
        """
        try:
            logger.info(f"Processing chat message for student {student_profile.id}")
            
            # 1. Query RAG for relevant context
            rag_results = await self.rag_service.query_all(
                query=message,
                student_profile=student_profile,
                k_per_collection=3
            )
            
            # 2. Build conversation messages
            messages = self._build_messages(
                message,
                student_profile,
                rag_results,
                conversation_history,
                current_schedule
            )
            
            # 3. Call OpenAI with function definitions
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                functions=self._get_function_definitions(),
                function_call="auto",
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS
            )
            
            # 4. Handle function calls if any
            function_calls = []
            updated_schedule = None
            
            message_obj = response.choices[0].message
            
            if message_obj.function_call:
                logger.info(f"Function called: {message_obj.function_call.name}")
                
                # Execute the function
                function_result = await self._handle_function_call(
                    message_obj.function_call,
                    student_profile,
                    current_schedule
                )
                
                function_calls.append({
                    "name": message_obj.function_call.name,
                    "arguments": message_obj.function_call.arguments,
                    "result": function_result
                })
                
                # If schedule was generated, include it
                if message_obj.function_call.name == "generate_schedule":
                    updated_schedule = function_result.get("schedule")
                
                # Make follow-up call with function result
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "function_call": {
                        "name": message_obj.function_call.name,
                        "arguments": message_obj.function_call.arguments
                    }
                })
                messages.append({
                    "role": "function",
                    "name": message_obj.function_call.name,
                    "content": str(function_result)
                })
                
                # Get final response
                final_response = await self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    temperature=settings.OPENAI_TEMPERATURE
                )
                
                response_text = final_response.choices[0].message.content
            else:
                response_text = message_obj.content
            
            # 5. Format retrieved documents for response
            retrieved_docs = self._format_rag_results(rag_results)
            
            return ChatResponse(
                message=response_text,
                function_calls=function_calls,
                retrieved_documents=retrieved_docs,
                updated_schedule=updated_schedule
            )
        
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return ChatResponse(
                message=f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                function_calls=[],
                retrieved_documents=[]
            )
    
    def _build_messages(
        self,
        user_message: str,
        student_profile: StudentProfile,
        rag_results: Dict[str, List[Dict]],
        history: List[ChatMessage],
        current_schedule: Optional[Schedule]
    ) -> List[Dict[str, str]]:
        """Build conversation messages with context"""
        
        # System prompt
        system_prompt = self._build_system_prompt(
            student_profile,
            rag_results,
            current_schedule
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 10 messages)
        for msg in history[-10:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    def _build_system_prompt(
        self,
        student_profile: StudentProfile,
        rag_results: Dict[str, List[Dict]],
        current_schedule: Optional[Schedule]
    ) -> str:
        """Build system prompt with context"""
        
        # Format RAG context
        courses_context = "\n".join([
            f"- {doc['document'][:200]}..." 
            for doc in rag_results.get('courses', [])[:3]
        ])
        
        requirements_context = "\n".join([
            f"- {doc['document'][:200]}..."
            for doc in rag_results.get('requirements', [])[:3]
        ])
        
        knowledge_context = "\n".join([
            f"- {doc['document'][:200]}..."
            for doc in rag_results.get('knowledge', [])[:2]
        ])
        
        # Format student info
        schedule_info = ""
        if current_schedule:
            schedule_info = f"\nCurrent schedule: {len(current_schedule.terms)} terms planned, {current_schedule.total_units} total units"
        
        completed_courses = ", ".join(student_profile.completed_courses) if student_profile.completed_courses else "None yet"
        
        prompt = f"""You are an expert MIT academic advisor helping students plan their 4-year schedules.

STUDENT INFORMATION:
- Major: {student_profile.major}
- Year: {student_profile.year}
- Current semester: {student_profile.semester}
- Completed courses: {completed_courses}
- In progress: {", ".join(student_profile.in_progress_courses) if student_profile.in_progress_courses else "None"}{schedule_info}

RELEVANT COURSE INFORMATION:
{courses_context}

RELEVANT REQUIREMENTS:
{requirements_context}

MIT KNOWLEDGE:
{knowledge_context}

YOUR CAPABILITIES:
1. Answer questions about courses, requirements, and MIT policies
2. Explain whether specific courses satisfy requirements
3. Generate complete 4-year schedules using the solver
4. Validate schedules against constraints
5. Provide personalized academic advice

GUIDELINES:
- Be helpful, friendly, and supportive
- Cite specific course numbers when relevant
- If you're unsure, use the search_courses function to find more info
- When asked to create a schedule, use the generate_schedule function
- Explain your reasoning clearly
- Consider the student's preferences and constraints
- Always verify prerequisites and requirements

When discussing schedules:
- Mention course numbers, titles, and units
- Warn about difficult courses or heavy workloads
- Suggest balancing technical and non-technical courses
- Consider the student's year and progress
"""
        
        return prompt
    
    def _get_function_definitions(self) -> List[Dict[str, Any]]:
        """Define functions the LLM can call"""
        return [
            {
                "name": "generate_schedule",
                "description": "Generate a complete 4-year schedule for the student that satisfies all requirements and preferences",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "optimization_goals": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Priority goals like 'minimize_mornings', 'balance_workload', 'front_load_major', 'maximize_ratings'"
                        },
                        "max_units_per_term": {
                            "type": "integer",
                            "description": "Maximum units per term (typically 48-60)"
                        },
                        "avoid_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Terms to leave lighter (e.g., for UROP or other commitments)"
                        }
                    }
                }
            },
            {
                "name": "search_courses",
                "description": "Search for courses by query, department, or other filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (course name, topic, etc.)"
                        },
                        "department": {
                            "type": "string",
                            "description": "Department number (e.g., '6', '18')"
                        },
                        "level": {
                            "type": "string",
                            "enum": ["U", "G"],
                            "description": "Course level (U for undergrad, G for grad)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "validate_requirement",
                "description": "Check if a specific course satisfies a requirement",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "course_id": {
                            "type": "string",
                            "description": "Course number (e.g., '6.006')"
                        },
                        "requirement_type": {
                            "type": "string",
                            "description": "Type of requirement (e.g., 'REST', 'CI-H', 'major foundation')"
                        }
                    },
                    "required": ["course_id", "requirement_type"]
                }
            },
            {
                "name": "check_prerequisites",
                "description": "Check if student has completed prerequisites for a course",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "course_id": {
                            "type": "string",
                            "description": "Course number to check"
                        }
                    },
                    "required": ["course_id"]
                }
            }
        ]
    
    async def _handle_function_call(
        self,
        function_call,
        student_profile: StudentProfile,
        current_schedule: Optional[Schedule]
    ) -> Dict[str, Any]:
        """Execute a function call"""
        import json
        
        function_name = function_call.name
        arguments = json.loads(function_call.arguments)
        
        try:
            if function_name == "generate_schedule":
                return await self._generate_schedule(student_profile, arguments)
            
            elif function_name == "search_courses":
                return await self._search_courses(arguments)
            
            elif function_name == "validate_requirement":
                return await self._validate_requirement(arguments, student_profile)
            
            elif function_name == "check_prerequisites":
                return await self._check_prerequisites(arguments, student_profile)
            
            else:
                return {"error": f"Unknown function: {function_name}"}
        
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return {"error": str(e)}
    
    async def _generate_schedule(
        self,
        student_profile: StudentProfile,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate schedule using solver"""
        
        # This is simplified - you'll need to:
        # 1. Fetch requirements for student's major
        # 2. Fetch available courses
        # 3. Fetch course offerings by term
        # 4. Call solver
        
        logger.info("Generating schedule...")
        
        # TODO: Implement full schedule generation
        # For now, return a placeholder
        
        return {
            "status": "success",
            "message": "Schedule generation is being implemented. For now, I can help you plan courses term by term.",
            "schedule": None
        }
    
    async def _search_courses(
        self,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Search courses using RAG"""
        
        query = arguments.get("query", "")
        
        # Use RAG to search
        results = await self.rag_service.query_courses(
            query=query,
            k=5
        )
        
        courses = []
        for doc in results:
            courses.append({
                "document": doc["document"][:300],
                "metadata": doc["metadata"]
            })
        
        return {
            "status": "success",
            "courses": courses,
            "count": len(courses)
        }
    
    async def _validate_requirement(
        self,
        arguments: Dict[str, Any],
        student_profile: StudentProfile
    ) -> Dict[str, Any]:
        """Validate if course satisfies requirement"""
        
        course_id = arguments.get("course_id")
        requirement_type = arguments.get("requirement_type")
        
        # Search for the course and requirement info
        course_results = await self.rag_service.query_courses(
            query=f"course {course_id}",
            k=1
        )
        
        req_results = await self.rag_service.query_requirements(
            query=requirement_type,
            major=student_profile.major,
            k=2
        )
        
        # Simple validation based on metadata
        satisfied = False
        explanation = ""
        
        if course_results:
            course_meta = course_results[0].get("metadata", {})
            meets_reqs = course_meta.get("meets_requirements", "").split(",")
            
            if requirement_type in meets_reqs:
                satisfied = True
                explanation = f"Yes, {course_id} satisfies the {requirement_type} requirement."
            else:
                explanation = f"No, {course_id} does not satisfy the {requirement_type} requirement."
        else:
            explanation = f"Could not find information about {course_id}."
        
        return {
            "status": "success",
            "course_id": course_id,
            "requirement_type": requirement_type,
            "satisfied": satisfied,
            "explanation": explanation
        }
    
    async def _check_prerequisites(
        self,
        arguments: Dict[str, Any],
        student_profile: StudentProfile
    ) -> Dict[str, Any]:
        """Check if prerequisites are satisfied"""
        
        course_id = arguments.get("course_id")
        
        # Search for course info
        results = await self.rag_service.query_courses(
            query=f"course {course_id} prerequisites",
            k=1
        )
        
        if not results:
            return {
                "status": "error",
                "message": f"Could not find information about {course_id}"
            }
        
        # Extract prerequisites from metadata
        course_meta = results[0].get("metadata", {})
        # This is simplified - actual implementation would parse prerequisites properly
        
        completed = student_profile.completed_courses
        
        return {
            "status": "success",
            "course_id": course_id,
            "completed_courses": completed,
            "message": f"Based on your completed courses, I'll check the prerequisites for {course_id}."
        }
    
    def _format_rag_results(
        self,
        rag_results: Dict[str, List[Dict]]
    ) -> List[Dict[str, Any]]:
        """Format RAG results for response"""
        
        formatted = []
        
        for collection, docs in rag_results.items():
            for doc in docs:
                formatted.append({
                    "collection": collection,
                    "content": doc.get("document", "")[:200],
                    "metadata": doc.get("metadata", {}),
                    "similarity": doc.get("similarity", 0)
                })
        
        return formatted
