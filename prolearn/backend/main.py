from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from . import models, schemas, database
from .database import engine, get_db
from passlib.context import CryptContext
from typing import Optional
import datetime
import random
import os
import json
import string
import uuid
import google.generativeai as genai
import time
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="backend/.env")

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3.5-flash')
else:
    model = None


def generate_content_with_retries(prompt: str, max_retries: int = 3, initial_delay: float = 1.0):
    """Call `model.generate_content` with basic retry/backoff for rate-limit/quota errors.

    This inspects the exception message for common indicators ("quota", "429", "rate limit")
    and will sleep for the returned retry delay if present, otherwise it uses exponential backoff.
    """
    if not model:
        raise RuntimeError("Gemini model not configured")

    for attempt in range(max_retries):
        try:
            return model.generate_content(prompt)
        except Exception as e:
            msg = str(e).lower()
            # Detect rate-limit/quota errors and attempt to retry
            if "quota" in msg or "429" in msg or "rate limit" in msg:
                # Try to parse a retry delay from the message if available
                delay = None
                m = re.search(r'retry_delay.*?seconds.*?([0-9]+(?:\.[0-9]+)?)', msg)
                if m:
                    try:
                        delay = float(m.group(1))
                    except Exception:
                        delay = None

                if delay is None:
                    delay = initial_delay * (2 ** attempt)

                print(f"Gemini rate limit hit. Retrying in {delay}s (attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
                continue

            # Non-rate-limit error: re-raise
            raise

    raise Exception("Gemini requests failed after retries due to rate limiting")

def ensure_custom_test_session_columns():
    """Add student detail columns for existing local SQLite databases."""
    with engine.begin() as connection:
        existing_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(custom_test_sessions)"))
        }
        columns_to_add = {
            "student_name": "VARCHAR",
            "student_email": "VARCHAR",
            "access_code": "VARCHAR",
        }

        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE custom_test_sessions ADD COLUMN {column_name} {column_type}")
                )


models.Base.metadata.create_all(bind=engine)
ensure_custom_test_session_columns()

app = FastAPI(title="Prolearn API")

# Use bcrypt_sha256 to avoid bcrypt's 72-byte password limit while staying compatible with bcrypt hashing.
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

# Static files and templates
app.mount("/static", StaticFiles(directory="backend/static"), name="static")
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
templates = Jinja2Templates(directory="templates")

QUESTION_FILE_MAP = {
    "Artificial Intelligence": "artificial_intelligence.json",
    "Data Science": "data_science.json",
    "Cybersecurity": "cybersecurity.json",
    "Cloud Computing": "cloud_computing.json",
    "Full Stack Development": "full_stack_development.json",
    "Mobile App Development": "mobile_app_development.json",
    "Deep Learning": "deep_learning.json",
    "Natural Language Processing": "natural_language_processing.json",
}

