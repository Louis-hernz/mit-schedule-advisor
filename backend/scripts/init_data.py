"""
Initialize RAG database with MIT course data
Run with: python -m scripts.init_data
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.mit_api import MITCoursesClient
from app.services.rag.rag_service import RAGService
from app.models.schemas import Course, Requirement, RequirementType, Term, CourseLevel
from loguru import logger


async def init_courses():
    """Fetch and index MIT courses"""
    logger.info("=" * 60)
    logger.info("INITIALIZING COURSE DATA")
    logger.info("=" * 60)
    
    courses_client = MITCoursesClient()
    rag_service = RAGService()
    
    try:
        # Fetch courses from MIT API
        logger.info("Fetching courses from MIT API...")
        try:
            courses = await courses_client.get_all_courses()
            logger.info(f"✓ Found {len(courses)} courses from API")
        except Exception as e:
            logger.warning(f"Could not fetch from API: {e}")
            logger.info("Using mock data instead...")
            courses = get_mock_courses()
            logger.info(f"✓ Created {len(courses)} mock courses")
        
        # Index in RAG
        logger.info("Indexing courses in vector database...")
        await rag_service.add_courses_batch(courses)
        logger.info(f"✓ Indexed {len(courses)} courses")
        
        # Verify
        count = rag_service.get_collection_count(rag_service.courses_collection.name)
        logger.info(f"✓ Total courses in database: {count}")
        
    finally:
        await courses_client.close()


async def init_requirements():
    """Add degree requirements"""
    logger.info("\n" + "=" * 60)
    logger.info("INITIALIZING REQUIREMENTS DATA")
    logger.info("=" * 60)
    
    rag_service = RAGService()
    
    requirements = get_mock_requirements()
    
    logger.info(f"Adding {len(requirements)} requirements...")
    for req in requirements:
        await rag_service.add_requirement(req)
    
    logger.info(f"✓ Added {len(requirements)} requirements")
    
    count = rag_service.get_collection_count(rag_service.requirements_collection.name)
    logger.info(f"✓ Total requirements in database: {count}")


async def init_mit_knowledge():
    """Add MIT-specific knowledge base"""
    logger.info("\n" + "=" * 60)
    logger.info("INITIALIZING MIT KNOWLEDGE BASE")
    logger.info("=" * 60)
    
    rag_service = RAGService()
    
    knowledge_docs = [
        {
            "id": "units_system",
            "text": """MIT uses a units system to measure course workload. A typical course is 12 units, 
            represented as X-Y-Z where X is classroom hours, Y is lab hours, and Z is outside work hours per week. 
            For example, 3-0-9 means 3 hours of lecture, 0 hours of lab, and 9 hours of outside work. 
            A full-time student typically takes 48-60 units per term.""",
            "metadata": {"type": "policy", "category": "general"}
        },
        {
            "id": "rest_requirement",
            "text": """REST (Restricted Elective in Science and Technology): All MIT students must complete 
            two subjects from the REST requirement list. These courses provide depth in scientific and 
            technical fields outside the student's major. REST courses are marked in the course catalog.""",
            "metadata": {"type": "requirement", "category": "general"}
        },
        {
            "id": "ci_requirement",
            "text": """Communication Intensive (CI) Requirement: Students must complete four CI subjects, 
            including at least two CI-H (Humanities, Arts, and Social Sciences) subjects. CI subjects 
            involve substantial writing, speaking, or presentation components.""",
            "metadata": {"type": "requirement", "category": "general"}
        },
        {
            "id": "hass_requirement",
            "text": """HASS (Humanities, Arts, and Social Sciences) Requirement: Students must complete 
            8 HASS subjects, including a HASS Concentration of at least 3 subjects in related fields.""",
            "metadata": {"type": "requirement", "category": "general"}
        },
        {
            "id": "course_6_3",
            "text": """Course 6-3 (Computer Science and Engineering) is one of MIT's most popular majors. 
            It requires strong foundations in algorithms, systems, and theory. Key courses include 
            6.006 (Algorithms), 6.046 (Advanced Algorithms), 6.004 (Computation Structures), and 
            6.031 (Software Construction). Students also complete an advanced undergraduate subject (AUS).""",
            "metadata": {"type": "major_info", "category": "6-3"}
        },
        {
            "id": "prerequisites",
            "text": """Prerequisites are courses that must be completed before taking a particular course. 
            At MIT, prerequisites are strictly enforced. Some courses also have corequisites, which must 
            be taken simultaneously or before.""",
            "metadata": {"type": "policy", "category": "general"}
        },
        {
            "id": "registration",
            "text": """MIT students register for classes during pre-registration (in the preceding term) 
            and can adjust during the first two weeks of the semester (Add/Drop period). Drop Date is 
            the last day to drop a class without record. After Drop Date but before the last day of classes, 
            you can drop with a 'W' notation.""",
            "metadata": {"type": "policy", "category": "registration"}
        },
        {
            "id": "grading_sophomore_year",
            "text": """First-year students take classes on Pass/No Record for their first semester. 
            Second semester first-year is ABC/No Record. Sophomore fall is also ABC/No Record, 
            allowing students to explore without grade pressure.""",
            "metadata": {"type": "policy", "category": "grading"}
        }
    ]
    
    logger.info(f"Adding {len(knowledge_docs)} knowledge documents...")
    for doc in knowledge_docs:
        await rag_service.add_knowledge(
            doc_id=doc["id"],
            text=doc["text"],
            metadata=doc["metadata"]
        )
        logger.info(f"  ✓ Added: {doc['id']}")
    
    count = rag_service.get_collection_count(rag_service.knowledge_collection.name)
    logger.info(f"✓ Total knowledge documents: {count}")


