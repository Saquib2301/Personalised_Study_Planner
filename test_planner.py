"""
Comprehensive Test Suite for Personalized AI Study Planner.
Tests:
- Strict availability constraints across all sample profiles
- Edge cases (zero-hour days, extreme time limits, full mastery)
- AI prioritization engine and prerequisite graph mechanics
- Dynamic progress updates and schedule regeneration
"""

from datetime import date
import unittest

from models import StudentProfile, TopicAssessment
from planner_service import StudyPlannerService
from sample_data import get_default_curriculum, get_sample_students
from verifier import AvailabilityVerifier


class TestStudyPlanner(unittest.TestCase):

    def setUp(self):
        self.curriculum = get_default_curriculum()
        self.students = get_sample_students()
        self.service = StudyPlannerService(self.curriculum)
        self.deadline = date(2026, 10, 24)
        self.start_date = date(2026, 10, 17)

    def test_sample_students_availability_compliance(self):
        """
        Critical Requirement Check:
        Scheduled study time must NEVER exceed stated availability for any sample student.
        """
        for student_id, student in self.students.items():
            with self.subTest(student=student.name):
                plan, audit = self.service.generate_initial_plan(
                    student=student,
                    start_date=self.start_date,
                    assessment_date=self.deadline
                )

                # 1. Global audit status must be PASS
                self.assertTrue(
                    audit["all_passed"],
                    f"Audit failed for {student.name}: {audit['violations']}"
                )
                self.assertEqual(audit["status"], "PASS")
                self.assertEqual(len(audit["violations"]), 0)

                # 2. Total scheduled hours must not exceed total available hours
                self.assertLessEqual(
                    audit["total_scheduled_hours"],
                    audit["total_available_hours"] + 1e-4,
                    f"Total hours exceeded for {student.name}"
                )

                # 3. Every individual day must not exceed that day's available hours
                for day_audit in audit["daily_audits"]:
                    self.assertTrue(
                        day_audit["is_valid"],
                        f"Day {day_audit['day_name']} exceeded availability for {student.name}"
                    )
                    self.assertLessEqual(
                        day_audit["scheduled_hours"],
                        day_audit["available_hours"] + 1e-4
                    )
                    self.assertGreaterEqual(
                        day_audit["buffer_hours"],
                        -1e-4,
                        f"Buffer cannot be negative on {day_audit['day_name']}"
                    )

    def test_zero_hour_rest_days(self):
        """Days with 0.0 available hours must have zero scheduled sessions."""
        rest_student = StudentProfile(
            id="rest_student",
            name="Rest Student",
            persona_tagline="Studies Mon-Fri, Strict Rest on Weekends",
            daily_availability={
                "Monday": 3.0,
                "Tuesday": 3.0,
                "Wednesday": 3.0,
                "Thursday": 3.0,
                "Friday": 3.0,
                "Saturday": 0.0,  # Rest
                "Sunday": 0.0,    # Rest
            },
            assessments=self.students["alex_rivera"].assessments,
            assessment_date=self.deadline
        )
        plan, audit = self.service.generate_initial_plan(rest_student)
        self.assertTrue(audit["all_passed"])

        sat = next(d for d in plan.days if d.day_name == "Saturday")
        sun = next(d for d in plan.days if d.day_name == "Sunday")
        self.assertEqual(sat.scheduled_hours, 0.0)
        self.assertEqual(len(sat.sessions), 0)
        self.assertEqual(sun.scheduled_hours, 0.0)
        self.assertEqual(len(sun.sessions), 0)

    def test_minimal_available_hours(self):
        """Very low availability (e.g. 2.5 hours in total week) must be respected."""
        busy_student = StudentProfile(
            id="busy_student",
            name="Ultra Busy Student",
            persona_tagline="Extreme time crunch - 2.5 hrs weekly",
            daily_availability={
                "Monday": 0.5,
                "Tuesday": 0.0,
                "Wednesday": 0.5,
                "Thursday": 0.0,
                "Friday": 0.5,
                "Saturday": 1.0,
                "Sunday": 0.0,
            },
            assessments=self.students["maya_chen"].assessments,
            assessment_date=self.deadline
        )
        plan, audit = self.service.generate_initial_plan(busy_student)
        self.assertTrue(audit["all_passed"])
        self.assertLessEqual(plan.total_scheduled_hours, 2.5 + 1e-4)

    def test_prioritization_engine_and_explanations(self):
        """Prioritization should assign higher priority to high-weight, low-mastery topics."""
        alex = self.students["alex_rivera"]
        plan, _ = self.service.generate_initial_plan(alex)

        # Ensure all topics have valid ranks and non-empty explanations
        ranks = [p.rank for p in plan.priorities]
        self.assertEqual(ranks, list(range(1, len(plan.priorities) + 1)))

        for p in plan.priorities:
            self.assertTrue(len(p.rationale) > 20)
            self.assertGreaterEqual(p.normalized_score, 1.0)
            self.assertLessEqual(p.normalized_score, 10.0)

        # In Alex's assessment:
        # Dynamic Programming & Trees have huge gap (0.90 gap) and high weight (9.5)
        # Python Fundamentals is already at 85% mastery with weight 6.0
        dp_priority = next(p for p in plan.priorities if p.topic.id == "DYN_PROG")
        py_priority = next(p for p in plan.priorities if p.topic.id == "PY_FUND")
        self.assertLess(dp_priority.rank, py_priority.rank)

    def test_progress_update_and_regeneration(self):
        """
        Updating a student's mastery should rebalance hours, regenerate the schedule,
        and maintain strict availability compliance.
        """
        alex = self.students["alex_rivera"]
        initial_plan, _ = self.service.generate_initial_plan(alex)

        # Alex studies hard on Recursion and improves mastery from 30% to 85%
        new_plan, audit, diff_explanation = self.service.update_progress_and_regenerate(
            student=alex,
            previous_plan=initial_plan,
            topic_updates={"RECURSION": 0.85},
            new_start_date=date(2026, 10, 20),
            assessment_date=self.deadline
        )

        # Invariant must remain strictly True
        self.assertTrue(audit["all_passed"])
        self.assertLessEqual(new_plan.total_scheduled_hours, alex.total_weekly_availability + 1e-4)

        # Rationale must explain the shift
        self.assertIn("RECURSION", diff_explanation)
        self.assertIn("Mastery increased from 30% to 85%", diff_explanation)


if __name__ == "__main__":
    unittest.main()
