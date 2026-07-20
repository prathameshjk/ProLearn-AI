from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sessions = relationship("TestSession", back_populates="user")
    custom_tests = relationship("CustomTest", back_populates="creator")
    custom_test_sessions = relationship("CustomTestSession", back_populates="user")

class Question(Base):
    __tablename__ =                          "questions"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, index=True) # AI, Data Science, etc.
    topic = Column(String) # Specific topic within domain
    question_text = Column(Text)
    option_a = Column(String)
    option_b = Column(String)
    option_c = Column(String)
    option_d = Column(String)
    correct_option = Column(String) # A, B, C, D

class TestSession(Base):
    __tablename__ = "test_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    domain = Column(String)
    score = Column(Integer)
    total_questions = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    answers = relationship("UserAnswer", back_populates="session")

class UserAnswer(Base):
    __tablename__ = "user_answers"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("test_sessions.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    selected_option = Column(String)
    is_correct = Column(Integer) # 1 for True, 0 for False

    session = relationship("TestSession", back_populates="answers")

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    video_url = Column(String)
    course_url = Column(String)
    pdf_url = Column(String)
    notes = Column(Text)

class CustomTest(Base):
    __tablename__ = "custom_tests"
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    access_code = Column(String, unique=True, index=True)  # Unique code to access the test
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    creator = relationship("User", back_populates="custom_tests")
    questions = relationship("CustomQuestion", back_populates="test", cascade="all, delete-orphan")
    test_sessions = relationship("CustomTestSession", back_populates="test", cascade="all, delete-orphan")

class CustomQuestion(Base):
    __tablename__ = "custom_questions"
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("custom_tests.id"))
    question_text = Column(Text)
    option_a = Column(String)
    option_b = Column(String)
    option_c = Column(String)
    option_d = Column(String)
    correct_option = Column(String)  # A, B, C, D
    
    test = relationship("CustomTest", back_populates="questions")

class CustomTestSession(Base):
    __tablename__ = "custom_test_sessions"
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("custom_tests.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    student_name = Column(String, nullable=True)
    student_email = Column(String, nullable=True)
    access_code = Column(String, nullable=True)
    score = Column(Integer)
    total_questions = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    test = relationship("CustomTest", back_populates="test_sessions")
    user = relationship("User", back_populates="custom_test_sessions")
    answers = relationship("CustomTestAnswer", back_populates="session", cascade="all, delete-orphan")

class CustomTestAnswer(Base):
    __tablename__ = "custom_test_answers"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("custom_test_sessions.id"))
    question_id = Column(Integer, ForeignKey("custom_questions.id"))
    selected_option = Column(String)
    is_correct = Column(Integer)  # 1 for True, 0 for False
    
    session = relationship("CustomTestSession", back_populates="answers")

class TopicVerification(Base):
    __tablename__ = "topic_verifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic = Column(String, index=True)
    score = Column(Integer)  # out of 100
    feedback = Column(Text)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User")
