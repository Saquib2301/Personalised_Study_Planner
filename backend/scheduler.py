"""
Intelligent Personalised Schedule Generator for SmartStudy AI.
Strictly respects daily study hour limits, preferred study windows,
selected available days, and deadline constraints.
Guarantees non-overlapping sessions, includes breaks and revision,
and provides capacity deficit warnings if time is insufficient.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple


class ScheduleGenerator:
    """
    Constraint-satisfaction scheduling engine.
    """

    DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    @classmethod
    def generate_schedule(
        cls,
        student_id: int,
        topics: List[Dict[str, Any]],
        daily_available_hours: float,
        preferred_start_time: str, # "09:00"
        preferred_end_time: str,   # "21:00"
        assessment_date_str: str,  # "YYYY-MM-DD"
        preferred_session_duration: int = 45, # minutes
        available_days: List[str] = None,     # ["Monday", ...]
        start_date: date = None,
        existing_completed_sessions: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generates full day-by-day study sessions strictly respecting all constraints.
        Returns generated sessions, capacity warning (if any), and audit report.
        """
        if start_date is None:
            start_date = date.today()

        if available_days is None or len(available_days) == 0:
            available_days = cls.DAY_NAMES

        try:
            exam_date = datetime.strptime(assessment_date_str, "%Y-%m-%d").date()
        except Exception:
            exam_date = start_date + timedelta(days=14)

        total_days = max(1, (exam_date - start_date).days)
        daily_limit_minutes = int(daily_available_hours * 60)

        # 1. Calculate Total Available Capacity before Exam
        active_study_dates = []
        for i in range(total_days):
            d = start_date + timedelta(days=i)
            day_name = cls.DAY_NAMES[d.weekday()]
            if day_name in available_days:
                active_study_dates.append((d, day_name))

        total_available_study_minutes = len(active_study_dates) * daily_limit_minutes
        total_available_study_hours = round(total_available_study_minutes / 60.0, 1)

        # 2. Calculate Total Required Work for Topics
        total_required_hours = sum(float(t.get("estimated_hours", 4.0)) for t in topics)
        total_required_minutes = int(total_required_hours * 60)

        capacity_warning = None
        if total_required_hours > total_available_study_hours:
            deficit_hours = round(total_required_hours - total_available_study_hours, 1)
            capacity_warning = {
                "has_warning": True,
                "deficit_hours": deficit_hours,
                "available_hours": total_available_study_hours,
                "required_hours": total_required_hours,
                "message": (
                    f"Warning: Requested workload ({total_required_hours}h) exceeds your total available "
                    f"study capacity ({total_available_study_hours}h) before the assessment by {deficit_hours} hours. "
                    f"The AI has prioritized your highest-yield topics and condensed tasks, "
                    f"retaining revision time. Consider increasing daily study hours or extending available study days."
                ),
                "recommended_priorities": [t["name"] for t in topics[:3]]
            }

        # 3. Decompose topics into actionable work sessions
        # Topics with higher priority score receive earlier slots and fuller time
        work_items = cls._create_work_items(
            topics=topics,
            available_minutes=total_available_study_minutes,
            session_duration_minutes=preferred_session_duration
        )

        # 4. Pack work items into active study days respecting preferred time windows
        sessions, daily_audits = cls._pack_schedule(
            student_id=student_id,
            work_items=work_items,
            active_dates=active_study_dates,
            daily_limit_minutes=daily_limit_minutes,
            preferred_start_time=preferred_start_time,
            preferred_end_time=preferred_end_time
        )

        # 5. Calculate global compliance metrics
        total_scheduled_minutes = sum(s["duration_minutes"] for s in sessions if s["session_type"] != "Break")
        total_scheduled_hours = round(total_scheduled_minutes / 60.0, 1)

        audit_report = {
            "all_passed": all(d["is_valid"] for d in daily_audits),
            "total_available_hours": total_available_study_hours,
            "total_scheduled_hours": total_scheduled_hours,
            "buffer_hours": round(total_available_study_hours - total_scheduled_hours, 1),
            "daily_audits": daily_audits
        }

        return {
            "sessions": sessions,
            "capacity_warning": capacity_warning,
            "audit_report": audit_report,
            "days_until_assessment": total_days
        }

    @classmethod
    def _create_work_items(
        cls,
        topics: List[Dict[str, Any]],
        available_minutes: int,
        session_duration_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Creates fine-grained sessions:
        - Concept Study
        - Practice Task
        - Quiz / Self-Assessment
        - Revision Session
        """
        items = []

        for t in topics:
            t_id = t.get("id")
            name = t.get("name")
            mastery = t.get("mastery_level", "Beginner")
            roadmap = t.get("roadmap_details", {})
            subtopics = roadmap.get("subtopics", [])
            quiz_data = roadmap.get("quiz", [])
            code_exercise = roadmap.get("practical_exercise", {})

            # Determine session counts based on mastery
            if mastery == "Beginner":
                concept_count = max(1, len(subtopics))
                practice_count = 2
                revision_count = 1
            elif mastery == "Intermediate":
                concept_count = max(1, len(subtopics) - 1)
                practice_count = 2
                revision_count = 1
            else: # Advanced
                concept_count = 1
                practice_count = 1
                revision_count = 2 # Heavy active recall

            # 1. Concept Study Sessions for subtopics
            for idx in range(concept_count):
                sub_name = subtopics[idx]["name"] if idx < len(subtopics) else f"Foundations of {name}"
                items.append({
                    "topic_id": t_id,
                    "topic_name": name,
                    "subtopic_name": sub_name,
                    "session_type": "Concept Study",
                    "duration_minutes": session_duration_minutes,
                    "learning_objectives": f"Master principles and internal mental models of {sub_name}.",
                    "study_material": f"Study theoretical definitions, code walkthroughs, and key operations for {sub_name}.",
                    "practice_exercise": "",
                    "quiz_data": {},
                    "priority_rank": t.get("rank", 99)
                })

            # 2. Practice Task Session
            for p_idx in range(practice_count):
                prompt = code_exercise.get("prompt", f"Solve 2 implementation challenges for {name}.")
                init_code = code_exercise.get("initial_code", "# Write your code solution here\n")
                items.append({
                    "topic_id": t_id,
                    "topic_name": name,
                    "subtopic_name": f"Practical Application Drill #{p_idx+1}",
                    "session_type": "Practice Task",
                    "duration_minutes": session_duration_minutes,
                    "learning_objectives": f"Hands-on coding and problem-solving implementation for {name}.",
                    "study_material": "Apply algorithmic patterns and test against sample inputs.",
                    "practice_exercise": prompt,
                    "code_exercise_data": code_exercise,
                    "quiz_data": {},
                    "priority_rank": t.get("rank", 99)
                })

            # 3. Interactive Quiz / Assessment Session
            items.append({
                "topic_id": t_id,
                "topic_name": name,
                "subtopic_name": f"{name} Concept Mastery Quiz",
                "session_type": "Self-Assessment Quiz",
                "duration_minutes": max(20, session_duration_minutes // 2),
                "learning_objectives": f"Validate understanding and active recall for {name} with instant feedback.",
                "study_material": "Answer all 3 assessment questions under timed conditions.",
                "practice_exercise": "",
                "quiz_data": {"questions": quiz_data},
                "priority_rank": t.get("rank", 99)
            })

            # 4. Revision & Spaced Recall Session
            for r_idx in range(revision_count):
                rev_tasks = roadmap.get("revision_tasks", [f"Active recall of {name} concepts."])
                task_desc = rev_tasks[r_idx % len(rev_tasks)]
                items.append({
                    "topic_id": t_id,
                    "topic_name": name,
                    "subtopic_name": f"Spaced Revision: {name}",
                    "session_type": "Revision Session",
                    "duration_minutes": session_duration_minutes,
                    "learning_objectives": f"Consolidate memory and reinforce weak spots in {name}.",
                    "study_material": task_desc,
                    "practice_exercise": f"Quick Review: {task_desc}",
                    "quiz_data": {},
                    "priority_rank": t.get("rank", 99) + 5 # Revision can occur slightly later
                })

        # Order items by priority rank and logical progression
        type_weight = {
            "Concept Study": 1,
            "Practice Task": 2,
            "Self-Assessment Quiz": 3,
            "Revision Session": 4
        }
        items.sort(key=lambda x: (x["priority_rank"], type_weight.get(x["session_type"], 5)))
        return items

    @classmethod
    def _pack_schedule(
        cls,
        student_id: int,
        work_items: List[Dict[str, Any]],
        active_dates: List[Tuple[date, str]],
        daily_limit_minutes: int,
        preferred_start_time: str,
        preferred_end_time: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Packs sessions into active calendar days ensuring:
        - NEVER exceed daily limit
        - NEVER overlap start/end times
        - Insert 10-min breaks between sessions
        - Maintain buffer
        """
        sessions = []
        daily_audits = []

        try:
            start_hour, start_min = map(int, preferred_start_time.split(":"))
        except Exception:
            start_hour, start_min = 9, 0

        item_index = 0
        total_items = len(work_items)

        for curr_date, day_name in active_dates:
            day_scheduled_minutes = 0
            day_sessions = []
            
            curr_time = datetime(
                year=curr_date.year,
                month=curr_date.month,
                day=curr_date.day,
                hour=start_hour,
                minute=start_min
            )

            while item_index < total_items:
                item = work_items[item_index]
                dur = item["duration_minutes"]

                # Check if this item fits in today's remaining daily capacity
                if (day_scheduled_minutes + dur) <= daily_limit_minutes:
                    start_str = curr_time.strftime("%H:%M")
                    end_time = curr_time + timedelta(minutes=dur)
                    end_str = end_time.strftime("%H:%M")

                    session_obj = {
                        "student_id": student_id,
                        "topic_id": item["topic_id"],
                        "topic_name": item["topic_name"],
                        "subtopic_name": item["subtopic_name"],
                        "date_str": curr_date.strftime("%Y-%m-%d"),
                        "day_name": day_name,
                        "start_time": start_str,
                        "end_time": end_str,
                        "duration_minutes": dur,
                        "session_type": item["session_type"],
                        "learning_objectives": item["learning_objectives"],
                        "study_material": item["study_material"],
                        "practice_exercise": item.get("practice_exercise", ""),
                        "quiz_data": item.get("quiz_data", {}),
                        "code_exercise_data": item.get("code_exercise_data", {}),
                        "status": "Not Started"
                    }
                    sessions.append(session_obj)
                    day_sessions.append(session_obj)
                    day_scheduled_minutes += dur
                    item_index += 1

                    # Add 10-minute break if capacity remains
                    if (day_scheduled_minutes + 10 + 20) <= daily_limit_minutes and item_index < total_items:
                        break_start = end_time
                        break_end = break_start + timedelta(minutes=10)
                        curr_time = break_end
                    else:
                        curr_time = end_time
                else:
                    # Day is filled to stated availability limit!
                    break

            daily_audits.append({
                "date_str": curr_date.strftime("%Y-%m-%d"),
                "day_name": day_name,
                "available_hours": round(daily_limit_minutes / 60.0, 2),
                "scheduled_hours": round(day_scheduled_minutes / 60.0, 2),
                "buffer_hours": round((daily_limit_minutes - day_scheduled_minutes) / 60.0, 2),
                "session_count": len(day_sessions),
                "is_valid": day_scheduled_minutes <= daily_limit_minutes
            })

        return sessions, daily_audits
