"""
Data models for the Personalized AI Study Planner.
Defines topics, student profiles, study sessions, and generated plans.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional


class SessionType(str, Enum):
    CONCEPT_STUDY = "Concept Study"
    PRACTICE_TASK = "Practice Task"
    REVISION = "Revision & Active Recall"


@dataclass
class Topic:
    """Represents a topic within the programming assessment syllabus."""
    id: str
    name: str
    category: str
    exam_weight: float       # Scale 1.0 to 10.0 (importance in assessment)
    difficulty: float        # Scale 1.0 to 5.0 (cognitive complexity)
    estimated_hours: float   # Baseline hours required for full mastery from 0%
    prerequisites: List[str] = field(default_factory=list)
    practice_prompts: List[str] = field(default_factory=list)
    revision_prompts: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "exam_weight": self.exam_weight,
            "difficulty": self.difficulty,
            "estimated_hours": self.estimated_hours,
            "prerequisites": self.prerequisites,
            "practice_prompts": self.practice_prompts,
            "revision_prompts": self.revision_prompts,
        }


@dataclass
class TopicAssessment:
    """A student's self-assessment for a specific topic."""
    topic_id: str
    mastery_level: float     # 0.0 (novice) to 1.0 (expert)
    confidence: float = 0.5  # 0.0 to 1.0
    notes: str = ""

    @property
    def knowledge_gap(self) -> float:
        return max(0.0, 1.0 - self.mastery_level)


@dataclass
class TopicPriority:
    """Calculated priority ranking and AI explanation for a topic."""
    topic: Topic
    mastery_level: float
    knowledge_gap: float
    raw_score: float
    normalized_score: float  # 0.0 to 10.0
    rank: int
    recommended_hours: float
    study_ratio: float       # Percentage of time for concept study
    practice_ratio: float    # Percentage of time for hands-on practice
    revision_ratio: float    # Percentage of time for revision
    rationale: str
    prerequisite_status: str


@dataclass
class StudySession:
    """An individual scheduled study session within a day."""
    session_id: str
    day_name: str
    date_str: str
    topic_id: str
    topic_name: str
    session_type: SessionType
    duration_hours: float
    objective: str
    task_description: str
    completed: bool = False
    notes: Optional[str] = None


@dataclass
class DaySchedule:
    """A single day's scheduled sessions and availability audit."""
    day_name: str
    date_str: str
    available_hours: float
    sessions: List[StudySession] = field(default_factory=list)

    @property
    def scheduled_hours(self) -> float:
        return round(sum(s.duration_hours for s in self.sessions), 2)

    @property
    def remaining_buffer_hours(self) -> float:
        return round(self.available_hours - self.scheduled_hours, 2)

    @property
    def is_valid(self) -> bool:
        """Strict check: scheduled hours must NEVER exceed available hours."""
        # Using a tiny floating-point tolerance of 1e-4
        return self.scheduled_hours <= (self.available_hours + 1e-4)


@dataclass
class StudyPlan:
    """Comprehensive weekly plan generated for a student."""
    student_id: str
    student_name: str
    generated_at: str
    assessment_date: str
    days_until_assessment: int
    total_available_hours: float
    priorities: List[TopicPriority]
    days: List[DaySchedule]

    @property
    def total_scheduled_hours(self) -> float:
        return round(sum(d.scheduled_hours for d in self.days), 2)

    @property
    def total_buffer_hours(self) -> float:
        return round(self.total_available_hours - self.total_scheduled_hours, 2)

    @property
    def is_valid(self) -> bool:
        """Global validation check for availability constraints."""
        total_valid = self.total_scheduled_hours <= (self.total_available_hours + 1e-4)
        daily_valid = all(d.is_valid for d in self.days)
        return total_valid and daily_valid


@dataclass
class StudentProfile:
    """Represents a student preparing for the assessment."""
    id: str
    name: str
    persona_tagline: str
    daily_availability: Dict[str, float]  # e.g., {"Monday": 3.0, "Tuesday": 2.5, ...}
    assessments: Dict[str, TopicAssessment]
    assessment_date: date = date(2026, 10, 24)

    @property
    def total_weekly_availability(self) -> float:
        return round(sum(self.daily_availability.values()), 2)
