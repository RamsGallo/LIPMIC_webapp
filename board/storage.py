# storage.py
import json, os, uuid

QUESTIONS_FILE = "board/questions.json"

def load_questions():
    if not os.path.exists(QUESTIONS_FILE):
        return {}
    with open(QUESTIONS_FILE, "r") as f:
        return json.load(f)

def save_questions(data):
    with open(QUESTIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_question(assessment_type, difficulty, prompt, images, correct):
    data = load_questions()
    if assessment_type not in data:
        data[assessment_type] = {"easy": [], "medium": [], "hard": []}
    q = {
        "id": str(uuid.uuid4()),
        "prompt": prompt,
        "images": images,
        "correct": correct
    }
    data[assessment_type][difficulty].append(q)
    save_questions(data)
    return q

def update_question(assessment_type, difficulty, q_id, prompt, images, correct):
    data = load_questions()
    questions = data.get(assessment_type, {}).get(difficulty, [])
    for q in questions:
        if q["id"] == q_id:
            q.update({"prompt": prompt, "images": images, "correct": correct})
            save_questions(data)
            return True
    return False

def delete_question(assessment_type, difficulty, q_id):
    data = load_questions()
    questions = data.get(assessment_type, {}).get(difficulty, [])
    new_questions = [q for q in questions if q["id"] != q_id]
    data[assessment_type][difficulty] = new_questions
    save_questions(data)
    return True
