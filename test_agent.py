import sys
sys.path.insert(0, '.')
from backend.agent.teacher_agent import TeacherAgent

agent = TeacherAgent()

print("QUIZ TEST:")
result = agent.quiz_response(
    student_name   = "Sara",
    word           = "necessary",
    student_attempt = "neccesary",
    attempt_number = 1,
    grade_level    = 4
)
print(result["response"])
print(f"Correct: {result['is_correct']}")
print(f"Error type: {result['eval'].get('error_type')}")

print()
print("LEARN TEST:")
result2 = agent.learn_response(
    student_name = "Sara",
    word         = "photograph",
    grade_level  = 5
)
print(result2["response"])