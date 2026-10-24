"""
Schedule Generator Engine.
Allocates study sessions, practice tasks, and revision time across available days.
Guarantees strictly that scheduled study time NEVER exceeds each student's stated availability.
"""

from datetime import date, timedelta
from typing import Dict, List
import uuid

from models import (
    DaySchedule,
    SessionType,
    StudentProfile,
    StudyPlan,
    StudySession,
    Topic,
    TopicPriority,
)


class ScheduleGenerator:
    """
    Constraint-satisfaction scheduler that translates topic priorities and
    daily availability into an actionable, balanced weekly study schedule.
    """

    DAY_NAMES = [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ]

    def __init__(self, topics: Dict[str, Topic]):
        self.topics = topics

    def generate_plan(
        self,
        student: StudentProfile,
        priorities: List[TopicPriority],
        start_date: date = date(2026, 10, 17),
        assessment_date: date = date(2026, 10, 24)
    ) -> StudyPlan:
        """
        Builds a full 7-day study plan adhering strictly to daily availability limits.
        """
        days_until = max(0, (assessment_date - start_date).days)
        total_avail = student.total_weekly_availability

        # 1. Initialize 7-day schedule containers based on student's availability
        day_schedules: List[DaySchedule] = []
        for i, day_name in enumerate(self.DAY_NAMES):
            current_day_date = start_date + timedelta(days=i)
            avail_hours = student.daily_availability.get(day_name, 0.0)
            day_schedules.append(
                DaySchedule(
                    day_name=day_name,
                    date_str=current_day_date.strftime("%Y-%m-%d"),
                    available_hours=avail_hours,
                    sessions=[]
                )
            )

        # 2. Decompose prioritized topics into atomic session work blocks
        work_units = self._create_work_units(priorities, total_avail)

        # 3. Fit work units into available daily slots (Constraint-satisfaction packing)
        self._pack_sessions(day_schedules, work_units)

        # 4. Final verification & safety clamp (guarantee invariant)
        self._enforce_availability_limits(day_schedules)

        study_plan = StudyPlan(
            student_id=student.id,
            student_name=student.name,
            generated_at=start_date.strftime("%Y-%m-%d"),
            assessment_date=assessment_date.strftime("%Y-%m-%d"),
            days_until_assessment=days_until,
            total_available_hours=total_avail,
            priorities=priorities,
            days=day_schedules
        )

        return study_plan

    def _create_work_units(
        self,
        priorities: List[TopicPriority],
        total_available_hours: float
    ) -> List[dict]:
        """
        Breaks down topic allocations into structured session blocks:
        - Concept Study
        - Practice Task
        - Revision Time
        """
        units = []

        # Target total hours to schedule: schedule up to 90-95% of available time to leave buffer,
        # but ensure realistic full utilization without ever overflowing.
        target_schedule_hours = min(
            total_available_hours,
            sum(p.recommended_hours for p in priorities)
        )

        for p in priorities:
            topic = p.topic
            rec_hours = p.recommended_hours
            if rec_hours <= 0.2:
                continue

            # Compute hours for each session type
            study_hrs = round(rec_hours * p.study_ratio, 1)
            practice_hrs = round(rec_hours * p.practice_ratio, 1)
            revision_hrs = round(rec_hours * p.revision_ratio, 1)

            # Ensure minimal practical chunk sizes (e.g., 0.5h, 1.0h, 1.5h)
            chunks = []
            if study_hrs >= 0.5:
                chunks.append((SessionType.CONCEPT_STUDY, study_hrs))
            if practice_hrs >= 0.5:
                chunks.append((SessionType.PRACTICE_TASK, practice_hrs))
            if revision_hrs >= 0.5:
                chunks.append((SessionType.REVISION, revision_hrs))

            # If chunks are too small, consolidate into the dominant type
            if not chunks and rec_hours >= 0.5:
                chunks.append((SessionType.PRACTICE_TASK, rec_hours))

            for stype, dur in chunks:
                objective, task_desc = self._get_session_content(topic, stype, p.mastery_level)
                units.append({
                    "topic_id": topic.id,
                    "topic_name": topic.name,
                    "session_type": stype,
                    "duration": dur,
                    "objective": objective,
                    "task_description": task_desc,
                    "rank": p.rank,
                    "exam_weight": topic.exam_weight
                })

        # Sort units: higher priority ranks first, Concept Study before Practice before Revision
        type_order = {
            SessionType.CONCEPT_STUDY: 0,
            SessionType.PRACTICE_TASK: 1,
            SessionType.REVISION: 2
        }
        units.sort(key=lambda u: (u["rank"], type_order[u["session_type"]]))
        return units

    def _pack_sessions(self, day_schedules: List[DaySchedule], work_units: List[dict]):
        """
        Distributes work units across the days ensuring no day exceeds availability.
        Uses a round-robin greedy bin-packing algorithm with capacity limits.
        """
        day_idx = 0
        total_days = len(day_schedules)

        for unit in work_units:
            duration = unit["duration"]
            placed = False

            # Try to place in days starting from day_idx to distribute load evenly
            for attempt in range(total_days):
                curr_idx = (day_idx + attempt) % total_days
                day = day_schedules[curr_idx]

                remaining_capacity = day.available_hours - day.scheduled_hours

                # Can it fit in full?
                if remaining_capacity >= (duration - 1e-4) and day.available_hours > 0:
                    self._add_session(day, unit, duration)
                    day_idx = (curr_idx + 1) % total_days
                    placed = True
                    break
                # If capacity is between 0.5h and duration, split the session if >= 0.5h
                elif remaining_capacity >= 0.5 and (duration - remaining_capacity) >= 0.4:
                    first_part = round(remaining_capacity, 1)
                    second_part = round(duration - first_part, 1)
                    
                    self._add_session(day, unit, first_part)
                    # Remaining part will be placed in subsequent day
                    unit["duration"] = second_part
                    day_idx = (curr_idx + 1) % total_days
                    # Continue trying to place the remaining piece
                    continue

            # If still not placed and any day has residual room >= 0.5h
            if not placed:
                for day in day_schedules:
                    rem = day.available_hours - day.scheduled_hours
                    if rem >= 0.5:
                        chunk = min(rem, unit["duration"])
                        self._add_session(day, unit, round(chunk, 1))
                        break

    def _add_session(self, day: DaySchedule, unit: dict, duration: float):
        """Helper to create and append a StudySession."""
        if duration <= 0:
            return
        session_id = f"SES-{uuid.uuid4().hex[:6].upper()}"
        session = StudySession(
            session_id=session_id,
            day_name=day.day_name,
            date_str=day.date_str,
            topic_id=unit["topic_id"],
            topic_name=unit["topic_name"],
            session_type=unit["session_type"],
            duration_hours=round(duration, 1),
            objective=unit["objective"],
            task_description=unit["task_description"],
            completed=False
        )
        day.sessions.append(session)

    def _enforce_availability_limits(self, day_schedules: List[DaySchedule]):
        """
        Hard safety check: Truncate or drop sessions if any rounding or split
        ever exceeds a day's available hours.
        """
        for day in day_schedules:
            if day.available_hours <= 0:
                day.sessions.clear()
                continue

            current_total = 0.0
            valid_sessions = []
            for s in day.sessions:
                if current_total + s.duration_hours <= day.available_hours + 1e-4:
                    valid_sessions.append(s)
                    current_total += s.duration_hours
                else:
                    # Clip session to remaining exact capacity if >= 0.3h
                    remaining = round(day.available_hours - current_total, 1)
                    if remaining >= 0.3:
                        s.duration_hours = remaining
                        valid_sessions.append(s)
                        current_total += remaining
                    break
            day.sessions = valid_sessions

    def _get_session_content(self, topic: Topic, stype: SessionType, mastery: float) -> tuple:
        """Generates dynamic objectives and specific practice tasks."""
        if stype == SessionType.CONCEPT_STUDY:
            obj = f"Deepen mental models and syntactic understanding of {topic.name}."
            desc = (
                f"Study core principles of {topic.name}. Trace execution with small test cases, "
                f"study standard patterns, and document edge cases."
            )
        elif stype == SessionType.PRACTICE_TASK:
            obj = f"Hands-on problem solving and algorithmic implementation for {topic.name}."
            if topic.practice_prompts:
                prompt_idx = min(len(topic.practice_prompts) - 1, int(mastery * len(topic.practice_prompts)))
                desc = f"Coding Drill: {topic.practice_prompts[prompt_idx]}"
            else:
                desc = f"Implement 2 medium-difficulty programming exercises covering {topic.name} under timed conditions."
        else:
            obj = f"Consolidate memory and active recall for {topic.name}."
            if topic.revision_prompts:
                desc = f"Quick Review: {topic.revision_prompts[0]}"
            else:
                desc = f"Flashcard self-quiz, formula review, and time-complexity dry-run for {topic.name}."

        return obj, desc
