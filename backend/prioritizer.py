"""
Intelligent Topic Prioritization Engine for SmartStudy AI.
Ranks topics using mastery level, importance, estimated learning time,
remaining days to exam, previous task completion, and quiz scores.
Produces transparent, explainable reasoning for every priority decision.
"""

from datetime import datetime, date
from typing import Dict, Any, List


class TopicPrioritizer:
    """
    Computes priority scores and generates clear human-readable explanations.
    """

    MASTERY_GAPS = {
        "Beginner": 0.90,
        "Intermediate": 0.50,
        "Advanced": 0.15
    }

    IMPORTANCE_WEIGHTS = {
        "High": 1.0,
        "Medium": 0.65,
        "Low": 0.35
    }

    @classmethod
    def prioritize_topics(
        cls,
        topics: List[Dict[str, Any]],
        assessment_date_str: str,
        current_date: date = None
    ) -> List[Dict[str, Any]]:
        """
        Calculates priority scores, sorts topics, and assigns rankings and explanations.
        """
        if current_date is None:
            current_date = date.today()

        try:
            exam_date = datetime.strptime(assessment_date_str, "%Y-%m-%d").date()
            days_remaining = max(1, (exam_date - current_date).days)
        except Exception:
            days_remaining = 14

        scored_topics = []

        for t in topics:
            name = t.get("name", "Unknown Topic")
            mastery = t.get("mastery_level", "Beginner")
            importance = t.get("importance", "Medium")
            est_hours = float(t.get("estimated_hours", 4.0))
            quiz_score = t.get("quiz_score") # None or 0.0 - 100.0
            status = t.get("status", "Pending")

            # 1. Knowledge Gap Factor (0.15 to 0.90)
            gap = cls.MASTERY_GAPS.get(mastery, 0.60)

            # If student previously took a quiz and scored poorly, widen the gap
            if quiz_score is not None:
                if quiz_score < 70.0:
                    gap = min(1.0, gap + 0.25)
                elif quiz_score >= 85.0:
                    gap = max(0.10, gap - 0.20)

            # If marked Needs Revision, give urgency boost
            if status == "Needs Revision":
                gap = min(1.0, gap + 0.20)

            # 2. Importance Factor (0.35 to 1.0)
            weight = cls.IMPORTANCE_WEIGHTS.get(importance, 0.65)

            # 3. Urgency / Time Factor
            if days_remaining <= 5:
                urgency = 1.35
            elif days_remaining <= 10:
                urgency = 1.20
            else:
                urgency = 1.05

            # 4. Effort Scaler (longer topics require earlier start)
            effort_factor = 1.0 + (min(est_hours, 10.0) / 30.0)

            # Raw composite formula
            raw_score = (gap ** 1.15) * weight * urgency * effort_factor

            # Maintenance floor: Even advanced topics must have minimal maintenance weight
            maintenance_floor = 0.08 * weight
            final_score = max(maintenance_floor, raw_score)

            # Generate natural language explainability
            rationale = cls._generate_explanation(
                name=name,
                mastery=mastery,
                importance=importance,
                days_remaining=days_remaining,
                quiz_score=quiz_score,
                status=status
            )

            scored_topics.append({
                **t,
                "priority_score": round(final_score * 10, 1),
                "raw_score": final_score,
                "gap": gap,
                "weight": weight,
                "priority_rationale": rationale
            })

        # Sort descending by priority score
        scored_topics.sort(key=lambda x: x["raw_score"], reverse=True)

        for rank, item in enumerate(scored_topics, start=1):
            item["rank"] = rank

        return scored_topics

    @classmethod
    def _generate_explanation(
        cls,
        name: str,
        mastery: str,
        importance: str,
        days_remaining: int,
        quiz_score: float,
        status: str
    ) -> str:
        """Constructs transparent reasoning for why a topic was prioritized."""
        parts = []

        # Mastery & Importance narrative
        if mastery == "Beginner" and importance == "High":
            parts.append(f"{name} has been given TOP PRIORITY because your mastery is Beginner and importance is High, requiring deep conceptual foundation and substantial practice.")
        elif mastery == "Beginner" and importance in ["Medium", "Low"]:
            parts.append(f"{name} is prioritized for early fundamentals due to Beginner mastery, balanced with {importance} exam weighting.")
        elif mastery == "Intermediate" and importance == "High":
            parts.append(f"{name} has High importance; building on your Intermediate foundation with targeted exercises will yield rapid score gains.")
        elif mastery == "Intermediate":
            parts.append(f"{name} is scheduled for focused application drills based on your Intermediate mastery and {importance} importance.")
        elif mastery == "Advanced":
            parts.append(f"{name} receives less initial study time because you have strong Advanced mastery, but is reserved for scheduled revision and active recall.")

        # Performance or revision trigger
        if status == "Needs Revision" or (quiz_score is not None and quiz_score < 70.0):
            score_txt = f"{int(quiz_score)}%" if quiz_score is not None else "unmet criteria"
            parts.append(f"Urgency is amplified because your recent quiz performance ({score_txt}) indicated topics needing revision.")

        # Deadline urgency
        if days_remaining <= 7:
            parts.append(f"With only {days_remaining} days until your assessment, high-yield practice must be prioritized immediately.")

        return " ".join(parts)
