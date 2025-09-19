import streamlit as st
import boto3
import json
import time
import random
import requests

# Constants
S3_BUCKET = "pt-dataset-bucket-zehra"  # Replace with your S3 bucket name
S3_KEY = "pt-questions.json"
API_URL = "https://au195rai4m.execute-api.us-east-1.amazonaws.com/ask"  # Replace with your AI endpoint if using

TOTAL_TIME = 1200  # 20 minutes in seconds
NUM_QUESTIONS = 10
MARKS_PER_QUESTION = 10
MAX_MARKS = NUM_QUESTIONS * MARKS_PER_QUESTION
PASS_MARKS = int(MAX_MARKS * 0.7)

# Page Config
st.set_page_config(page_title="Practice Test Assistant 🎉", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #cc2f2f 0%, #e63939 50%, #ffffff 100%); /* slightly darker red gradient */
    font-family: 'Arial', sans-serif;
    color: white;
}
.title {
    font-size: 2.5rem;
    font-weight: bold;
    text-align: center;
    color: #000000;
    margin-top: 10px;
}
.subtitle {
    font-size: 1.2rem;
    text-align: center;
    color: #f8f8f8;
    margin-bottom: 10px;
}
/* Logo centered above the question */
.logo-container { 
    text-align: center; 
    margin-top: 15px; 
    margin-bottom: 10px; 
}
.logo-container img { 
    width: 100px; 
    height: auto; 
}
/* Question box */
.question-box {
    background: #ffe0b3;
    padding: 20px; 
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    color: #000;
    margin: 15px auto;
}
.ai-box {
    background: linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%);
    padding: 15px; 
    border-radius: 12px;
    margin-top: 15px; 
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    color: #000;
}
.timer { font-size: 1.2rem; font-weight: bold; color: #ffecec; }
.success { color: #00ff9d; font-weight: bold; }
.error { color: #ffb3b3; font-weight: bold; }
.result-box {
    background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
    padding: 20px; 
    border-radius: 15px; 
    color: #000; 
    text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
</style>
""", unsafe_allow_html=True)

# ---------- Logo ----------
st.markdown("""
<div class="logo-container">
    <img src="https://play-lh.googleusercontent.com/pUxNfrcwglo40Se238mGSMCQwBI-8niKDse6zdvgVnR4iCkQMckNqoE_WhcCSQVz9w" alt="Whizlabs Logo">
</div>
""", unsafe_allow_html=True)

# ---------- Session State Setup ----------
if "current_page" not in st.session_state: st.session_state.current_page = "landing"
if "quiz_started" not in st.session_state: st.session_state.quiz_started = False
if "questions" not in st.session_state: st.session_state.questions = []
if "current_question" not in st.session_state: st.session_state.current_question = 0
if "answers" not in st.session_state: st.session_state.answers = {}
if "checked_answers" not in st.session_state: st.session_state.checked_answers = {}
if "feedback" not in st.session_state: st.session_state.feedback = ""
if "start_time" not in st.session_state: st.session_state.start_time = None
if "paused" not in st.session_state: st.session_state.paused = False
if "submitted" not in st.session_state: st.session_state.submitted = False
if "ai_responses" not in st.session_state: st.session_state.ai_responses = {}

# ---------- Utility Functions ----------
@st.cache_data
def load_questions_from_s3():
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
    all_questions = json.loads(obj["Body"].read().decode("utf-8"))
    return all_questions

def get_time_remaining():
    if st.session_state.start_time is None:
        return TOTAL_TIME
    elapsed = time.time() - st.session_state.start_time
    return max(0, TOTAL_TIME - int(elapsed))

def submit_quiz():
    correct = 0
    for idx, q in enumerate(st.session_state.questions):
        sel = st.session_state.answers.get(idx)
        if sel == q["correct_answer"]:
            correct += 1
    st.session_state.score = correct * MARKS_PER_QUESTION
    st.session_state.current_page = "result"
    st.session_state.submitted = True

def check_answer_for_current():
    q_idx = st.session_state.current_question
    q = st.session_state.questions[q_idx]
    sel = st.session_state.answers.get(q_idx)
    correct = q["correct_answer"]
    st.session_state.checked_answers[q_idx] = sel
    if sel == correct:
        st.session_state.feedback = "Correct! ✅ Nice move!"
    else:
        st.session_state.feedback = f"Wrong! ❌ The correct answer is **{correct}**"

def ask_ai_for_current(user_query: str):
    q = st.session_state.questions[st.session_state.current_question]
    payload = {"qid": q["qid"], "question": user_query, "user_id": "student1"}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("answer"), data.get("source")
        else:
            return None, f"Error code {response.status_code}"
    except Exception as e:
        return None, str(e)

# ---------- Main App Flow ----------
if st.session_state.current_page == "landing":
    st.markdown('<div class="title">Practice Test Assistant 🎉</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Exam Instructions 🚀</div>', unsafe_allow_html=True)
    st.write("""
    The exam comprises:
    - Multiple Choice Single Response (MCSR)
    - Multiple Choice Multiple Response (MCMR) — No negative marking.
    A timer ⏰ in the top-right corner shows time left.
    """)
    st.markdown('<div class="subtitle">Exam Details 🎯</div>', unsafe_allow_html=True)
    st.write(f"Questions: {NUM_QUESTIONS}")
    st.write("Time: 20 minutes")
    st.write(f"Max. Marks: {MAX_MARKS}")
    st.write(f"Passing: 70% ({PASS_MARKS} marks)")

    if st.button("Start Quiz 🚀", key="start_quiz"):
        all_qs = load_questions_from_s3()
        st.session_state.questions = random.sample(all_qs, NUM_QUESTIONS)
        st.session_state.start_time = time.time()
        st.session_state.quiz_started = True
        st.session_state.current_page = "quiz"

elif st.session_state.current_page == "quiz":
    remaining = get_time_remaining()
    if remaining <= 0:
        submit_quiz()

    st.sidebar.markdown(f'<div class="timer">Time Remaining ⏰: {remaining // 60}:{remaining % 60:02d}</div>', unsafe_allow_html=True)

    # Pause / Resume
    if not st.session_state.paused:
        if st.sidebar.button("Pause Quiz ⏸️", key="pause"):
            st.session_state.paused = True
            st.session_state.pause_time = time.time()
    else:
        if st.sidebar.button("Continue 🚀", key="continue"):
            paused_duration = time.time() - st.session_state.pause_time
            st.session_state.start_time += paused_duration
            st.session_state.paused = False

    # Show question
    q_idx = st.session_state.current_question
    q = st.session_state.questions[q_idx]

    st.markdown(f'<div class="question-box"><b>Question {q_idx + 1}:</b> {q["question_text"]}</div>', unsafe_allow_html=True)

    options = list(q["options"].items())
    selected = st.radio("Select your answer:", [opt[1] for opt in options], key=f"q{q_idx}")

    for key, val in q["options"].items():
        if val == selected:
            st.session_state.answers[q_idx] = key

    if st.button("Check Answer ✅", key=f"check_{q_idx}"):
        check_answer_for_current()

    if q_idx in st.session_state.checked_answers:
        fb = st.session_state.feedback
        if "Correct" in fb:
            st.markdown(f'<div class="success">{fb}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="error">{fb}</div>', unsafe_allow_html=True)

    # Ask AI Box
    st.markdown('<div class="ai-box">', unsafe_allow_html=True)
    st.subheader("Ask AI about this question 🤖")
    user_query = st.text_input("E.g., 'Why is option A incorrect?'", key=f"query{q_idx}")
    if st.button("Ask AI 🚀", key=f"ask{q_idx}"):
        answer, source = ask_ai_for_current(user_query)
        if answer is None:
            st.error(f"AI Response Error: {source}")
        else:
            st.write(f"AI Answer: {answer} (Source: {source}) 🎯")
    st.markdown('</div>', unsafe_allow_html=True)

    # Navigation (only once!)
    col_prev, col_next, col_submit = st.columns(3)
    with col_prev:
        if st.button("⬅️ Previous", key="prev", disabled=(q_idx == 0)):
            st.session_state.current_question -= 1
    with col_next:
        if st.button("➡️ Next", key="next", disabled=(q_idx == NUM_QUESTIONS - 1)):
            st.session_state.current_question += 1
    with col_submit:
        if st.button("🎯 Submit Quiz", key="submit"):
            submit_quiz()

elif st.session_state.current_page == "result":
    score = st.session_state.score
    correct = score // MARKS_PER_QUESTION
    wrong = NUM_QUESTIONS - correct
    percent = (score / MAX_MARKS) * 100

    st.balloons()
    st.markdown('<div class="title">Final Results 🎊</div>', unsafe_allow_html=True)
    st.markdown('<div class="result-box">', unsafe_allow_html=True)
    st.write(f"✅ Correct: {correct} | ❌ Wrong: {wrong}")
    st.write(f"🏆 Score: **{score} / {MAX_MARKS}**")
    st.write(f"📊 Percentage: **{percent:.2f}%**")
    if score >= PASS_MARKS:
        st.success("🎉 Hurray! You're Genius 🤩🔥")
    else:
        st.error("😅 Leave it buddy! You can do it! Come fully prepared tomorrow 💪")
    st.markdown('</div>', unsafe_allow_html=True)
 
