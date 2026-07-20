# 🚀 ProLearn-AI

ProLearn-AI is an AI-powered personalized learning platform designed to help students enhance their technical skills through intelligent assessments and personalized learning recommendations. The platform leverages Google Gemini AI to dynamically generate multiple-choice questions, answers, explanations, and study recommendations based on each user's performance.

---

## ✨ Features

- 🤖 AI-generated MCQs
- 📝 AI-generated answers and explanations
- 📊 Performance analysis and insights
- 📈 Progress tracking
- 🎯 Personalized learning recommendations
- 🎥 YouTube learning resource suggestions
- 🔐 User authentication
- 👨‍💼 Admin dashboard
- 📱 Responsive user interface

---

## 🛠️ Tech Stack

### Frontend
- React.js
- Tailwind CSS
- React Router

### Backend
- FastAPI
- Python
- SQLAlchemy

### Database
- SQLite

### AI Integration
- Google Gemini API

### Authentication
- Firebase Authentication

---

## 📁 Project Structure

```
ProLearn-AI/
│
├── backend/
│   ├── main.py
│   ├── seed.py
│   ├── models.py
│   ├── schemas.py
|   |── seed.py
|   ├── .env    <-- Enter Your API Key Here
│   └──__pycache__/
│   └── static/

├── templates/
│   ├── index.html
│   ├── login.html
│   ├── profile.html
│   ├── result.html
│   └── ...



├── requirements.txt
├── README.md

```

---

# 🚀 How to Run the Project

## 1. Clone the Repository

```bash
git clone https://github.com/your-username/ProLearn-AI.git
cd ProLearn-AI
```

---

## 2. Create a Python 3.10 Virtual Environment

### Windows

```bash
py -3.10 -m venv venv
venv\Scripts\activate
```

### Linux/macOS

```bash
python3.10 -m venv venv
source venv/bin/activate
```

---

## 3. Install Required Dependencies

```bash
pip install -r requirements.txt
```

The project uses the following libraries:

- FastAPI
- Uvicorn
- SQLAlchemy
- python-multipart
- passlib[bcrypt]
- bcrypt==3.2.0
- python-dotenv
- Jinja2
- google-generativeai
- pydantic[email]

---

## 4. Configure Environment Variables

Create a `.env` file in the project root and add your Google Gemini API key.

Example:

```env
GEMINI_API_KEY=your_api_key_here
```

---

## 5. Initialize the Database

```bash
python -m backend.seed
```

---

## 6. Start the Backend Server

```bash
uvicorn backend.main:app --reload
```

The backend will be available at:

```
http://127.0.0.1:8000
```

Swagger API Documentation:

```
http://127.0.0.1:8000/docs
```

---

## 7. Start the Frontend

Open a new terminal.

```bash
cd frontend
npm install
npm start
```

The frontend will be available at:

```
http://localhost:3000
```

---


## 🎯 Workflow

1. User registers or logs in.
2. Selects a learning domain.
3. Google Gemini AI generates personalized MCQs.
4. User completes the assessment.
5. AI evaluates performance.
6. Weak areas are identified.
7. Personalized learning resources are recommended.
8. User progress is stored and visualized.

---

## 🚀 Future Enhancements

- AI Chat Tutor
- Voice-based learning assistant
- Coding challenge support
- Interview preparation module
- Mobile application
- Certificate generation
- Leaderboard system

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push the branch.
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Developer

**Prathamesh Kamble**
**Noman Makandar**
**Siddhi Patane**
**Shubham Aiwale**
**Vrunda BUte**

Bachelor of Engineering (Computer Engineering)



---

## ⭐ Support

If you found this project helpful, consider giving it a ⭐ on GitHub!