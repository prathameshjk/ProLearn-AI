from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    class Config:
        orm_mode = True

class QuestionResponse(BaseModel):
    id: int
    domain: str
    topic: str
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    class Config:
        orm_mode = True

class TestSubmit(BaseModel):
    domain: str
    answers: List[dict] # [{"question_id": 1, "selected_option": "A"}, ...]
    total_questions: int

class TestAnalysis(BaseModel):
    score: int
    total: int
    weak_topics: List[str]
    recommendations: List[dict]

# Custom Test Schemas
class CustomQuestionCreate(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str  # A, B, C, D

class CustomQuestionResponse(CustomQuestionCreate):
    id: int
    class Config:
        orm_mode = True

class CustomTestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    questions: List[CustomQuestionCreate]

class CustomTestResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    access_code: str
    creator_id: int
    created_at: datetime
    questions: List[CustomQuestionResponse]
    class Config:
        orm_mode = True

class CustomTestPublic(BaseModel):
    id: int
    title: str
    description: Optional[str]
    access_code: str
    created_at: datetime
    creator_id: int
    total_questions: int
    class Config:
        orm_mode = True

class CustomTestSubmit(BaseModel):
    test_id: int
    student_name: str
    student_email: EmailStr
    access_code: str
    answers: List[dict]  # [{"question_id": 1, "selected_option": "A"}, ...]

class CustomTestResultResponse(BaseModel):
    session_id: int
    score: int
    total: int
    percentage: float
    created_at: datetime

class VerificationGenerateRequest(BaseModel):
    topic: str

class VerificationSubmitRequest(BaseModel):
    topic: str
    questions: List[str]
    answers: List[str]

class VerificationResponse(BaseModel):
    score: int
    feedback: str
    verified: bool
