"""
Study Planner Core Service.
Coordinates prioritization, schedule generation, progress logging,
dynamic regeneration, and delta comparison reporting.
"""

from copy import deepcopy
from datetime import date
from typing import Dict, List, Optional, Tuple

from models import StudentProfile, StudyPlan, Topic, TopicAssessment, TopicPriority
from prioritizer import TopicPrioritizer
from scheduler import ScheduleGenerator
from verifier import AvailabilityVerifier


class StudyPlannerService:
    """
    Main orchestration service for the Personalized AI Study Planner.
    """

    def __init__(self, curriculum: Dict[str, Topic]):
        self.curriculum = curriculum
        self.prioritizer = TopicPrioritizer(curriculum)
        self.scheduler = ScheduleGenerator(curriculum)

    def generate_initial_plan(
        self,
        student: StudentProfile,
        start_date: date = date(2026, 10, 17),
        assessment_date: Optional[date] = None
    ) -> Tuple[StudyPlan, Dict]:
        """
        Generates the first baseline weekly study plan for a student profile.
        Also runs the availability verification check.
        """
        deadline = assessment_date or student.assessment_date
        priorities = self.prioritizer.calculate_priorities(
            assessments=student.assessments,
            assessment_date=deadline,
            current_date=start_date,
            weekly_study_hours=student.total_weekly_availability
        )
        plan = self.scheduler.generate_plan(
            student=student,
            priorities=priorities,
            start_date=start_date,
            assessment_date=deadline
        )
        audit = AvailabilityVerifier.verify(plan)
        return plan, audit

    def update_progress_and_regenerate(
        self,
        student: StudentProfile,
        previous_plan: StudyPlan,
        topic_updates: Dict[str, float],  # {topic_id: new_mastery_level}
        new_start_date: date = date(2026, 10, 20),
        adjusted_availability: Optional[Dict[str, float]] = None,
        assessment_date: Optional[date] = None
    ) -> Tuple[StudyPlan, Dict, str]:
        """
        Updates student topic mastery ratings and/or availability, regenerates the schedule,
        verifies constraints, and outputs an explanation of the shifts between old and new plans.
        """
        updated_student = deepcopy(student)
        deadline = assessment_date or student.assessment_date

        # Apply updated mastery ratings
        for t_id, new_mastery in topic_updates.items():
            if t_id in updated_student.assessments:
                updated_student.assessments[t_id].mastery_level = max(0.0, min(1.0, new_mastery))
            else:
                updated_student.assessments[t_id] = TopicAssessment(topic_id=t_id, mastery_level=new_mastery)

        # Apply adjusted availability if provided
        if adjusted_availability:
            updated_student.daily_availability = adjusted_availability

        # Recalculate priorities
        new_priorities = self.prioritizer.calculate_priorities(
            assessments=updated_student.assessments,
            assessment_date=deadline,
            current_date=new_start_date,
            weekly_study_hours=updated_student.total_weekly_availability
        )

        # Generate new plan
        new_plan = self.scheduler.generate_plan(
            student=updated_student,
            priorities=new_priorities,
            start_date=new_start_date,
            assessment_date=deadline
        )

        # Run verification check
        audit = AvailabilityVerifier.verify(new_plan)

        # Generate explainable comparison delta
        diff_explanation = self._explain_plan_adaptation(
            old_plan=previous_plan,
            new_plan=new_plan,
            topic_updates=topic_updates,
            new_start_date=new_start_date,
            deadline=deadline
        )

        return new_plan, audit, diff_explanation

    def _explain_plan_adaptation(
        self,
        old_plan: StudyPlan,
        new_plan: StudyPlan,
        topic_updates: Dict[str, float],
        new_start_date: date,
        deadline: date
    ) -> str:
        """
        Generates human-readable AI reasoning explaining why the schedule changed after regeneration.
        """
        days_rem = (deadline - new_start_date).days
        old_ranks = {p.topic.id: p for p in old_plan.priorities}
        new_ranks = {p.topic.id: p for p in new_plan.priorities}

        lines = []
        lines.append(f"AI Plan Adaptation Summary (Regenerated for {new_start_date.strftime('%d %B %Y')}):")
        lines.append(f"- Time remaining to assessment: {days_rem} days.")

        # Explain mastery progression impact
        for t_id, new_val in topic_updates.items():
            topic_name = self.curriculum[t_id].name if t_id in self.curriculum else t_id
            old_p = old_ranks.get(t_id)
            new_p = new_ranks.get(t_id)

            if old_p and new_p:
                old_m = int(old_p.mastery_level * 100)
                new_m = int(new_val * 100)
                rank_shift = old_p.rank - new_p.rank

                if new_m > old_m:
                    if new_p.rank > old_p.rank:
                        shift_str = f"Priority lowered from #{old_p.rank} to #{new_p.rank}"
                        effect = f"Hours reallocated ({old_p.recommended_hours}h -> {new_p.recommended_hours}h) to remaining weaker topics."
                    else:
                        shift_str = f"Remains at rank #{new_p.rank}"
                        effect = f"Session mix pivoted towards practice tasks & revision rather than raw theory."
                    lines.append(
                        f"* {topic_name} [{t_id}]: Mastery increased from {old_m}% to {new_m}%. "
                        f"{shift_str}. {effect}"
                    )
                elif new_m < old_m:
                    lines.append(
                        f"* {topic_name} [{t_id}]: Mastery adjusted downward from {old_m}% to {new_m}%. "
                        f"Priority raised from #{old_p.rank} to #{new_p.rank}. Allocated +{round(new_p.recommended_hours - old_p.recommended_hours, 1)}h."
                    )

        # Highlight newly elevated top focus topics
        top_new = new_plan.priorities[0]
        lines.append(
            f"* Current Top Priority: {top_new.topic.name} (Priority {top_new.normalized_score}/10) "
            f"now commands {top_new.recommended_hours} hours this cycle."
        )

        return "\n".join(lines)
