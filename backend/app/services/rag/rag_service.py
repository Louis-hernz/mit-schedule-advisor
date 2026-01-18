"""
MIT Schedule Advisor - RAG Service
Handles vector embeddings, document storage, and retrieval
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from loguru import logger

from app.core.config import get_settings
from app.models.schemas import Course, Requirement, StudentProfile

settings = get_settings()


class RAGService:
    """
    Retrieval-Augmented Generation service
    Manages embeddings and document retrieval using ChromaDB
    """

    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Initialize ChromaDB
        use_ssl = settings.CHROMA_PORT == 443

        self.chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            ssl=use_ssl,
            settings=ChromaSettings(allow_reset=True)
        )
        # Get or create collections
        self.courses_collection = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_COURSES,
            metadata={"description": "MIT course descriptions and information"}
        )

        self.requirements_collection = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_REQUIREMENTS,
            metadata={"description": "Degree requirements and rules"}
        )

        self.knowledge_collection = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_KNOWLEDGE,
            metadata={"description": "MIT-specific knowledge base"}
        )

        logger.info("RAG Service initialized")

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    async def add_course(self, course: Course) -> None:
        """
        Add a course to the vector database

        Args:
            course: Course object to add
        """
        try:
            # Create document text from course information
            doc_text = self._course_to_document(course)

            # Generate embedding
            embedding = await self.embed_text(doc_text)

            # Add to collection
            self.courses_collection.add(
                ids=[course.id],
                documents=[doc_text],
                embeddings=[embedding],
                metadatas=[{
                    "course_id": course.id,
                    "title": course.title,
                    "department": course.department,
                    "level": course.level.value,
                    "units": course.units,
                    "terms_offered": ",".join([t.value for t in course.terms_offered]),
                    "has_prerequisites": len(course.prerequisites) > 0
                }]
            )

            logger.debug(f"Added course {course.id} to vector database")

        except Exception as e:
            logger.error(f"Error adding course {course.id}: {e}")
            raise

    async def add_courses_batch(self, courses: List[Course]) -> None:
        """
        Add multiple courses to the vector database efficiently

        Args:
            courses: List of Course objects
        """
        try:
            logger.info(f"Adding {len(courses)} courses to vector database")

            # Prepare data
            ids = [c.id for c in courses]
            documents = [self._course_to_document(c) for c in courses]
            metadatas = [self._course_to_metadata(c) for c in courses]

            # Generate embeddings in batch
            embeddings = await self.embed_batch(documents)

            # Add to collection
            self.courses_collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )

            logger.info(f"Successfully added {len(courses)} courses")

        except Exception as e:
            logger.error(f"Error adding courses batch: {e}")
            raise

    async def add_requirement(self, requirement: Requirement) -> None:
        """
        Add a requirement to the vector database

        Args:
            requirement: Requirement object to add
        """
        try:
            doc_text = self._requirement_to_document(requirement)
            embedding = await self.embed_text(doc_text)

            self.requirements_collection.add(
                ids=[requirement.id],
                documents=[doc_text],
                embeddings=[embedding],
                metadatas=[{
                    "requirement_id": requirement.id,
                    "major": requirement.major,
                    "rule_type": requirement.rule_type.value,
                    "category": requirement.category or ""
                }]
            )

            logger.debug(f"Added requirement {requirement.id} to vector database")

        except Exception as e:
            logger.error(f"Error adding requirement {requirement.id}: {e}")
            raise

    async def add_knowledge(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Add a knowledge base document

        Args:
            doc_id: Unique document ID
            text: Document text
            metadata: Document metadata
        """
        try:
            embedding = await self.embed_text(text)

            self.knowledge_collection.add(
                ids=[doc_id],
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata]
            )

            logger.debug(f"Added knowledge document {doc_id}")

        except Exception as e:
            logger.error(f"Error adding knowledge document: {e}")
            raise

    async def query_courses(
        self,
        query: str,
        student_profile: Optional[StudentProfile] = None,
        k: int = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query courses using semantic search

        Args:
            query: Search query
            student_profile: Optional student profile for context
            k: Number of results (default from settings)
            filters: Metadata filters

        Returns:
            List of retrieved documents with metadata
        """
        try:
            k = k or settings.RAG_TOP_K

            # Generate query embedding
            query_embedding = await self.embed_text(query)

            # Build where clause from filters and student profile
            where = self._build_where_clause(filters, student_profile)

            # Query collection
            results = self.courses_collection.query(
                query_embeddings=[query_embedding],
                n_results=k * 2 if settings.RAG_RERANK else k,  # Over-fetch for reranking
                where=where if where else None
            )

            # Format results
            documents = self._format_query_results(results)

            # Rerank if enabled
            if settings.RAG_RERANK and len(documents) > k:
                documents = await self._rerank_results(query, documents, student_profile)
                documents = documents[:k]

            logger.info(f"Retrieved {len(documents)} course documents for query: {query[:50]}...")
            return documents

        except Exception as e:
            logger.error(f"Error querying courses: {e}")
            raise

    async def query_requirements(
        self,
        query: str,
        major: Optional[str] = None,
        k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Query requirements using semantic search

        Args:
            query: Search query
            major: Filter by major
            k: Number of results

        Returns:
            List of retrieved requirement documents
        """
        try:
            k = k or settings.RAG_TOP_K

            query_embedding = await self.embed_text(query)

            where = {"major": major} if major else None

            results = self.requirements_collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where
            )

            documents = self._format_query_results(results)

            logger.info(f"Retrieved {len(documents)} requirement documents")
            return documents

        except Exception as e:
            logger.error(f"Error querying requirements: {e}")
            raise

    async def query_knowledge(
        self,
        query: str,
        k: int = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query MIT knowledge base

        Args:
            query: Search query
            k: Number of results
            category: Filter by category

        Returns:
            List of retrieved knowledge documents
        """
        try:
            k = k or settings.RAG_TOP_K

            query_embedding = await self.embed_text(query)

            where = {"category": category} if category else None

            results = self.knowledge_collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where
            )

            documents = self._format_query_results(results)

            logger.info(f"Retrieved {len(documents)} knowledge documents")
            return documents

        except Exception as e:
            logger.error(f"Error querying knowledge: {e}")
            raise

    async def query_all(
        self,
        query: str,
        student_profile: Optional[StudentProfile] = None,
        k_per_collection: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query all collections and return combined results

        Args:
            query: Search query
            student_profile: Optional student profile
            k_per_collection: Results per collection

        Returns:
            Dictionary with results from each collection
        """
        try:
            courses = await self.query_courses(query, student_profile, k_per_collection)
            requirements = await self.query_requirements(
                query,
                major=student_profile.major if student_profile else None,
                k=k_per_collection
            )
            knowledge = await self.query_knowledge(query, k_per_collection)

            return {
                "courses": courses,
                "requirements": requirements,
                "knowledge": knowledge
            }

        except Exception as e:
            logger.error(f"Error querying all collections: {e}")
            raise

    def _course_to_document(self, course: Course) -> str:
        """Convert course to searchable document text"""
        parts = [
            f"Course {course.id}: {course.title}",
            f"Description: {course.description}",
            f"Units: {course.units}",
            f"Level: {course.level.value}"
        ]

        if course.prerequisites:
            parts.append(f"Prerequisites: {', '.join(course.prerequisites)}")

        if course.terms_offered:
            terms = ', '.join([t.value for t in course.terms_offered])
            parts.append(f"Offered: {terms}")

        if course.meets_requirements:
            parts.append(f"Satisfies: {', '.join(course.meets_requirements)}")

        return "\n".join(parts)

    def _course_to_metadata(self, course: Course) -> Dict[str, Any]:
        """Convert course to metadata dictionary"""
        return {
            "course_id": course.id,
            "title": course.title,
            "department": course.department,
            "level": course.level.value,
            "units": course.units,
            "terms_offered": ",".join([t.value for t in course.terms_offered]),
            "has_prerequisites": len(course.prerequisites) > 0,
            "difficulty_rating": course.difficulty_rating or 0.0,
            "student_rating": course.student_rating or 0.0
        }

    def _requirement_to_document(self, requirement: Requirement) -> str:
        """Convert requirement to searchable document text"""
        parts = [
            f"Requirement for {requirement.major}: {requirement.description}",
            f"Type: {requirement.rule_type.value}"
        ]

        if requirement.courses_allowed:
            parts.append(f"Allowed courses: {', '.join(requirement.courses_allowed)}")

        if requirement.category:
            parts.append(f"Category: {requirement.category}")

        if requirement.units_required:
            parts.append(f"Units required: {requirement.units_required}")

        return "\n".join(parts)

    def _build_where_clause(
        self,
        filters: Optional[Dict[str, Any]],
        student_profile: Optional[StudentProfile]
    ) -> Optional[Dict[str, Any]]:
        """Build ChromaDB where clause from filters and student profile"""
        where = filters.copy() if filters else {}

        if student_profile:
            # Add implicit filters based on student profile
            if "level" not in where:
                # Undergrad students typically take undergrad courses
                if student_profile.year <= 4:
                    where["level"] = "U"

        return where if where else None

    def _format_query_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format ChromaDB query results into consistent structure"""
        documents = []

        if not results or not results.get("ids"):
            return documents

        ids = results["ids"][0] if results["ids"] else []
        docs = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results.get("distances") else [0] * len(ids)

        for i, doc_id in enumerate(ids):
            # Filter by similarity threshold
            similarity = 1 - distances[i]  # Convert distance to similarity
            if similarity < settings.RAG_SIMILARITY_THRESHOLD:
                continue

            documents.append({
                "id": doc_id,
                "document": docs[i] if i < len(docs) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "similarity": similarity
            })

        return documents

    async def _rerank_results(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        student_profile: Optional[StudentProfile]
    ) -> List[Dict[str, Any]]:
        """
        Rerank results based on additional context
        This is a placeholder for more sophisticated reranking
        """
        # Simple reranking: boost courses in student's department
        if student_profile and "department" in student_profile.major:
            dept = student_profile.major.split("-")[0]

            for doc in documents:
                metadata = doc.get("metadata", {})
                if metadata.get("department") == dept:
                    doc["similarity"] *= 1.2  # Boost department courses

        # Sort by adjusted similarity
        documents.sort(key=lambda x: x["similarity"], reverse=True)

        return documents

    def get_collection_count(self, collection_name: str) -> int:
        """Get count of documents in a collection"""
        collection = self.chroma_client.get_collection(collection_name)
        return collection.count()

    def reset_collections(self):
        """Reset all collections (use with caution!)"""
        logger.warning("Resetting all RAG collections")
        self.chroma_client.reset()
        self.__init__()  # Reinitialize collections
