"""
MIT Schedule Advisor - Schedule Solver
Constraint-based schedule generation using OR-Tools
"""
from typing import List, Dict, Any, Optional, Tuple
from ortools.sat.python import cp_model
from loguru import logger
import time

from app.models.schemas import (
    Course, Requirement, StudentProfile, Schedule, ScheduledTerm,
    ScheduledCourse, Term, ScheduleValidation, RequirementType
)
from app.core.config import get_settings

settings = get_settings()


class ScheduleSolver:
    """
    Constraint satisfaction solver for schedule generation
    
    Uses Google OR-Tools CP-SAT solver to generate valid 4-year schedules
    that satisfy all requirements while optimizing for student preferences.
    """
    
    def __init__(self):
        self.model = None
        self.solver = None
        self.settings = get_settings()
    
    async def solve(
        self,
        student_profile: StudentProfile,
        requirements: List[Requirement],
        available_courses: Dict[str, Course],  # course_id -> Course
        course_offerings: Dict[str, List[str]],  # term_id -> [course_ids]
        preferences: Optional[Dict[str, float]] = None
    ) -> Tuple[Optional[Schedule], float]:
        """
        Generate a complete 4-year schedule
        
        Args:
            student_profile: Student information and history
            requirements: List of degree requirements to satisfy
            available_courses: All available courses
            course_offerings: Which courses are offered in which terms
            preferences: Optimization weights (0-1)
        
        Returns:
            Tuple of (Schedule object, optimization_score) or (None, 0) if no solution
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting schedule generation for student {student_profile.id}")
            
            # Initialize model
            self.model = cp_model.CpModel()
            
            # Get student preferences with defaults
            preferences = preferences or student_profile.optimization_weights
            
            # Calculate terms to plan
            terms = self._generate_terms(student_profile)
            
            # Create decision variables
            # course_vars[course_id][term_id] = 1 if course taken in term, 0 otherwise
            course_vars = {}
            for course_id in available_courses:
                course_vars[course_id] = {}
                for term_id in terms:
                    var_name = f"{course_id}_{term_id}"
                    course_vars[course_id][term_id] = self.model.NewBoolVar(var_name)
            
            # Add constraints
            self._add_requirement_constraints(
                course_vars, requirements, available_courses, terms
            )
            self._add_prerequisite_constraints(
                course_vars, available_courses, terms, student_profile.completed_courses
            )
            self._add_offering_constraints(
                course_vars, course_offerings, terms
            )
            self._add_unit_constraints(
                course_vars, available_courses, terms, student_profile
            )
            # Note: Time conflict constraints would require meeting time data
            
            # Add objective (maximize preferences)
            self._add_objective(
                course_vars, available_courses, terms, preferences
            )
            
            # Solve
            self.solver = cp_model.CpSolver()
            self.solver.parameters.max_time_in_seconds = settings.SOLVER_TIMEOUT_SECONDS
            
            logger.info("Solving constraint satisfaction problem...")
            status = self.solver.Solve(self.model)
            
            solve_time = time.time() - start_time
            
            if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
                logger.info(f"Solution found in {solve_time:.2f}s")
                
                # Extract schedule from solution
                schedule = self._extract_schedule(
                    course_vars, available_courses, terms, student_profile
                )
                
                # Calculate optimization score
                score = self._calculate_score(schedule, preferences)
                
                return schedule, score
            
            else:
                logger.warning(f"No solution found (status: {status})")
                return None, 0.0
        
        except Exception as e:
            logger.error(f"Error in solver: {e}")
            raise
    
    def validate_schedule(
        self,
        schedule: Schedule,
        requirements: List[Requirement],
        available_courses: Dict[str, Course]
    ) -> ScheduleValidation:
        """
        Validate a schedule against all requirements
        
        Args:
            schedule: Schedule to validate
            requirements: List of requirements
            available_courses: Available courses
        
        Returns:
            ScheduleValidation with detailed results
        """
        errors = []
        warnings = []
        requirements_satisfied = {}
        missing_requirements = []
        conflicts = []
        
        try:
            # Get all courses in schedule
            scheduled_courses = schedule.all_courses
            
            # Check each requirement
            for req in requirements:
                satisfied = self._check_requirement(
                    req, scheduled_courses, available_courses
                )
                requirements_satisfied[req.id] = satisfied
                
                if not satisfied:
                    missing_requirements.append(req.id)
                    errors.append(f"Requirement not satisfied: {req.description}")
            
            # Check prerequisites
            for term in schedule.terms:
                for scheduled_course in term.courses:
                    course = scheduled_course.course
                    
                    # Get courses taken before this term
                    prior_courses = self._get_prior_courses(schedule, term.year, term.semester)
                    
                    # Check prerequisites
                    for prereq in course.prerequisites:
                        if prereq not in prior_courses:
                            errors.append(
                                f"Prerequisite {prereq} not satisfied for {course.id} in {term.term_id}"
                            )
            
            # Check time conflicts within each term
            for term in schedule.terms:
                term_conflicts = term.has_conflicts()
                if term_conflicts:
                    conflicts.extend([
                        {
                            "term": term.term_id,
                            "courses": list(conflict)
                        }
                        for conflict in term_conflicts
                    ])
                    errors.append(f"Time conflicts in {term.term_id}")
            
            # Check unit limits
            for term in schedule.terms:
                if term.total_units > settings.DEFAULT_MAX_UNITS_PER_TERM:
                    warnings.append(
                        f"Term {term.term_id} exceeds recommended unit limit "
                        f"({term.total_units} > {settings.DEFAULT_MAX_UNITS_PER_TERM})"
                    )
                elif term.total_units < settings.DEFAULT_MIN_UNITS_PER_TERM:
                    warnings.append(
                        f"Term {term.term_id} below typical unit load "
                        f"({term.total_units} < {settings.DEFAULT_MIN_UNITS_PER_TERM})"
                    )
            
            is_valid = len(errors) == 0
            
            return ScheduleValidation(
                is_valid=is_valid,
                requirements_satisfied=requirements_satisfied,
                missing_requirements=missing_requirements,
                warnings=warnings,
                errors=errors,
                conflicts=conflicts
            )
        
        except Exception as e:
            logger.error(f"Error validating schedule: {e}")
            return ScheduleValidation(
                is_valid=False,
                requirements_satisfied={},
                errors=[f"Validation error: {str(e)}"]
            )
    
    def _generate_terms(self, student_profile: StudentProfile) -> List[str]:
        """Generate list of term IDs to plan"""
        terms = []
        current_year = student_profile.year
        current_semester = student_profile.semester
        
        # Map semester to order
        semester_order = {Term.FALL: 0, Term.IAP: 1, Term.SPRING: 2}
        
        year = current_year
        semester_idx = semester_order[current_semester]
        semesters = [Term.FALL, Term.IAP, Term.SPRING]
        
        for _ in range(settings.SOLVER_MAX_TERMS):
            semester = semesters[semester_idx]
            
            # Skip IAP for now (simpler)
            if semester != Term.IAP:
                term_id = f"{2024 + year}{['FA', 'IA', 'SP'][semester_idx]}"
                terms.append(term_id)
            
            semester_idx = (semester_idx + 1) % 3
            if semester_idx == 0:
                year += 1
        
        return terms
    
    def _add_requirement_constraints(
        self,
        course_vars: Dict[str, Dict[str, cp_model.IntVar]],
        requirements: List[Requirement],
        available_courses: Dict[str, Course],
        terms: List[str]
    ):
        """Add constraints for degree requirements"""
        for req in requirements:
            if req.rule_type == RequirementType.SPECIFIC_COURSE:
                # Must take one of the allowed courses
                if req.courses_allowed:
                    course_taken_vars = []
                    for course_id in req.courses_allowed:
                        if course_id in course_vars:
                            # Sum over all terms for this course
                            taken = self.model.NewBoolVar(f"req_{req.id}_{course_id}")
                            self.model.Add(
                                sum(course_vars[course_id].values()) >= 1
                            ).OnlyEnforceIf(taken)
                            course_taken_vars.append(taken)
                    
                    # At least one required course must be taken
                    if course_taken_vars:
                        self.model.Add(sum(course_taken_vars) >= 1)
            
            elif req.rule_type == RequirementType.UNITS:
                # Must earn certain number of units from category
                if req.category and req.units_required:
                    category_units = []
                    for course_id, course in available_courses.items():
                        if req.category in course.meets_requirements:
                            if course_id in course_vars:
                                for term_id in terms:
                                    category_units.append(
                                        course_vars[course_id][term_id] * course.units
                                    )
                    
                    if category_units:
                        self.model.Add(sum(category_units) >= req.units_required)
    
    def _add_prerequisite_constraints(
        self,
        course_vars: Dict[str, Dict[str, cp_model.IntVar]],
        available_courses: Dict[str, Course],
        terms: List[str],
        completed_courses: List[str]
    ):
        """Add prerequisite constraints"""
        for course_id, course in available_courses.items():
            if course_id not in course_vars:
                continue
            
            for prereq in course.prerequisites:
                if prereq in completed_courses:
                    continue  # Already completed
                
                if prereq not in course_vars:
                    # Prerequisite not in schedule - can't take course
                    for term_id in terms:
                        self.model.Add(course_vars[course_id][term_id] == 0)
                    continue
                
                # Prerequisite must be taken before this course
                for i, term_id in enumerate(terms):
                    # If course taken in this term
                    # Then prerequisite must be taken in an earlier term
                    prereq_taken_before = []
                    for j in range(i):
                        prereq_taken_before.append(course_vars[prereq][terms[j]])
                    
                    if prereq_taken_before:
                        # If course taken in term i, sum of prereq in earlier terms >= 1
                        self.model.Add(
                            sum(prereq_taken_before) >= 1
                        ).OnlyEnforceIf(course_vars[course_id][term_id])
    
    def _add_offering_constraints(
        self,
        course_vars: Dict[str, Dict[str, cp_model.IntVar]],
        course_offerings: Dict[str, List[str]],
        terms: List[str]
    ):
        """Add constraints for when courses are offered"""
        for course_id in course_vars:
            for term_id in terms:
                # If course not offered in this term, can't take it
                if term_id in course_offerings:
                    if course_id not in course_offerings[term_id]:
                        self.model.Add(course_vars[course_id][term_id] == 0)
    
    def _add_unit_constraints(
        self,
        course_vars: Dict[str, Dict[str, cp_model.IntVar]],
        available_courses: Dict[str, Course],
        terms: List[str],
        student_profile: StudentProfile
    ):
        """Add unit limit constraints per term"""
        max_units = student_profile.preferences.get(
            "max_units_per_term",
            settings.DEFAULT_MAX_UNITS_PER_TERM
        )
        
        for term_id in terms:
            term_units = []
            for course_id, course in available_courses.items():
                if course_id in course_vars:
                    term_units.append(
                        course_vars[course_id][term_id] * course.units
                    )
            
            if term_units:
                self.model.Add(sum(term_units) <= max_units)
                # Also enforce minimum to avoid empty terms
                self.model.Add(sum(term_units) >= 12)  # At least 1 course
    
    def _add_objective(
        self,
        course_vars: Dict[str, Dict[str, cp_model.IntVar]],
        available_courses: Dict[str, Course],
        terms: List[str],
        preferences: Dict[str, float]
    ):
        """Add optimization objective"""
        objective_terms = []
        
        # Example: Prefer highly-rated courses
        rating_weight = preferences.get("maximize_ratings", 0.5)
        for course_id, course in available_courses.items():
            if course.student_rating and course_id in course_vars:
                rating = int(course.student_rating * 100)  # Scale to integer
                for term_id in terms:
                    objective_terms.append(
                        course_vars[course_id][term_id] * rating * int(rating_weight * 100)
                    )
        
        # Balance workload - penalize extreme term loads
        # (This is complex, simplified version)
        
        if objective_terms:
            self.model.Maximize(sum(objective_terms))
    
    def _extract_schedule(
        self,
        course_vars: Dict[str, Dict[str, cp_model.IntVar]],
        available_courses: Dict[str, Course],
        terms: List[str],
        student_profile: StudentProfile
    ) -> Schedule:
        """Extract schedule from solver solution"""
        scheduled_terms = []
        
        for term_id in terms:
            # Parse term (e.g., "2024FA" -> year=2024, semester=FALL)
            year = int(term_id[:4])
            semester_code = term_id[4:]
            semester = {"FA": Term.FALL, "SP": Term.SPRING, "IA": Term.IAP}[semester_code]
            
            # Get courses scheduled in this term
            courses_in_term = []
            for course_id, course in available_courses.items():
                if course_id in course_vars:
                    if self.solver.Value(course_vars[course_id][term_id]) == 1:
                        scheduled_course = ScheduledCourse(
                            course=course,
                            term=term_id,
                            year=year,
                            semester=semester,
                            meeting_times=[]  # Would be populated from catalog data
                        )
                        courses_in_term.append(scheduled_course)
            
            if courses_in_term:
                scheduled_term = ScheduledTerm(
                    year=year,
                    semester=semester,
                    courses=courses_in_term
                )
                scheduled_terms.append(scheduled_term)
        
        return Schedule(
            student_id=student_profile.id,
            terms=scheduled_terms
        )
    
    def _calculate_score(
        self,
        schedule: Schedule,
        preferences: Dict[str, float]
    ) -> float:
        """Calculate optimization score for schedule"""
        # Simplified scoring
        score = 0.0
        
        # Balance: Reward consistent term loads
        term_units = [term.total_units for term in schedule.terms]
        if term_units:
            avg_units = sum(term_units) / len(term_units)
            variance = sum((u - avg_units) ** 2 for u in term_units) / len(term_units)
            balance_score = 1.0 / (1.0 + variance / 100)  # Normalize
            score += balance_score * preferences.get("balance_workload", 0.5)
        
        return min(1.0, score)  # Normalize to 0-1
    
    def _check_requirement(
        self,
        requirement: Requirement,
        scheduled_courses: List[str],
        available_courses: Dict[str, Course]
    ) -> bool:
        """Check if a requirement is satisfied by scheduled courses"""
        if requirement.rule_type == RequirementType.SPECIFIC_COURSE:
            if requirement.courses_allowed:
                return any(c in scheduled_courses for c in requirement.courses_allowed)
        
        elif requirement.rule_type == RequirementType.UNITS:
            if requirement.category:
                total_units = sum(
                    available_courses[cid].units
                    for cid in scheduled_courses
                    if cid in available_courses
                    and requirement.category in available_courses[cid].meets_requirements
                )
                return total_units >= (requirement.units_required or 0)
        
        return False
    
    def _get_prior_courses(
        self,
        schedule: Schedule,
        target_year: int,
        target_semester: Term
    ) -> List[str]:
        """Get all courses taken before a specific term"""
        prior = []
        
        semester_order = {Term.FALL: 0, Term.IAP: 1, Term.SPRING: 2}
        target_order = (target_year, semester_order[target_semester])
        
        for term in schedule.terms:
            term_order = (term.year, semester_order[term.semester])
            if term_order < target_order:
                prior.extend([c.course.id for c in term.courses])
        
        return prior