# Auth utils
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def generate_access_code():
    """Generate a unique 6-character alphanumeric access code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def load_questions_from_file(domain: str):
    filename = QUESTION_FILE_MAP.get(domain)
    if not filename:
        return []

    data_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "questions", filename))
    if not os.path.exists(data_path):
        return []

    with open(data_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    return [models.Question(
        domain=domain,
        topic=q.get("topic", "General"),
        question_text=q["question_text"],
        option_a=q["option_a"],
        option_b=q["option_b"],
        option_c=q["option_c"],
        option_d=q["option_d"],
        correct_option=q["correct_option"],
    ) for q in questions]

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.get("/dashboard")
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")

@app.get("/test")
async def test_page(request: Request):
    return templates.TemplateResponse(request, "test.html")

@app.get("/result")
async def result_page(request: Request):
    return templates.TemplateResponse(request, "result.html")

@app.get("/profile")
async def profile_page(request: Request):
    return templates.TemplateResponse(request, "profile.html")

@app.get("/create-test")
async def create_test_page(request: Request):
    return templates.TemplateResponse(request, "create_test.html")

@app.get("/my-tests")
async def my_tests_page(request: Request):
    return templates.TemplateResponse(request, "my_tests.html")

@app.get("/take-test/{access_code}")
async def take_test_page(request: Request, access_code: str):
    return templates.TemplateResponse(request, "take_test.html", {"access_code": access_code})

@app.get("/custom-test-result")
async def custom_test_result_page(request: Request):
    return templates.TemplateResponse(request, "custom_test_result.html")

@app.get("/test-leaderboard")
async def test_leaderboard_page(request: Request):
    return templates.TemplateResponse(request, "test_leaderboard.html")

@app.get("/test-results")
async def test_results_page(request: Request):
    return templates.TemplateResponse(request, "test_results.html")

@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login")
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"message": "Login successful", "user_id": user.id, "username": user.username}

@app.get("/questions/{domain}")
def get_questions(domain: str, user_id: int, db: Session = Depends(get_db)):
    # Daily limit check
    today = datetime.datetime.utcnow().date()
    start_of_day = datetime.datetime.combine(today, datetime.time.min)
    
    test_count = db.query(models.TestSession).filter(
        models.TestSession.user_id == user_id,
        models.TestSession.created_at >= start_of_day
    ).count()
    
    if test_count >= 1:
        raise HTTPException(status_code=403, detail="Daily test limit reached (1 per day)")
        
    # Attempt to use Gemini if configured
    if model:
        prompt = f"""
        Generate exactly 20 multiple-choice questions for the domain: {domain}.
        Each question should be challenging and relevant to modern industry standards.
        
        Return the response as a JSON array of objects. Each object MUST have these keys:
        - topic: a specific sub-topic (e.g., 'Neural Networks' for AI)
        - question_text: the question text
        - option_a: option A
        - option_b: option B
        - option_c: option C
        - option_d: option D
        - correct_option: exactly one character 'A', 'B', 'C', or 'D'
        
        Provide ONLY the raw JSON array. No markdown blocks, no extra text.
        """
        try:
            response = generate_content_with_retries(prompt)
            content = response.text.strip()
            # Clean up markdown if present
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            
            generated_questions = json.loads(content)
            
            db_questions = []
            for q in generated_questions[:20]: # Ensure limit
                new_q = models.Question(
                    domain=domain,
                    topic=q.get('topic', 'General'),
                    question_text=q['question_text'],
                    option_a=q['option_a'],
                    option_b=q['option_b'],
                    option_c=q['option_c'],
                    option_d=q['option_d'],
                    correct_option=q['correct_option']
                )
                db.add(new_q)
                db_questions.append(new_q)
            
            db.commit()
            for q in db_questions:
                db.refresh(q)
            return db_questions
            
        except Exception as e:
            print(f"Gemini Error: {e}. Falling back to database.")

    # Fallback: Get questions from database with case-insensitive matching
    all_questions = db.query(models.Question).filter(func.lower(models.Question.domain) == domain.lower()).all()
    
    if not all_questions:
        local_questions = load_questions_from_file(domain)
        if local_questions:
            db.add_all(local_questions)
            db.commit()
            for q in local_questions:
                db.refresh(q)
            random.shuffle(local_questions)
            return local_questions[:20]

        raise HTTPException(status_code=404, detail="No questions found and AI generation failed.")
    
    # Shuffle and pick 20 random questions
    random.shuffle(all_questions)
    questions = all_questions[:20]
    
    return questions

@app.post("/submit_test")
def submit_test(submission: schemas.TestSubmit, user_id: int, db: Session = Depends(get_db)):
    score = 0
    total = submission.total_questions
    weak_topics = set()
    
    # Create test session
    session = models.TestSession(user_id=user_id, domain=submission.domain, score=0, total_questions=total)
    db.add(session)
    db.commit()
    db.refresh(session)
    
    answer_details = []
    for ans in submission.answers:
        question = db.query(models.Question).filter(models.Question.id == ans['question_id']).first()
        is_correct = 1 if question and question.correct_option == ans['selected_option'] else 0
        if is_correct:
            score += 1
        else:
            if question: weak_topics.add(question.topic)
            
        user_ans = models.UserAnswer(
            session_id=session.id,
            question_id=ans['question_id'],
            selected_option=ans['selected_option'],
            is_correct=is_correct
        )
        db.add(user_ans)
        
        if question:
            answer_details.append({
                "question_id": question.id,
                "question_text": question.question_text,
                "selected_option": ans['selected_option'],
                "correct_option": question.correct_option,
                "is_correct": is_correct,
                "options": {
                    "A": question.option_a,
                    "B": question.option_b,
                    "C": question.option_c,
                    "D": question.option_d
                }
            })
    
    session.score = score
    db.commit()
    
    # Fetch recommendations
    recommendations = db.query(models.Recommendation).filter(models.Recommendation.topic.in_(list(weak_topics))).all()
    
    return {
        "score": score,
        "total": total,
        "weak_topics": list(weak_topics),
        "recommendations": recommendations,
        "session_id": session.id,
        "answers": answer_details
    }

@app.get("/analysis/{session_id}")
def get_analysis(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.TestSession).filter(models.TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    answers = db.query(models.UserAnswer).filter(models.UserAnswer.session_id == session_id).all()
    
    weak_topics = set()
    for ans in answers:
        if ans.is_correct == 0:
            q = db.query(models.Question).filter(models.Question.id == ans.question_id).first()
            if q: weak_topics.add(q.topic)
            
    recommendations = db.query(models.Recommendation).filter(models.Recommendation.topic.in_(list(weak_topics))).all()
    
    return {
        "score": session.score,
        "total": session.total_questions,
        "domain": session.domain,
        "weak_topics": list(weak_topics),
        "recommendations": recommendations,
        "date": session.created_at
    }

@app.get("/api/user/stats/{user_id}")
def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    # 1. Test History
    sessions = db.query(models.TestSession).filter(models.TestSession.user_id == user_id).order_by(models.TestSession.created_at.desc()).all()
    
    # 2. Progress Data (Last 10 tests)
    progress_data = [{
        "date": s.created_at.strftime("%Y-%m-%d"),
        "score": (s.score / s.total_questions) * 100 if s.total_questions > 0 else 0
    } for s in reversed(sessions[:10])]

    # 3. Weak Topics Analysis
    all_wrong_answers = db.query(models.UserAnswer).join(models.TestSession).filter(
        models.TestSession.user_id == user_id,
        models.UserAnswer.is_correct == 0
    ).all()
    
    topic_counts = {}
    for ans in all_wrong_answers:
        q = db.query(models.Question).filter(models.Question.id == ans.question_id).first()
        if q:
            topic_counts[q.topic] = topic_counts.get(q.topic, 0) + 1
            
    sorted_weak_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    
    # 4. Domain Mastery
    domain_stats = {}
    for s in sessions:
        if s.domain not in domain_stats:
            domain_stats[s.domain] = []
        domain_stats[s.domain].append((s.score / s.total_questions) * 100 if s.total_questions > 0 else 0)
    
    domain_mastery = {domain: sum(scores)/len(scores) for domain, scores in domain_stats.items()}

    # Courses logic
    all_courses = ["Artificial Intelligence", "Cybersecurity", "Cloud Computing", "Full Stack", "Data Science", "Mobile App Dev", "Deep Learning", "NLP"]
    completed_courses = [d for d, m in domain_mastery.items() if m >= 80]
    ongoing_courses = [d for d, m in domain_mastery.items() if m < 80 and d in all_courses]
    uncompleted_courses = [c for c in all_courses if c not in completed_courses and c not in ongoing_courses]
    overall_progress = (len(completed_courses) / len(all_courses)) * 100 if all_courses else 0

    # 5. Streak calculation
    streak = 0
    if sessions:
        today = datetime.datetime.utcnow().date()
        dates = sorted(list(set([s.created_at.date() for s in sessions])), reverse=True)
        
        current_date = today
        if dates and dates[0] == today:
            for d in dates:
                if d == current_date:
                    streak += 1
                    current_date -= datetime.timedelta(days=1)
                else:
                    break
        elif dates and dates[0] == today - datetime.timedelta(days=1):
            current_date = today - datetime.timedelta(days=1)
            for d in dates:
                if d == current_date:
                    streak += 1
                    current_date -= datetime.timedelta(days=1)
                else:
                    break

    return {
        "test_history": sessions,
        "progress_data": progress_data,
        "weak_topics": [{"topic": t, "count": c} for t, c in sorted_weak_topics[:5]],
        "domain_mastery": domain_mastery,
        "streak": streak,
        "total_tests": len(sessions),
        "avg_score": sum([ (s.score/s.total_questions)*100 if s.total_questions > 0 else 0 for s in sessions])/len(sessions) if sessions else 0,
        "completed_courses": completed_courses,
        "ongoing_courses": ongoing_courses,
        "uncompleted_courses": uncompleted_courses,
        "overall_progress": overall_progress
    }

# ============= CUSTOM TEST ENDPOINTS =============

@app.post("/api/custom-tests", response_model=schemas.CustomTestResponse)
def create_custom_test(test_data: schemas.CustomTestCreate, user_id: int, db: Session = Depends(get_db)):
    """Create a custom test with questions"""
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate unique access code
    access_code = generate_access_code()
    while db.query(models.CustomTest).filter(models.CustomTest.access_code == access_code).first():
        access_code = generate_access_code()
    
    # Create test
    custom_test = models.CustomTest(
        creator_id=user_id,
        title=test_data.title,
        description=test_data.description,
        access_code=access_code
    )
    db.add(custom_test)
    db.flush()
    
    # Add questions
    for q in test_data.questions:
        custom_question = models.CustomQuestion(
            test_id=custom_test.id,
            question_text=q.question_text,
            option_a=q.option_a,
            option_b=q.option_b,
            option_c=q.option_c,
            option_d=q.option_d,
            correct_option=q.correct_option
        )
        db.add(custom_question)
    
    db.commit()
    db.refresh(custom_test)
    return custom_test

@app.get("/api/custom-tests/user/{user_id}")
def get_user_custom_tests(user_id: int, db: Session = Depends(get_db)):
    """Get all custom tests created by a user"""
    tests = db.query(models.CustomTest).filter(models.CustomTest.creator_id == user_id).order_by(models.CustomTest.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "access_code": t.access_code,
            "created_at": t.created_at,
            "total_questions": len(t.questions),
            "total_attempts": len(t.test_sessions)
        }
        for t in tests
    ]

@app.get("/api/custom-tests/manage/{test_id}")
def get_custom_test_for_edit(test_id: int, user_id: int, db: Session = Depends(get_db)):
    """Get a custom test for editing by its creator"""
    test = db.query(models.CustomTest).filter(models.CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if test.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Only the creator can edit this test")

    return {
        "id": test.id,
        "title": test.title,
        "description": test.description,
        "access_code": test.access_code,
        "creator_id": test.creator_id,
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_option": q.correct_option
            }
            for q in test.questions
        ]
    }

@app.put("/api/custom-tests/{test_id}", response_model=schemas.CustomTestResponse)
def update_custom_test(test_id: int, test_data: schemas.CustomTestCreate, user_id: int, db: Session = Depends(get_db)):
    """Update a custom test while keeping the same shared access code"""
    test = db.query(models.CustomTest).filter(models.CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if test.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Only the creator can edit this test")

    test.title = test_data.title
    test.description = test_data.description
    test.updated_at = datetime.datetime.utcnow()

    db.query(models.CustomQuestion).filter(models.CustomQuestion.test_id == test_id).delete()
    db.flush()

    for q in test_data.questions:
        db.add(models.CustomQuestion(
            test_id=test.id,
            question_text=q.question_text,
            option_a=q.option_a,
            option_b=q.option_b,
            option_c=q.option_c,
            option_d=q.option_d,
            correct_option=q.correct_option
        ))

    db.commit()
    db.refresh(test)
    return test

@app.get("/api/custom-tests/{access_code}")
def get_custom_test_by_code(access_code: str, db: Session = Depends(get_db)):
    """Get custom test by access code (for taking test)"""
    test = db.query(models.CustomTest).filter(models.CustomTest.access_code == access_code.strip().upper()).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found. Invalid access code.")
    
    return {
        "id": test.id,
        "title": test.title,
        "description": test.description,
        "access_code": test.access_code,
        "creator_id": test.creator_id,
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d
            }
            for q in test.questions
        ]
    }

@app.post("/api/custom-tests/submit")
def submit_custom_test(
    submission: schemas.CustomTestSubmit,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Submit answers to a custom test"""
    # Verify test exists
    test = db.query(models.CustomTest).filter(
        models.CustomTest.id == submission.test_id,
        models.CustomTest.access_code == submission.access_code.strip().upper()
    ).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found. Invalid access code.")
    
    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    if not submission.student_name.strip():
        raise HTTPException(status_code=400, detail="Student name is required")
    
    score = 0
    total = len(test.questions)
    
    # Create test session
    session = models.CustomTestSession(
        test_id=submission.test_id,
        user_id=user_id,
        student_name=submission.student_name.strip(),
        student_email=str(submission.student_email),
        access_code=submission.access_code.strip().upper(),
        score=0,
        total_questions=total
    )
    db.add(session)
    db.flush()
    
    # Process answers
    for ans in submission.answers:
        question = db.query(models.CustomQuestion).filter(
            models.CustomQuestion.id == ans['question_id'],
            models.CustomQuestion.test_id == test.id
        ).first()
        if question:
            is_correct = 1 if question.correct_option == ans['selected_option'] else 0
            if is_correct:
                score += 1
            
            user_ans = models.CustomTestAnswer(
                session_id=session.id,
                question_id=ans['question_id'],
                selected_option=ans['selected_option'],
                is_correct=is_correct
            )
            db.add(user_ans)
    
    session.score = score
    db.commit()
    db.refresh(session)
    
    percentage = (score / total * 100) if total > 0 else 0
    
    return {
        "session_id": session.id,
        "score": score,
        "total": total,
        "percentage": percentage,
        "student_name": session.student_name,
        "student_email": session.student_email,
        "created_at": session.created_at
    }

