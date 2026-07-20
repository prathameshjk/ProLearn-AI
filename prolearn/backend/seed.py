import json
import os
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models

def seed_data():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # 1. Clear existing questions to avoid duplicates on re-seed
    db.query(models.Question).delete()
    db.query(models.Recommendation).delete()
    db.commit()

    # Domains
    domains = [
        "Artificial Intelligence", "Data Science", "Cybersecurity", 
        "Cloud Computing", "Full Stack Development", "Mobile App Development", 
        "Deep Learning", "Natural Language Processing"
    ]
    
    # Load from separate JSON files
    questions_dir = os.path.join(os.path.dirname(__file__), "..", "data", "questions")
    final_questions = []
    
    domain_file_map = {
        "Artificial Intelligence": "artificial_intelligence.json",
        "Data Science": "data_science.json",
        "Cybersecurity": "cybersecurity.json",
        "Cloud Computing": "cloud_computing.json",
        "Full Stack Development": "full_stack_development.json",
        "Mobile App Development": "mobile_app_development.json",
        "Deep Learning": "deep_learning.json",
        "Natural Language Processing": "natural_language_processing.json"
    }

    for domain, filename in domain_file_map.items():
        file_path = os.path.join(questions_dir, filename)
        domain_questions = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                domain_questions = json.load(f)
        
        # Add real ones from file
        for q in domain_questions:
            final_questions.append(models.Question(
                domain=domain,
                topic=q.get('topic', 'General'),
                question_text=q['question_text'],
                option_a=q['option_a'],
                option_b=q['option_b'],
                option_c=q['option_c'],
                option_d=q['option_d'],
                correct_option=q['correct_option']
            ))
        
        # Fill the rest to reach 200 with unique text
        current_count = len(domain_questions)
        for i in range(current_count + 1, 201):
            final_questions.append(models.Question(
                domain=domain,
                topic="General",
                question_text=f"{domain} Mastery Question {i}: Identify the correct approach for this scenario.",
                option_a="Strategic Analysis",
                option_b="Technical Implementation",
                option_c="Optimized Solution",
                option_d="Peer Review",
                correct_option="C"
            ))

    # Sample Recommendations
    recommendations = [
        models.Recommendation(topic="Search Algorithms", video_url="https://youtu.be/z0GhX_d6P-s", course_url="https://www.coursera.org/learn/algorithms-part1", pdf_url="#", notes="Focus on Dijkstra and A* algorithms."),
        models.Recommendation(topic="Machine Learning", video_url="https://youtu.be/GwIo3gDZCVQ", course_url="https://www.coursera.org/learn/machine-learning", pdf_url="#", notes="Learn about supervised vs unsupervised learning."),
        models.Recommendation(topic="Statistics", video_url="https://youtu.be/VhzXU4T_c1Q", course_url="https://www.edx.org/course/statistics-and-data-science", pdf_url="#", notes="Brush up on descriptive statistics."),
        models.Recommendation(topic="Encryption", video_url="https://youtu.be/jkV1692nyXw", course_url="https://www.coursera.org/learn/cryptography", pdf_url="#", notes="Study AES and RSA algorithms."),
        models.Recommendation(topic="Neural Networks", video_url="https://youtu.be/aircAruvnKk", course_url="https://www.coursera.org/specializations/deep-learning", pdf_url="#", notes="Understand backpropagation and activation functions."),
        models.Recommendation(topic="Tokenization", video_url="https://youtu.be/fNxaJsNG3-s", course_url="https://www.coursera.org/learn/natural-language-processing", pdf_url="#", notes="Learn about NLTK and SpaCy libraries.")
    ]
    
    db.bulk_save_objects(final_questions)
    db.add_all(recommendations)
    db.commit()
    db.close()
    print(f"Database seeded successfully with {len(final_questions)} questions!")

if __name__ == "__main__":
    seed_data()
