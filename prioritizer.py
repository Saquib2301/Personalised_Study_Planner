"""
AI Prioritization Engine for Study Planning.
Evaluates topics using mastery level, exam importance, difficulty,
prerequisite relationships, and time remaining until the assessment.
Provides explainable AI reasoning for each priority decision.
"""

import math
from datetime import date
from typing import Dict, List, Tuple
from models import Topic, TopicAssessment, TopicPriority, SessionType


class TopicPrioritizer:
    """
    Computes multi-factor priority scores for topics and produces
    transparent, human-readable explanations of the ranking rationale.
    """

    def __init__(self, topics: Dict[str, Topic]):
        self.topics = topics

    def calculate_priorities(
        self,
        assessments: Dict[str, TopicAssessment],
        assessment_date: date,
        current_date: date = date(2026, 10, 17),
        weekly_study_hours: float = 20.0
    ) -> List[TopicPriority]:
        """
        Calculates priority scores, ranks topics, and crafts explainable rationales.
        """
        days_remaining = max(1, (assessment_date - current_date).days)
        
        # 1. Determine prerequisite dependency graph & unmastered downstream impact
        prereq_impact = self._compute_prerequisite_impact(assessments)

        scored_topics = []

        for topic_id, topic in self.topics.items():
            assessment = assessments.get(
                topic_id,
                TopicAssessment(topic_id=topic_id, mastery_level=0.5, confidence=0.5)
            )
            mastery = max(0.0, min(1.0, assessment.mastery_level))
            gap = 1.0 - mastery

            # --- Multi-factor Scoring Algorithm ---
            # Factor A: Knowledge Gap & Exam Importance
            # We use gap^1.15 so severe deficits on high-weight topics escalate rapidly
            base_deficit = (gap ** 1.15) * (topic.exam_weight / 10.0)

            # Factor B: Difficulty Cognitive Load Factor (1.0 to 1.4)
            difficulty_factor = 1.0 + (topic.difficulty - 1.0) * 0.10

            # Factor C: Prerequisite Multiplier
            # If this topic is blocking downstream high-weight topics, boost its priority
            blocked_dependents = prereq_impact.get(topic_id, [])
            unmastered_dependents_count = len(blocked_dependents)
            prereq_multiplier = 1.0 + (unmastered_dependents_count * 0.20)

            # Factor D: Time Remaining / Urgency Factor
            # When time is short (< 14 days), unmastered high-weight topics become urgent
            if days_remaining <= 7:
                urgency_multiplier = 1.0 + 0.35 * (topic.exam_weight / 10.0)
            elif days_remaining <= 14:
                urgency_multiplier = 1.0 + 0.20 * (topic.exam_weight / 10.0)
            else:
                urgency_multiplier = 1.0 + 0.10 * (topic.exam_weight / 10.0)

            # Factor E: Maintenance Baseline for High Mastery
            # Even if mastery is 100%, topics still need light maintenance/revision (10% floor)
            maintenance_floor = 0.08 * (topic.exam_weight / 10.0)

            raw_score = max(
                maintenance_floor,
                base_deficit * difficulty_factor * prereq_multiplier * urgency_multiplier
            )

            # Prerequisite status check (is this topic itself blocked by another weak topic?)
            unmet_prereqs = self._get_unmet_prerequisites(topic, assessments)

            scored_topics.append({
                "topic": topic,
                "mastery": mastery,
                "gap": gap,
                "raw_score": raw_score,
                "blocked_dependents": blocked_dependents,
                "unmet_prereqs": unmet_prereqs,
                "days_remaining": days_remaining,
            })

        # Sort by raw score descending
        scored_topics.sort(key=lambda x: x["raw_score"], reverse=True)

        # Normalize score to 0.0 - 10.0 scale
        max_raw = max(x["raw_score"] for x in scored_topics) if scored_topics else 1.0
        min_raw = min(x["raw_score"] for x in scored_topics) if scored_topics else 0.0
        spread = max(0.001, max_raw - min_raw)

        # Distribute recommended study hours proportionally across topics based on raw score
        total_raw = sum(x["raw_score"] for x in scored_topics)
        
        priorities: List[TopicPriority] = []
        for rank, item in enumerate(scored_topics, start=1):
            topic = item["topic"]
            mastery = item["mastery"]
            gap = item["gap"]
            raw_score = item["raw_score"]
            days = item["days_remaining"]
            unmet = item["unmet_prereqs"]
            blocked = item["blocked_dependents"]

            # Normalized priority score from 1.0 to 10.0
            normalized = round(1.0 + (raw_score / max_raw) * 9.0, 1)

            # Allocation proportion of available weekly hours
            share = raw_score / total_raw if total_raw > 0 else (1.0 / len(scored_topics))
            rec_hours = round(share * weekly_study_hours, 1)

            # Compute session type distribution based on mastery & urgency
            study_pct, practice_pct, revision_pct = self._compute_session_distribution(mastery, days)

            # Generate natural language explainability rationale
            rationale, prereq_status = self._generate_explanation(
                rank=rank,
                topic=topic,
                mastery=mastery,
                gap=gap,
                normalized_score=normalized,
                days_remaining=days,
                unmet_prereqs=unmet,
                blocked_dependents=blocked,
                rec_hours=rec_hours
            )

            priorities.append(
                TopicPriority(
                    topic=topic,
                    mastery_level=mastery,
                    knowledge_gap=gap,
                    raw_score=raw_score,
                    normalized_score=normalized,
                    rank=rank,
                    recommended_hours=rec_hours,
                    study_ratio=study_pct,
                    practice_ratio=practice_pct,
                    revision_ratio=revision_pct,
                    rationale=rationale,
                    prerequisite_status=prereq_status
                )
            )

        return priorities

    def _compute_session_distribution(self, mastery: float, days_remaining: int) -> Tuple[float, float, float]:
        """
        Dynamically shifts study, practice, and revision ratios based on
        mastery level and deadline proximity.
        """
        # Baseline splits
        if mastery < 0.35:
            # Low mastery: needs concept grounding before solving tough problems
            study, practice, revision = 0.50, 0.40, 0.10
        elif mastery < 0.70:
            # Medium mastery: active problem-solving drills yield best results
            study, practice, revision = 0.25, 0.55, 0.20
        else:
            # High mastery: active recall, edge-case practice, and spaced revision
            study, practice, revision = 0.10, 0.45, 0.45

        # In final week before assessment (<= 7 days), amplify revision & practice
        if days_remaining <= 7:
            revision_boost = 0.10
            study = max(0.05, study - revision_boost)
            revision += revision_boost

        return (round(study, 2), round(practice, 2), round(revision, 2))

    def _compute_prerequisite_impact(self, assessments: Dict[str, TopicAssessment]) -> Dict[str, List[str]]:
        """Finds which unmastered downstream topics are blocked if this topic is weak."""
        impact: Dict[str, List[str]] = {t_id: [] for t_id in self.topics}
        for child_id, child_topic in self.topics.items():
            child_assessment = assessments.get(child_id)
            child_mastery = child_assessment.mastery_level if child_assessment else 0.5
            # If child topic is not mastered (< 0.70), its prerequisites matter heavily
            if child_mastery < 0.70:
                for prereq_id in child_topic.prerequisites:
                    if prereq_id in impact:
                        impact[prereq_id].append(child_topic.name)
        return impact

    def _get_unmet_prerequisites(self, topic: Topic, assessments: Dict[str, TopicAssessment]) -> List[str]:
        """Returns names of prerequisites that the student hasn't mastered (< 0.60)."""
        unmet = []
        for p_id in topic.prerequisites:
            p_topic = self.topics.get(p_id)
            if p_topic:
                p_assessment = assessments.get(p_id)
                mastery = p_assessment.mastery_level if p_assessment else 0.5
                if mastery < 0.60:
                    unmet.append(f"{p_topic.name} ({int(mastery*100)}% mastery)")
        return unmet

    def _generate_explanation(
        self,
        rank: int,
        topic: Topic,
        mastery: float,
        gap: float,
        normalized_score: float,
        days_remaining: int,
        unmet_prereqs: List[str],
        blocked_dependents: List[str],
        rec_hours: float
    ) -> Tuple[str, str]:
        """
        Synthesizes a transparent, human-readable AI explanation of why the topic
        was assigned this priority rank and study allocation.
        """
        reasons = []

        # Exam Weight Analysis
        if topic.exam_weight >= 8.0:
            reasons.append(f"Crucial syllabus topic with high exam weighting ({topic.exam_weight}/10)")
        elif topic.exam_weight >= 5.0:
            reasons.append(f"Moderate exam weighting ({topic.exam_weight}/10)")
        else:
            reasons.append(f"Minor exam weighting ({topic.exam_weight}/10)")

        # Mastery & Knowledge Gap Analysis
        mastery_pct = int(mastery * 100)
        gap_pct = int(gap * 100)
        if mastery < 0.30:
            reasons.append(f"critical knowledge deficit ({gap_pct}% gap, self-assessed mastery only {mastery_pct}%)")
        elif mastery < 0.65:
            reasons.append(f"developing proficiency ({mastery_pct}% mastery) with room for targeted improvement")
        else:
            reasons.append(f"strong existing competency ({mastery_pct}% mastery) requiring maintenance and test-readiness polish")

        # Prerequisite Dependency Analysis
        prereq_status_str = "All prerequisites satisfied."
        if blocked_dependents:
            dependents_str = ", ".join(blocked_dependents[:2])
            reasons.append(f"acts as a critical gateway concept for downstream topics: {dependents_str}")
        
        if unmet_prereqs:
            unmet_str = ", ".join(unmet_prereqs)
            prereq_status_str = f"Warning: Unmastered foundational prerequisites: {unmet_str}."

        # Time Proximity / Urgency Analysis
        if days_remaining <= 7:
            reasons.append(f"assessment is in only {days_remaining} days (urgent revision cycle)")
        elif days_remaining <= 14:
            reasons.append(f"{days_remaining} days remaining until assessment date")

        # Compile final narrative
        explanation = (
            f"Ranked #{rank} (Priority Score: {normalized_score}/10). "
            f"Prioritized due to {reasons[0]} paired with {reasons[1]}. "
        )
        if len(reasons) > 2:
            explanation += f"Additionally, {reasons[2]}. "
        explanation += f"Recommended weekly allocation: {rec_hours} hours."

        return explanation, prereq_status_str
