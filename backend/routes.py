"""
RESTful API routes for SmartStudy AI.
Handles onboarding, roadmap generation, scheduling, interactive task execution,
quizzes, code grading, dynamic re-planning, and dashboard analytics.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db, Student, TopicModel, StudySessionModel, QuizAttemptModel
from backend.ai_engine import AIEngine
from backend.prioritizer import TopicPrioritizer
from backend.scheduler import ScheduleGenerator
from backend.evaluators import QuizEvaluator, CodeEvaluator
from backend.sample_profiles import get_sample_profiles

router = APIRouter(prefix="/api")


# Pydantic Schemas
class StudentCreateSchema(BaseModel):
    name: str
    assessment_name: str
    subject_name: str
    daily_available_hours: float = 2.0
    preferred_start_time: str = "09:00"
    preferred_end_time: str = "21:00"
    assessment_date: str
    preferred_session_duration: int = 45
    available_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    topics: List[Dict[str, Any]] = []


class TopicInputSchema(BaseModel):
    name: str
    mastery_level: str = "Beginner"
    importance: str = "High"
    estimated_hours: Optional[float] = None


class QuizSubmissionSchema(BaseModel):
    submitted_answers: Dict[str, Any]


class CodeSubmissionSchema(BaseModel):
    code: str


class TaskCompletionSchema(BaseModel):
    notes: Optional[str] = ""
    time_spent_seconds: Optional[int] = 0


@router.get("/health")
def health_check():
    return {"status": "ok", "app": "SmartStudy AI Personalised Study Planner"}


@router.get("/sample-profiles")
def list_sample_profiles():
    return {"profiles": get_sample_profiles()}


@router.post("/sample-profiles/{profile_id}/load")
def load_sample_profile(profile_id: str, db: Session = Depends(get_db)):
    """Loads one of the 3 demonstration profiles into the active database."""
    profiles = get_sample_profiles()
    if profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Sample profile not found")

    p = profiles[profile_id]

    # Create student
    student = Student(
        name=p["name"],
        assessment_name=p["assessment_name"],
        subject_name=p["subject_name"],
        daily_available_hours=p["daily_available_hours"],
        preferred_start_time=p["preferred_start_time"],
        preferred_end_time=p["preferred_end_time"],
        assessment_date=p["assessment_date"],
        preferred_session_duration=p["preferred_session_duration"],
        available_days=p["available_days"]
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    # Add topics and generate roadmaps
    topic_objs = []
    for t in p["topics"]:
        roadmap = AIEngine.generate_topic_roadmap(
            subject=student.subject_name,
            topic_name=t["name"],
            mastery=t["mastery_level"],
            importance=t["importance"]
        )
        tm = TopicModel(
            student_id=student.id,
            name=t["name"],
            mastery_level=t["mastery_level"],
            importance=t["importance"],
            estimated_hours=roadmap.get("estimated_hours", t.get("estimated_hours", 3.5)),
            roadmap_details=roadmap,
            status="Pending"
        )
        db.add(tm)
        db.commit()
        db.refresh(tm)
        topic_objs.append({
            "id": tm.id,
            "name": tm.name,
            "mastery_level": tm.mastery_level,
            "importance": tm.importance,
            "estimated_hours": tm.estimated_hours,
            "roadmap_details": tm.roadmap_details,
            "status": tm.status
        })

    # Prioritize topics
    prioritized = TopicPrioritizer.prioritize_topics(
        topics=topic_objs,
        assessment_date_str=student.assessment_date,
        current_date=date.today()
    )

    # Update priorities in DB
    for p_item in prioritized:
        db_topic = db.query(TopicModel).filter(TopicModel.id == p_item["id"]).first()
        if db_topic:
            db_topic.priority_score = p_item["priority_score"]
            db_topic.priority_rationale = p_item["priority_rationale"]
    db.commit()

    # Generate schedule
    sched_result = ScheduleGenerator.generate_schedule(
        student_id=student.id,
        topics=prioritized,
        daily_available_hours=student.daily_available_hours,
        preferred_start_time=student.preferred_start_time,
        preferred_end_time=student.preferred_end_time,
        assessment_date_str=student.assessment_date,
        preferred_session_duration=student.preferred_session_duration,
        available_days=student.available_days,
        start_date=date.today()
    )

    # Persist sessions
    for s in sched_result["sessions"]:
        sm = StudySessionModel(
            student_id=student.id,
            topic_id=s["topic_id"],
            topic_name=s["topic_name"],
            subtopic_name=s["subtopic_name"],
            date_str=s["date_str"],
            day_name=s["day_name"],
            start_time=s["start_time"],
            end_time=s["end_time"],
            duration_minutes=s["duration_minutes"],
            session_type=s["session_type"],
            learning_objectives=s["learning_objectives"],
            study_material=s["study_material"],
            practice_exercise=s.get("practice_exercise", ""),
            quiz_data=s.get("quiz_data", {}),
            status="Not Started"
        )
        db.add(sm)
    db.commit()

    return {
        "student_id": student.id,
        "message": f"Successfully loaded sample profile: {student.name}",
        "profile": p,
        "capacity_warning": sched_result["capacity_warning"],
        "audit_report": sched_result["audit_report"]
    }


@router.post("/students")
def create_student_onboarding(data: StudentCreateSchema, db: Session = Depends(get_db)):
    """Creates a new student profile and custom topics entered by user."""
    student = Student(
        name=data.name,
        assessment_name=data.assessment_name,
        subject_name=data.subject_name,
        daily_available_hours=data.daily_available_hours,
        preferred_start_time=data.preferred_start_time,
        preferred_end_time=data.preferred_end_time,
        assessment_date=data.assessment_date,
        preferred_session_duration=data.preferred_session_duration,
        available_days=data.available_days
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    # Add custom topics
    topic_dicts = []
    for t_data in data.topics:
        t_name = t_data.get("name", "").strip()
        if not t_name:
            continue
        mastery = t_data.get("mastery_level", "Beginner")
        importance = t_data.get("importance", "High")

        roadmap = AIEngine.generate_topic_roadmap(
            subject=student.subject_name,
            topic_name=t_name,
            mastery=mastery,
            importance=importance
        )
        tm = TopicModel(
            student_id=student.id,
            name=t_name,
            mastery_level=mastery,
            importance=importance,
            estimated_hours=roadmap.get("estimated_hours", 4.0),
            roadmap_details=roadmap,
            status="Pending"
        )
        db.add(tm)
        db.commit()
        db.refresh(tm)
        topic_dicts.append({
            "id": tm.id,
            "name": tm.name,
            "mastery_level": tm.mastery_level,
            "importance": tm.importance,
            "estimated_hours": tm.estimated_hours,
            "roadmap_details": tm.roadmap_details,
            "status": tm.status
        })

    # Prioritize and schedule
    prioritized = TopicPrioritizer.prioritize_topics(
        topics=topic_dicts,
        assessment_date_str=student.assessment_date,
        current_date=date.today()
    )
    for p_item in prioritized:
        db_topic = db.query(TopicModel).filter(TopicModel.id == p_item["id"]).first()
        if db_topic:
            db_topic.priority_score = p_item["priority_score"]
            db_topic.priority_rationale = p_item["priority_rationale"]
    db.commit()

    sched_result = ScheduleGenerator.generate_schedule(
        student_id=student.id,
        topics=prioritized,
        daily_available_hours=student.daily_available_hours,
        preferred_start_time=student.preferred_start_time,
        preferred_end_time=student.preferred_end_time,
        assessment_date_str=student.assessment_date,
        preferred_session_duration=student.preferred_session_duration,
        available_days=student.available_days,
        start_date=date.today()
    )

    for s in sched_result["sessions"]:
        sm = StudySessionModel(
            student_id=student.id,
            topic_id=s["topic_id"],
            topic_name=s["topic_name"],
            subtopic_name=s["subtopic_name"],
            date_str=s["date_str"],
            day_name=s["day_name"],
            start_time=s["start_time"],
            end_time=s["end_time"],
            duration_minutes=s["duration_minutes"],
            session_type=s["session_type"],
            learning_objectives=s["learning_objectives"],
            study_material=s["study_material"],
            practice_exercise=s.get("practice_exercise", ""),
            quiz_data=s.get("quiz_data", {}),
            status="Not Started"
        )
        db.add(sm)
    db.commit()

    return {
        "student_id": student.id,
        "message": "Student created and initial plan generated",
        "capacity_warning": sched_result["capacity_warning"],
        "audit_report": sched_result["audit_report"]
    }


@router.get("/students/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    topics = db.query(TopicModel).filter(TopicModel.student_id == student_id).all()
    return {
        "id": student.id,
        "name": student.name,
        "assessment_name": student.assessment_name,
        "subject_name": student.subject_name,
        "daily_available_hours": student.daily_available_hours,
        "preferred_start_time": student.preferred_start_time,
        "preferred_end_time": student.preferred_end_time,
        "assessment_date": student.assessment_date,
        "preferred_session_duration": student.preferred_session_duration,
        "available_days": student.available_days,
        "topics": [
            {
                "id": t.id,
                "name": t.name,
                "mastery_level": t.mastery_level,
                "importance": t.importance,
                "estimated_hours": t.estimated_hours,
                "priority_score": t.priority_score,
                "priority_rationale": t.priority_rationale,
                "status": t.status,
                "roadmap_details": t.roadmap_details
            }
            for t in topics
        ]
    }


@router.post("/students/{student_id}/topics")
def add_topic(student_id: int, topic_in: TopicInputSchema, db: Session = Depends(get_db)):
    """Allows student to enter an additional topic manually."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    roadmap = AIEngine.generate_topic_roadmap(
        subject=student.subject_name,
        topic_name=topic_in.name,
        mastery=topic_in.mastery_level,
        importance=topic_in.importance
    )
    tm = TopicModel(
        student_id=student.id,
        name=topic_in.name,
        mastery_level=topic_in.mastery_level,
        importance=topic_in.importance,
        estimated_hours=topic_in.estimated_hours or roadmap.get("estimated_hours", 4.0),
        roadmap_details=roadmap,
        status="Pending"
    )
    db.add(tm)
    db.commit()
    db.refresh(tm)

    return {"message": "Topic added successfully", "topic_id": tm.id}


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(TopicModel).filter(TopicModel.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    db.delete(topic)
    db.commit()
    return {"message": "Topic deleted"}


@router.get("/students/{student_id}/schedule")
def get_schedule(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    sessions = db.query(StudySessionModel).filter(
        StudySessionModel.student_id == student_id
    ).order_by(StudySessionModel.date_str, StudySessionModel.start_time).all()

    # Group by date
    days_dict = {}
    for s in sessions:
        if s.date_str not in days_dict:
            days_dict[s.date_str] = {
                "date_str": s.date_str,
                "day_name": s.day_name,
                "sessions": []
            }
        days_dict[s.date_str]["sessions"].append({
            "id": s.id,
            "topic_id": s.topic_id,
            "topic_name": s.topic_name,
            "subtopic_name": s.subtopic_name,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "duration_minutes": s.duration_minutes,
            "session_type": s.session_type,
            "learning_objectives": s.learning_objectives,
            "study_material": s.study_material,
            "practice_exercise": s.practice_exercise,
            "quiz_data": s.quiz_data,
            "status": s.status,
            "quiz_score": s.quiz_score,
            "student_notes": s.student_notes
        })

    return {
        "student_id": student_id,
        "assessment_date": student.assessment_date,
        "daily_available_hours": student.daily_available_hours,
        "days": list(days_dict.values())
    }


@router.get("/students/{student_id}/checklist/today")
def get_today_checklist(student_id: int, db: Session = Depends(get_db)):
    today_str = date.today().strftime("%Y-%m-%d")
    sessions = db.query(StudySessionModel).filter(
        StudySessionModel.student_id == student_id,
        StudySessionModel.date_str == today_str
    ).order_by(StudySessionModel.start_time).all()

    # If no sessions on today's exact date, fetch the earliest pending date
    if not sessions:
        earliest_pending = db.query(StudySessionModel).filter(
            StudySessionModel.student_id == student_id,
            StudySessionModel.status != "Completed"
        ).order_by(StudySessionModel.date_str, StudySessionModel.start_time).first()
        if earliest_pending:
            today_str = earliest_pending.date_str
            sessions = db.query(StudySessionModel).filter(
                StudySessionModel.student_id == student_id,
                StudySessionModel.date_str == today_str
            ).order_by(StudySessionModel.start_time).all()

    return {
        "date_str": today_str,
        "tasks": [
            {
                "id": s.id,
                "topic_name": s.topic_name,
                "subtopic_name": s.subtopic_name,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration_minutes": s.duration_minutes,
                "session_type": s.session_type,
                "status": s.status,
                "learning_objectives": s.learning_objectives,
                "study_material": s.study_material,
                "practice_exercise": s.practice_exercise,
                "quiz_data": s.quiz_data,
                "quiz_score": s.quiz_score
            }
            for s in sessions
        ]
    }


@router.post("/sessions/{session_id}/start")
def start_session_task(session_id: int, db: Session = Depends(get_db)):
    session = db.query(StudySessionModel).filter(StudySessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "Not Started":
        session.status = "In Progress"
        db.commit()

    return {
        "session_id": session.id,
        "status": session.status,
        "topic_name": session.topic_name,
        "subtopic_name": session.subtopic_name,
        "session_type": session.session_type,
        "duration_minutes": session.duration_minutes,
        "study_material": session.study_material,
        "practice_exercise": session.practice_exercise,
        "quiz_data": session.quiz_data
    }


@router.post("/sessions/{session_id}/complete")
def complete_session_task(session_id: int, payload: TaskCompletionSchema, db: Session = Depends(get_db)):
    session = db.query(StudySessionModel).filter(StudySessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "Completed"
    session.student_notes = payload.notes
    session.time_spent_seconds = payload.time_spent_seconds or (session.duration_minutes * 60)
    session.completed_at = datetime.utcnow()
    db.commit()

    return {"message": "Task marked as completed", "session_id": session.id, "status": session.status}


@router.post("/sessions/{session_id}/quiz/submit")
def submit_quiz_attempt(session_id: int, submission: QuizSubmissionSchema, db: Session = Depends(get_db)):
    session = db.query(StudySessionModel).filter(StudySessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    questions = session.quiz_data.get("questions", [])
    if not questions and session.topic_id:
        topic = db.query(TopicModel).filter(TopicModel.id == session.topic_id).first()
        if topic and topic.roadmap_details:
            questions = topic.roadmap_details.get("quiz", [])

    grade_result = QuizEvaluator.grade_quiz(questions, submission.submitted_answers)

    session.quiz_score = grade_result["score_percentage"]
    if grade_result["passed"]:
        session.status = "Completed"
        session.completed_at = datetime.utcnow()
    else:
        # Mark as Needs Revision if score < 70%
        session.status = "Needs Revision"
        if session.topic_id:
            topic = db.query(TopicModel).filter(TopicModel.id == session.topic_id).first()
            if topic:
                topic.status = "Needs Revision"

    # Record Quiz Attempt
    attempt = QuizAttemptModel(
        student_id=session.student_id,
        topic_name=session.topic_name,
        session_id=session.id,
        total_questions=grade_result["total_questions"],
        correct_answers=grade_result["correct_answers"],
        score_percentage=grade_result["score_percentage"],
        passed=grade_result["passed"],
        submitted_answers=submission.submitted_answers
    )
    db.add(attempt)
    db.commit()

    return {
        "grade_result": grade_result,
        "session_status": session.status,
        "quiz_score": session.quiz_score
    }


@router.post("/sessions/{session_id}/code/submit")
def submit_code_solution(session_id: int, payload: CodeSubmissionSchema, db: Session = Depends(get_db)):
    session = db.query(StudySessionModel).filter(StudySessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get test cases from topic roadmap
    test_cases = []
    if session.topic_id:
        topic = db.query(TopicModel).filter(TopicModel.id == session.topic_id).first()
        if topic and topic.roadmap_details:
            prac = topic.roadmap_details.get("practical_exercise", {})
            test_cases = prac.get("test_cases", [])

    eval_result = CodeEvaluator.evaluate_code(payload.code, test_cases)
    session.code_submission = payload.code
    session.code_test_result = eval_result
    if eval_result["all_passed"]:
        session.status = "Completed"
        session.completed_at = datetime.utcnow()
    db.commit()

    return {"eval_result": eval_result, "session_status": session.status}


@router.post("/students/{student_id}/reschedule")
def dynamic_reschedule(student_id: int, db: Session = Depends(get_db)):
    """
    Dynamic Rescheduling & Plan Regeneration:
    1. Preserves completed tasks (never erases them).
    2. Identifies incomplete, overdue, or Needs Revision tasks.
    3. Re-evaluates topic priorities with latest quiz performance.
    4. Packs remaining tasks into future available days without exceeding availability.
    5. Returns explainable change report.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # 1. Fetch completed tasks
    completed_sessions = db.query(StudySessionModel).filter(
        StudySessionModel.student_id == student_id,
        StudySessionModel.status == "Completed"
    ).all()
    completed_ids = {s.id for s in completed_sessions}

    # 2. Fetch topics and average quiz scores
    topics = db.query(TopicModel).filter(TopicModel.student_id == student_id).all()
    topic_dicts = []
    for t in topics:
        # Check quiz score from attempts
        latest_attempt = db.query(QuizAttemptModel).filter(
            QuizAttemptModel.student_id == student_id,
            QuizAttemptModel.topic_name == t.name
        ).order_by(QuizAttemptModel.attempted_at.desc()).first()

        quiz_score = latest_attempt.score_percentage if latest_attempt else None

        topic_dicts.append({
            "id": t.id,
            "name": t.name,
            "mastery_level": t.mastery_level,
            "importance": t.importance,
            "estimated_hours": t.estimated_hours,
            "quiz_score": quiz_score,
            "status": t.status,
            "roadmap_details": t.roadmap_details
        })

    # 3. Recalculate Priorities
    prioritized = TopicPrioritizer.prioritize_topics(
        topics=topic_dicts,
        assessment_date_str=student.assessment_date,
        current_date=date.today()
    )

    for p_item in prioritized:
        db_topic = db.query(TopicModel).filter(TopicModel.id == p_item["id"]).first()
        if db_topic:
            db_topic.priority_score = p_item["priority_score"]
            db_topic.priority_rationale = p_item["priority_rationale"]
    db.commit()

    # 4. Remove incomplete future sessions to replace with regenerated schedule
    db.query(StudySessionModel).filter(
        StudySessionModel.student_id == student_id,
        StudySessionModel.status != "Completed"
    ).delete()
    db.commit()

    # 5. Generate new schedule for remaining days
    sched_result = ScheduleGenerator.generate_schedule(
        student_id=student.id,
        topics=prioritized,
        daily_available_hours=student.daily_available_hours,
        preferred_start_time=student.preferred_start_time,
        preferred_end_time=student.preferred_end_time,
        assessment_date_str=student.assessment_date,
        preferred_session_duration=student.preferred_session_duration,
        available_days=student.available_days,
        start_date=date.today()
    )

    # 6. Save new sessions
    for s in sched_result["sessions"]:
        sm = StudySessionModel(
            student_id=student.id,
            topic_id=s["topic_id"],
            topic_name=s["topic_name"],
            subtopic_name=s["subtopic_name"],
            date_str=s["date_str"],
            day_name=s["day_name"],
            start_time=s["start_time"],
            end_time=s["end_time"],
            duration_minutes=s["duration_minutes"],
            session_type=s["session_type"],
            learning_objectives=s["learning_objectives"],
            study_material=s["study_material"],
            practice_exercise=s.get("practice_exercise", ""),
            quiz_data=s.get("quiz_data", {}),
            status="Not Started"
        )
        db.add(sm)
    db.commit()

    # 7. Generate explanation of changes
    delta_explanation = (
        f"Schedule successfully regenerated! Preserved {len(completed_sessions)} completed study tasks. "
        f"Recalculated priorities based on remaining {sched_result['days_until_assessment']} days to assessment. "
        f"Top focus topic is now: {prioritized[0]['name']} (Score: {prioritized[0]['priority_score']}/10). "
        f"All future sessions packed strictly within {student.daily_available_hours}h daily availability."
    )

    return {
        "message": "Plan successfully regenerated",
        "explanation": delta_explanation,
        "capacity_warning": sched_result["capacity_warning"],
        "audit_report": sched_result["audit_report"],
        "preserved_completed_count": len(completed_sessions)
    }


@router.get("/students/{student_id}/dashboard")
def get_dashboard_metrics(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    topics = db.query(TopicModel).filter(TopicModel.student_id == student_id).all()
    sessions = db.query(StudySessionModel).filter(StudySessionModel.student_id == student_id).all()
    quiz_attempts = db.query(QuizAttemptModel).filter(QuizAttemptModel.student_id == student_id).all()

    today_str = date.today().strftime("%Y-%m-%d")

    total_tasks = len(sessions)
    completed_tasks = sum(1 for s in sessions if s.status == "Completed")
    today_completed = sum(1 for s in sessions if s.status == "Completed" and s.date_str == today_str)
    pending_tasks = sum(1 for s in sessions if s.status == "Not Started" or s.status == "In Progress")
    overdue_tasks = sum(1 for s in sessions if s.date_str < today_str and s.status != "Completed")
    needs_revision_count = sum(1 for s in sessions if s.status == "Needs Revision") + sum(1 for t in topics if t.status == "Needs Revision")

    total_scheduled_minutes = sum(s.duration_minutes for s in sessions)
    completed_minutes = sum(s.duration_minutes for s in sessions if s.status == "Completed")
    remaining_hours = round(max(0.0, (total_scheduled_minutes - completed_minutes) / 60.0), 1)
    total_hours = round(total_scheduled_minutes / 60.0, 1)

    overall_progress_pct = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

    # Days remaining
    try:
        exam_d = datetime.strptime(student.assessment_date, "%Y-%m-%d").date()
        days_rem = max(0, (exam_d - date.today()).days)
    except Exception:
        days_rem = 7

    # Multi-factor Readiness Indicator (Completion + Quiz Accuracy + Mastery)
    avg_quiz_score = 0.0
    if quiz_attempts:
        avg_quiz_score = sum(q.score_percentage for q in quiz_attempts) / len(quiz_attempts)
    else:
        avg_quiz_score = 50.0 # neutral baseline

    mastery_scores = {"Beginner": 40.0, "Intermediate": 75.0, "Advanced": 95.0}
    avg_mastery_baseline = sum(mastery_scores.get(t.mastery_level, 50.0) for t in topics) / max(1, len(topics))

    # Readiness formula: 40% completion rate + 35% quiz accuracy + 25% mastery baseline
    readiness_score = round(
        (0.40 * overall_progress_pct) + (0.35 * avg_quiz_score) + (0.25 * avg_mastery_baseline),
        1
    )
    readiness_score = max(5.0, min(99.0, readiness_score))

    # Daily hours chart data
    daily_chart_dict = {}
    for s in sessions:
        if s.date_str not in daily_chart_dict:
            daily_chart_dict[s.date_str] = {
                "date": s.date_str,
                "scheduled_hours": 0.0,
                "completed_hours": 0.0,
                "available_hours": student.daily_available_hours
            }
        dur_h = s.duration_minutes / 60.0
        daily_chart_dict[s.date_str]["scheduled_hours"] += dur_h
        if s.status == "Completed":
            daily_chart_dict[s.date_str]["completed_hours"] += dur_h

    daily_chart_data = sorted(list(daily_chart_dict.values()), key=lambda x: x["date"])

    return {
        "student_name": student.name,
        "assessment_name": student.assessment_name,
        "subject_name": student.subject_name,
        "assessment_date": student.assessment_date,
        "days_remaining": days_rem,
        "overall_progress_pct": overall_progress_pct,
        "total_topics": len(topics),
        "topics_completed": sum(1 for t in topics if t.status == "Completed"),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "tasks_completed_today": today_completed,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
        "needs_revision_tasks": needs_revision_count,
        "total_scheduled_hours": total_hours,
        "remaining_study_hours": remaining_hours,
        "readiness_score": readiness_score,
        "readiness_disclaimer": "The readiness score is an AI estimate synthesizing task completion, quiz accuracy, and self-assessed mastery. It is not an absolute guarantee of exam performance.",
        "daily_chart_data": daily_chart_data
    }