def get_mock_courses():
    """Generate mock course data for testing"""
    return [
        Course(
            id="6.006",
            title="Introduction to Algorithms",
            description="Introduction to mathematical modeling of computational problems. Analysis of algorithms. Techniques for designing efficient algorithms. Core data structures and algorithms including sorting, searching, graph algorithms, and dynamic programming.",
            units=12,
            level=CourseLevel.UNDERGRAD,
            prerequisites=["6.100A"],
            corequisites=[],
            terms_offered=[Term.FALL, Term.SPRING],
            meets_requirements=["REST"],
            department="6",
            difficulty_rating=4.5,
            student_rating=4.2
        ),
        Course(
            id="6.046",
            title="Design and Analysis of Algorithms",
            description="Advanced algorithmic techniques including divide-and-conquer, dynamic programming, greedy algorithms, network flow, computational geometry, number-theoretic algorithms, amortization, and approximation algorithms.",
            units=12,
            level=CourseLevel.UNDERGRAD,
            prerequisites=["6.006"],
            terms_offered=[Term.SPRING],
            meets_requirements=["REST", "AUS"],
            department="6",
            difficulty_rating=4.8,
            student_rating=4.5
        ),
        Course(
            id="6.100A",
            title="Introduction to Computer Science Programming in Python",
            description="Introduction to computer science and programming using Python. Topics include computational thinking, algorithms, data structures, and software engineering principles.",
            units=6,
            level=CourseLevel.UNDERGRAD,
            prerequisites=[],
            terms_offered=[Term.FALL, Term.SPRING],
            meets_requirements=[],
            department="6",
            difficulty_rating=3.2,
            student_rating=4.0
        ),
        Course(
            id="18.06",
            title="Linear Algebra",
            description="Matrix theory and linear algebra. Emphasis on topics useful in other disciplines. Linear equations, determinants, eigenvalues, positive definite matrices, linear transformations, vector spaces.",
            units=12,
            level=CourseLevel.UNDERGRAD,
            prerequisites=["18.01"],
            terms_offered=[Term.FALL, Term.SPRING],
            meets_requirements=["REST"],
            department="18",
            difficulty_rating=4.0,
            student_rating=4.3
        ),
        Course(
            id="18.01",
            title="Single Variable Calculus",
            description="Differentiation and integration of functions of one variable. Applications. Techniques of integration, approximation by polynomials, sequences and series.",
            units=12,
            level=CourseLevel.UNDERGRAD,
            prerequisites=[],
            terms_offered=[Term.FALL, Term.SPRING],
            meets_requirements=[],
            department="18",
            difficulty_rating=3.8,
            student_rating=4.1
        ),
        Course(
            id="8.01",
            title="Physics I",
            description="Introduction to Newtonian mechanics. Forces, energy, momentum, angular momentum, and periodic motion. Laboratory and tutorial sessions emphasize problem-solving and critical thinking.",
            units=12,
            level=CourseLevel.UNDERGRAD,
            prerequisites=[],
            terms_offered=[Term.FALL],
            meets_requirements=["GIR"],
            department="8",
            difficulty_rating=4.2,
            student_rating=3.8
        ),
    ]


def get_mock_requirements():
    """Generate mock requirements for testing"""
    return [
        Requirement(
            id="6-3-algorithms-foundation",
            major="6-3",
            description="Foundation in Algorithms: Must complete 6.006 (Introduction to Algorithms)",
            rule_type=RequirementType.SPECIFIC_COURSE,
            courses_allowed=["6.006"],
            metadata={"category": "foundation", "required": True}
        ),
        Requirement(
            id="6-3-advanced-algorithms",
            major="6-3",
            description="Advanced Algorithms: Must complete one of 6.046, 6.854, or 6.856",
            rule_type=RequirementType.SPECIFIC_COURSE,
            courses_allowed=["6.046", "6.854", "6.856"],
            metadata={"category": "advanced", "required": True}
        ),
        Requirement(
            id="general-rest",
            major="ALL",
            description="REST Requirement: Complete 2 REST subjects",
            rule_type=RequirementType.UNITS,
            category="REST",
            units_required=24,
            courses_required=2,
            metadata={"type": "general_requirement"}
        ),
        Requirement(
            id="general-ci-h",
            major="ALL",
            description="CI-H Requirement: Complete at least 2 CI-H subjects",
            rule_type=RequirementType.UNITS,
            category="CI-H",
            courses_required=2,
            metadata={"type": "general_requirement"}
        ),
    ]


async def main():
    """Main initialization function"""
    logger.info("\n" + "=" * 60)
    logger.info("MIT SCHEDULE ADVISOR - DATA INITIALIZATION")
    logger.info("=" * 60 + "\n")
    
    try:
        # Initialize all data
        await init_courses()
        await init_requirements()
        await init_mit_knowledge()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ INITIALIZATION COMPLETE!")
        logger.info("=" * 60)
        logger.info("\nYou can now start the API server:")
        logger.info("  cd backend")
        logger.info("  python -m uvicorn app.main:app --reload")
        logger.info("\nAPI will be available at: http://localhost:8000")
        logger.info("API docs at: http://localhost:8000/docs\n")
        
    except Exception as e:
        logger.error(f"\n❌ INITIALIZATION FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
