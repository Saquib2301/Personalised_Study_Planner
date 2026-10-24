"""
Three realistic synthetic student profiles meeting the exact specification:
- Profile 1: Beginner Programmer (Variables, Loops, Functions, Arrays • 2 hrs/day)
- Profile 2: Intermediate Programmer (Recursion, Searching, Sorting, Linked Lists • 3 hrs/day)
- Profile 3: Operating Systems Student (Process Scheduling, Synchronisation, Deadlocks, Memory Management • 90 min/day)
"""

from datetime import date, timedelta
from typing import Dict, Any


def get_sample_profiles() -> Dict[str, Dict[str, Any]]:
    """Returns sample profile definitions with dynamic future assessment dates."""
    today = date.today()

    return {
        "profile_1_beginner": {
            "id": "profile_1_beginner",
            "name": "Alex Rivera",
            "assessment_name": "CS101 Intro to Programming Practical",
            "subject_name": "Python Programming Fundamentals",
            "daily_available_hours": 2.0,
            "preferred_start_time": "18:00",
            "preferred_end_time": "20:30",
            "preferred_session_duration": 40,
            "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "assessment_date": (today + timedelta(days=10)).strftime("%Y-%m-%d"),
            "goal": "Build solid programming fundamentals from scratch",
            "topics": [
                {"name": "Variables & Primitive Types", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 3.0},
                {"name": "Control Flow & Loops (for/while)", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 4.0},
                {"name": "Functions, Scope & Parameters", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 3.5},
                {"name": "Arrays & List Manipulations", "mastery_level": "Intermediate", "importance": "Medium", "estimated_hours": 3.0}
            ]
        },
        "profile_2_intermediate": {
            "id": "profile_2_intermediate",
            "name": "Maya Chen",
            "assessment_name": "Data Structures & Algorithms Midterm",
            "subject_name": "Data Structures & Algorithms",
            "daily_available_hours": 3.0,
            "preferred_start_time": "15:00",
            "preferred_end_time": "19:00",
            "preferred_session_duration": 50,
            "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
            "assessment_date": (today + timedelta(days=14)).strftime("%Y-%m-%d"),
            "goal": "Prepare for a timed algorithmic coding assessment",
            "topics": [
                {"name": "Recursion & Backtracking", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 5.0},
                {"name": "Binary Search & Monotonic Spaces", "mastery_level": "Intermediate", "importance": "High", "estimated_hours": 4.0},
                {"name": "Sorting Algorithms (Merge & Quick Sort)", "mastery_level": "Intermediate", "importance": "Medium", "estimated_hours": 3.5},
                {"name": "Singly & Doubly Linked Lists", "mastery_level": "Advanced", "importance": "Medium", "estimated_hours": 2.5}
            ]
        },
        "profile_3_os": {
            "id": "profile_3_os",
            "name": "Sam Taylor",
            "assessment_name": "Operating Systems Final Examination",
            "subject_name": "Operating Systems",
            "daily_available_hours": 1.5,
            "preferred_start_time": "20:00",
            "preferred_end_time": "22:00",
            "preferred_session_duration": 45,
            "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Sunday"],
            "assessment_date": (today + timedelta(days=12)).strftime("%Y-%m-%d"),
            "goal": "Master OS concurrency theory, scheduling algorithms, and memory management",
            "topics": [
                {"name": "CPU Process Scheduling (RR, SJF, Priority)", "mastery_level": "Intermediate", "importance": "High", "estimated_hours": 3.0},
                {"name": "Process Synchronisation & Semaphores", "mastery_level": "Beginner", "importance": "High", "estimated_hours": 4.5},
                {"name": "Deadlocks & Banker's Algorithm", "mastery_level": "Intermediate", "importance": "Medium", "estimated_hours": 3.0},
                {"name": "Virtual Memory, Paging & TLB", "mastery_level": "Advanced", "importance": "High", "estimated_hours": 3.0}
            ]
        }
    }