@app.get("/api/custom-tests/{test_id}/results")
def get_custom_test_results(test_id: int, user_id: int, db: Session = Depends(get_db)):
    """Get all student attempts and answer details for a creator's custom test"""
    test = db.query(models.CustomTest).filter(models.CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if test.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Only the test creator can view these results")

    sessions = db.query(models.CustomTestSession).filter(
        models.CustomTestSession.test_id == test_id
    ).order_by(models.CustomTestSession.created_at.desc()).all()

    attempts = []
    for session in sessions:
        saved_answers = db.query(models.CustomTestAnswer).filter(
            models.CustomTestAnswer.session_id == session.id
        ).all()
        answers_by_question_id = {answer.question_id: answer for answer in saved_answers}

        answer_details = []
        for question in test.questions:
            answer = answers_by_question_id.get(question.id)
            answer_details.append({
                "question_id": question.id,
                "question_text": question.question_text,
                "selected_option": answer.selected_option if answer else None,
                "correct_option": question.correct_option,
                "is_correct": answer.is_correct if answer else 0,
                "options": {
                    "A": question.option_a,
                    "B": question.option_b,
                    "C": question.option_c,
                    "D": question.option_d
                }
            })

        percentage = (session.score / session.total_questions * 100) if session.total_questions > 0 else 0
        attempts.append({
            "session_id": session.id,
            "student_name": session.student_name or "Student",
            "student_email": session.student_email,
            "score": session.score,
            "total": session.total_questions,
            "percentage": percentage,
            "created_at": session.created_at,
            "answers": answer_details
        })

    return {
        "test_id": test.id,
        "title": test.title,
        "access_code": test.access_code,
        "total_attempts": len(attempts),
        "attempts": attempts
    }
@app.get("/api/custom-tests/{test_id}/leaderboard")
def get_test_leaderboard(test_id: int, db: Session = Depends(get_db)):
    """Get leaderboard for a custom test"""
    sessions = db.query(models.CustomTestSession).filter(
        models.CustomTestSession.test_id == test_id
    ).order_by(models.CustomTestSession.score.desc()).limit(10).all()
    
    leaderboard = []
    for session in sessions:
        user = db.query(models.User).filter(models.User.id == session.user_id).first() if session.user_id else None
        percentage = (session.score / session.total_questions * 100) if session.total_questions > 0 else 0
        leaderboard.append({
            "username": session.student_name or (user.username if user else "Student"),
            "email": session.student_email,
            "score": session.score,
            "total": session.total_questions,
            "percentage": percentage,
            "date": session.created_at
        })
    
    return leaderboard

@app.delete("/api/custom-tests/{test_id}")
def delete_custom_test(test_id: int, user_id: int, db: Session = Depends(get_db)):
    """Delete a custom test (only by creator)"""
    test = db.query(models.CustomTest).filter(models.CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    if test.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Only the creator can delete this test")
    
    db.delete(test)
    db.commit()
    return {"message": "Test deleted successfully"}

# ============= AI TOPIC VERIFICATION =============

@app.get("/api/verify/generate-questions")
def generate_verification_questions(topic: str):
    if not model:
        raise HTTPException(status_code=503, detail="Gemini AI is not configured")
        
    prompt = f"""
    Generate exactly 1 short, simple, open-ended conceptual question to test a student's understanding of the topic: "{topic}".
    Return the response as a JSON array of strings containing only that one question.
    Provide ONLY the raw JSON array. No markdown blocks, no extra text.
    """
    try:
        response = generate_content_with_retries(prompt)
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        questions = json.loads(content)
        return {"questions": questions[:1]}
    except Exception as e:
        print(f"Gemini Error generating questions: {e}")
        # Graceful fallback: return a simple handcrafted conceptual question
        fallback = [f"In your own words, explain the core concept of '{topic}' and why it matters."]
        return {"questions": fallback}

@app.post("/api/verify/evaluate", response_model=schemas.VerificationResponse)
def evaluate_verification_answers(
    request: schemas.VerificationSubmitRequest, 
    user_id: int, 
    db: Session = Depends(get_db)
):
    if not model:
        raise HTTPException(status_code=503, detail="Gemini AI is not configured")
        
    qa_text = ""
    for q, a in zip(request.questions, request.answers):
        qa_text += f"Q: {q}\nA: {a}\n\n"
        
    prompt = f"""
    A student is being tested on the topic: "{request.topic}".
    Evaluate their answers to the following questions for accuracy, completeness, and understanding.
    
    {qa_text}
    
    Return the evaluation as a JSON object with two keys:
    - "score": an integer from 0 to 100 representing the overall understanding.
    - "feedback": a short, constructive paragraph explaining what they got right and what needs improvement.
    
    Provide ONLY the raw JSON object. No markdown blocks, no extra text.
    """
    try:
        response = generate_content_with_retries(prompt)
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        evaluation = json.loads(content)
        score = int(evaluation.get("score", 0))
        feedback = evaluation.get("feedback", "No feedback provided.")
        verified = score > 60
        
        # Save to database
        verification = models.TopicVerification(
            user_id=user_id,
            topic=request.topic,
            score=score,
            feedback=feedback,
            verified=verified
        )
        db.add(verification)
        db.commit()
        db.refresh(verification)
        
        return {
            "score": score,
            "feedback": feedback,
            "verified": verified
        }
    except Exception as e:
        print(f"Gemini Error evaluating answers: {e}")
        # Fallback heuristic evaluation when AI is unavailable
        total_len = sum(len(str(a).split()) for a in request.answers)
        avg_len = total_len / max(1, len(request.answers))
        if avg_len > 20:
            score = 70
            feedback = "Answers show reasonable detail; expand on examples for deeper understanding."
        elif avg_len > 8:
            score = 50
            feedback = "Partial understanding demonstrated; include more specifics and examples."
        else:
            score = 30
            feedback = "Answers are too brief; elaborate on key points and provide examples."

        verified = score > 60
        try:
            verification = models.TopicVerification(
                user_id=user_id,
                topic=request.topic,
                score=score,
                feedback=feedback,
                verified=verified
            )
            db.add(verification)
            db.commit()
            db.refresh(verification)
        except Exception:
            # If DB save fails, still return the evaluation
            pass

        return {
            "score": score,
            "feedback": feedback,
            "verified": verified
        }
