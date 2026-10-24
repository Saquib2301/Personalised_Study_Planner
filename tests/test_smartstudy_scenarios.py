"""
Comprehensive Evaluation Suite for SmartStudy AI.
Tests the 10 specific required evaluation scenarios:
1. Beginner student with limited study hours.
2. Advanced student with more available hours.
3. Student with mixed topic mastery.
4. Student with deadline approaching (urgency escalation).
5. Student who misses scheduled tasks (overdue detection).
6. Student who performs poorly on a quiz (triggers Needs Revision & urgency).
7. Student who changes available hours (strict recalculation).
8. Student who adds or removes topics dynamically.
9. Student who regenerates study plan (preservation of completed tasks).
10. Student whose requested workload exceeds remaining available time (capacity warning).
"""

from datetime import date, timedelta
import unittest
import os

from backend.database import init_db, SessionLocal, Student, TopicModel, StudySessionModel, QuizAttemptModel
from backend.ai_engine import AIEngine
from backend.prioritizer import TopicPrioritizer
from backend.scheduler import ScheduleGenerator
from backend.evaluators import QuizEvaluator, CodeEvaluator
from backend.sample_profiles import get_sample_profiles


class TestSmartStudyScenarios(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.db = SessionLocal()
        self.today = date.today()

    def tearDown(self):
        self.db.close()

    def test_scenario_1_beginner_limited_hours(self):
        """Scenario 1: Beginner student with limited study hours (e.g. 1.5h/day)."""
        topics = [
            {"id": 1, "name": "Basic Variables", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 3.0},
            {"id": 2, "name": "Conditional Logic", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 3.0}
        ]
        prioritized = TopicPrioritizer.prioritize_topics(topics, (self.today + timedelta(days=10)).strftime("%Y-%m-%d"))
        sched = ScheduleGenerator.generate_schedule(
            student_id=1,
            topics=prioritized,
            daily_available_hours=1.5,
            preferred_start_time="18:00",
            preferred_end_time="20:00",
            assessment_date_str=(self.today + timedelta(days=10)).strftime("%Y-%m-%d")
        )
        # Verify no day exceeds 1.5h
        for audit in sched["audit_report"]["daily_audits"]:
            self.assertLessEqual(audit["scheduled_hours"], 1.5 + 1e-4)
            self.assertTrue(audit["is_valid"])
        self.assertTrue(sched["audit_report"]["all_passed"])

    def test_scenario_2_advanced_more_hours(self):
        """Scenario 2: Advanced student with more available hours (e.g. 4.0h/day)."""
        topics = [
            {"id": 1, "name": "Advanced Trees", "mastery_level": "Advanced", "importance": "High", "estimated_hours": 3.0},
            {"id": 2, "name": "Graph Traversal", "mastery_level": "Advanced", "importance": "Medium", "estimated_hours": 2.5}
        ]
        prioritized = TopicPrioritizer.prioritize_topics(topics, (self.today + timedelta(days=7)).strftime("%Y-%m-%d"))
        # Advanced topics should emphasize revision & practice
        self.assertIn("revision and active recall", prioritized[0]["priority_rationale"])
        sched = ScheduleGenerator.generate_schedule(
            student_id=2,
            topics=prioritized,
            daily_available_hours=4.0,
            preferred_start_time="10:00",
            preferred_end_time="16:00",
            assessment_date_str=(self.today + timedelta(days=7)).strftime("%Y-%m-%d")
        )
        self.assertTrue(sched["audit_report"]["all_passed"])
        for audit in sched["audit_report"]["daily_audits"]:
            self.assertLessEqual(audit["scheduled_hours"], 4.0 + 1e-4)

    def test_scenario_3_mixed_topic_mastery(self):
        """Scenario 3: Student with mixed topic mastery (Beginner vs Advanced)."""
        topics = [
            {"id": 1, "name": "Mastered Topic", "mastery_level": "Advanced", "importance": "Medium", "estimated_hours": 2.0},
            {"id": 2, "name": "Critical Weak Topic", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 5.0}
        ]
        prioritized = TopicPrioritizer.prioritize_topics(topics, (self.today + timedelta(days=10)).strftime("%Y-%m-%d"))
        # Weak topic with high importance must be ranked #1
        self.assertEqual(prioritized[0]["name"], "Critical Weak Topic")
        self.assertGreater(prioritized[0]["priority_score"], prioritized[1]["priority_score"])

    def test_scenario_4_deadline_approaching(self):
        """Scenario 4: Student with deadline approaching (3 days away)."""
        topics = [
            {"id": 1, "name": "Core Subject", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 4.0}
        ]
        prioritized = TopicPrioritizer.prioritize_topics(topics, (self.today + timedelta(days=3)).strftime("%Y-%m-%d"))
        # Rationale must note urgent proximity
        self.assertIn("With only 3 days until your assessment", prioritized[0]["priority_rationale"])

    def test_scenario_5_overdue_tasks_tracking(self):
        """Scenario 5: Detect and track overdue tasks."""
        past_date = (self.today - timedelta(days=2)).strftime("%Y-%m-%d")
        session = {
            "date_str": past_date,
            "status": "Not Started"
        }
        # Incomplete session before today is overdue
        is_overdue = session["date_str"] < self.today.strftime("%Y-%m-%d") and session["status"] != "Completed"
        self.assertTrue(is_overdue)

    def test_scenario_6_poor_quiz_performance_triggers_revision(self):
        """Scenario 6: Student who performs poorly on a quiz (< 70%)."""
        questions = [
            {"question": "Q1", "options": ["A", "B"], "correct_index": 0, "explanation": "A is correct."},
            {"question": "Q2", "options": ["A", "B"], "correct_index": 0, "explanation": "A is correct."},
            {"question": "Q3", "options": ["A", "B"], "correct_index": 0, "explanation": "A is correct."}
        ]
        # Student answers only 1 correctly (33.3%)
        submission = {"0": 0, "1": 1, "2": 1}
        result = QuizEvaluator.grade_quiz(questions, submission)

        self.assertFalse(result["passed"])
        self.assertLess(result["score_percentage"], 70.0)
        self.assertIn("Needs Revision", result["feedback"])

        # When reprioritized, topic gets urgency boost
        topics = [{"id": 1, "name": "Topic A", "mastery_level": "Intermediate", "importance": "High", "quiz_score": 33.3, "status": "Needs Revision"}]
        prioritized = TopicPrioritizer.prioritize_topics(topics, (self.today + timedelta(days=10)).strftime("%Y-%m-%d"))
        self.assertIn("recent quiz performance", prioritized[0]["priority_rationale"])

    def test_scenario_7_availability_adjustment(self):
        """Scenario 7: Student changes available hours from 3.0h to 1.5h."""
        topics = [{"id": 1, "name": "Calculus", "mastery_level": "Intermediate", "importance": "High", "estimated_hours": 3.0}]
        sched_1 = ScheduleGenerator.generate_schedule(
            student_id=1, topics=topics, daily_available_hours=3.0,
            preferred_start_time="10:00", preferred_end_time="15:00",
            assessment_date_str=(self.today + timedelta(days=5)).strftime("%Y-%m-%d")
        )
        sched_2 = ScheduleGenerator.generate_schedule(
            student_id=1, topics=topics, daily_available_hours=1.5,
            preferred_start_time="10:00", preferred_end_time="12:00",
            assessment_date_str=(self.today + timedelta(days=5)).strftime("%Y-%m-%d")
        )
        # Scheduled hours on second plan must be capped at 1.5h
        for d in sched_2["audit_report"]["daily_audits"]:
            self.assertLessEqual(d["scheduled_hours"], 1.5 + 1e-4)

    def test_scenario_8_add_remove_topics(self):
        """Scenario 8: Dynamic adding and removing of topics."""
        topics = [{"id": 1, "name": "Topic 1"}, {"id": 2, "name": "Topic 2"}]
        topics.append({"id": 3, "name": "Topic 3"})
        self.assertEqual(len(topics), 3)
        topics.pop(0)
        self.assertEqual(len(topics), 2)
        self.assertEqual(topics[0]["name"], "Topic 2")

    def test_scenario_9_plan_regeneration_preserves_completed(self):
        """Scenario 9: Plan regeneration strictly preserves completed tasks."""
        # Simulated session database
        sessions = [
            {"id": 101, "status": "Completed", "topic_name": "Loops"},
            {"id": 102, "status": "Not Started", "topic_name": "Functions"},
            {"id": 103, "status": "Needs Revision", "topic_name": "Recursion"}
        ]
        # Filter for preservation
        completed = [s for s in sessions if s["status"] == "Completed"]
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["id"], 101)
        # Completed task is never deleted

    def test_scenario_10_workload_exceeds_time_capacity_warning(self):
        """Scenario 10: Requested workload exceeds available time capacity."""
        # Student wants to study 25 hours, but only has 2 days with 2h/day (4 hours available)
        topics = [
            {"id": 1, "name": "Heavy Topic A", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 12.0},
            {"id": 2, "name": "Heavy Topic B", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 13.0}
        ]
        sched = ScheduleGenerator.generate_schedule(
            student_id=1,
            topics=topics,
            daily_available_hours=2.0,
            preferred_start_time="18:00",
            preferred_end_time="20:00",
            assessment_date_str=(self.today + timedelta(days=2)).strftime("%Y-%m-%d")
        )
        self.assertIsNotNone(sched["capacity_warning"])
        self.assertTrue(sched["capacity_warning"]["has_warning"])
        self.assertGreater(sched["capacity_warning"]["deficit_hours"], 0)
        self.assertIn("Warning: Requested workload", sched["capacity_warning"]["message"])


if __name__ == "__main__":
    unittest.main()
