"""
Database models and connection setup for SmartStudy AI.
Supports SQLite (default out-of-the-box) and MySQL via DATABASE_URL environment variable.
"""

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smartstudy.db")

# SQLite needs connect_args for multithreading
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    assessment_name = Column(String(150), nullable=False)
    subject_name = Column(String(150), nullable=False)
    daily_available_hours = Column(Float, default=2.0)
    preferred_start_time = Column(String(10), default="09:00")
    preferred_end_time = Column(String(10), default="21:00")
    assessment_date = Column(String(20), nullable=False)
    preferred_session_duration = Column(Integer, default=45) # minutes
    available_days = Column(JSON, default=list) # e.g. ["Monday", "Tuesday", ...]
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    topics = relationship("TopicModel", back_populates="student", cascade="all, delete-orphan")
    sessions = relationship("StudySessionModel", back_populates="student", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttemptModel", back_populates="student", cascade="all, delete-orphan")


class TopicModel(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    name = Column(String(150), nullable=False)
    mastery_level = Column(String(30), default="Beginner") # Beginner, Intermediate, Advanced
    importance = Column(String(30), default="Medium")      # Low, Medium, High
    estimated_hours = Column(Float, default=4.0)
    priority_score = Column(Float, default=5.0)
    priority_rationale = Column(Text, default="")
    status = Column(String(30), default="Pending") # Pending, In Progress, Completed, Needs Revision
    
    # AI-Generated Roadmap Details stored as JSON
    roadmap_details = Column(JSON, default=dict)
    
    student = relationship("Student", back_populates="topics")
    sessions = relationship("StudySessionModel", back_populates="topic", cascade="all, delete-orphan")


class StudySessionModel(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    topic_name = Column(String(150), nullable=False)
    subtopic_name = Column(String(200), default="")
    date_str = Column(String(20), nullable=False) # YYYY-MM-DD
    day_name = Column(String(20), nullable=False)
    start_time = Column(String(10), nullable=False) # HH:MM
    end_time = Column(String(10), nullable=False)   # HH:MM
    duration_minutes = Column(Integer, default=45)
    session_type = Column(String(50), default="Concept Study") # Concept Study, Practice Task, Quiz, Revision, Break
    learning_objectives = Column(Text, default="")
    study_material = Column(Text, default="")
    practice_exercise = Column(Text, default="")
    quiz_data = Column(JSON, default=dict)
    
    # Task completion & accountability
    status = Column(String(30), default="Not Started") # Not Started, In Progress, Completed, Needs Revision
    student_notes = Column(Text, default="")
    time_spent_seconds = Column(Integer, default=0)
    code_submission = Column(Text, default="")
    code_test_result = Column(JSON, default=dict)
    quiz_score = Column(Float, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    student = relationship("Student", back_populates="sessions")
    topic = relationship("TopicModel", back_populates="sessions")


class QuizAttemptModel(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    topic_name = Column(String(150), nullable=False)
    session_id = Column(Integer, nullable=True)
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    score_percentage = Column(Float, default=0.0)
    passed = Column(Boolean, default=False)
    submitted_answers = Column(JSON, default=dict)
    attempted_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="quiz_attempts")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
