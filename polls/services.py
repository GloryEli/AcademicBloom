import math
from collections.abc import Iterable, Mapping
from html import escape
from typing import SupportsFloat, TypedDict


class CourseOutcome(TypedDict):
    predicted_score: float
    study_guide: str


class QuizStudyRecommendation(TypedDict):
    predicted_score: float
    study_tips: list[str]


def _number(data: Mapping[str, object], key: str, default: object) -> float:
    value = data.get(key, default)
    if not isinstance(value, (str, SupportsFloat)):
        raise ValueError(f"{key} must be a number")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{key} must be a number") from error

    if not math.isfinite(number):
        raise ValueError(f"{key} must be a finite number")
    return number


def predict_course_score(data: Mapping[str, object]) -> float:
    """Predict a score from the student's actual course inputs."""
    previous_scores = _number(data, "previous_scores", data.get("previous_grades", 50))
    hours_studied = _number(data, "hours_studied", data.get("hours_per_week", 0))
    sleep_hours = _number(data, "sleep_hours", 0)
    question_papers = _number(data, "question_papers", data.get("question_papers_solved", 0))

    extracurricular = str(data.get("extracurricular", "No")).strip().lower() == "yes"
    motivation = str(data.get("motivation", data.get("motivation_level", "medium"))).lower()

    score = previous_scores
    score += hours_studied * 0.55
    score += question_papers * 0.8
    score += {"high": 7, "medium": 3, "low": -4}.get(motivation, 0)
    score += 5 if extracurricular else -2
    score += max(-6, min(6, (sleep_hours - 7) * 1.4))

    return round(max(0, min(100, score)), 1)


def generate_study_guidance(data: Mapping[str, object], predicted_score: float | None = None) -> list[str]:
    """Generate rule-based study tips from the same student inputs used for prediction."""
    hours_studied = _number(data, "hours_studied", data.get("hours_per_week", 0))
    sleep_hours = _number(data, "sleep_hours", 0)
    question_papers = _number(data, "question_papers", data.get("question_papers_solved", 0))
    motivation = str(data.get("motivation", data.get("motivation_level", "medium"))).lower()
    preferred_style = str(data.get("preferred_learning_style", data.get("learning_style", ""))).lower()
    goal = str(data.get("goal", "")).strip()

    tips: list[str] = []
    if predicted_score is not None:
        if predicted_score < 60:
            tips.append("Prioritise the most difficult topics first and review them before each study session.")
        elif predicted_score < 80:
            tips.append("Keep a steady revision rhythm and spend extra time on mistakes from recent quizzes.")
        else:
            tips.append("Maintain your revision rhythm and use practice questions to keep your score consistently high.")

    if hours_studied < 5:
        tips.append("Set aside a few focused study blocks each week and keep them consistent.")
    elif hours_studied > 20:
        tips.append("Break long sessions into shorter blocks so you stay focused and avoid burnout.")
    else:
        tips.append("Continue your current routine and make sure each session has a clear aim.")

    if question_papers < 3:
        tips.append("Practice at least one timed question paper each week and review the errors carefully.")
    else:
        tips.append("Keep working through question papers and use each mistake to improve your revision targets.")

    if sleep_hours < 7:
        tips.append("Aim for at least 7 hours of sleep so you can think clearly during revision and tests.")
    elif sleep_hours > 9:
        tips.append("Keep a regular sleep routine to maintain concentration and avoid tired study sessions.")

    if motivation == "low":
        tips.append("Start with one small task you can finish quickly to build momentum.")
    elif motivation == "high":
        tips.append("Use your strong motivation to focus on deeper problem-solving and difficult topics.")

    if "visual" in preferred_style:
        tips.append("Use diagrams, summaries, colour-coding, and mind maps for revision.")
    elif "auditory" in preferred_style:
        tips.append("Explain ideas aloud or teach the topic to someone else to strengthen recall.")
    elif "kinesthetic" in preferred_style:
        tips.append("Use worked examples, hands-on practice, and short active recall drills.")
    elif "reading_writing" in preferred_style:
        tips.append("Turn your notes into short summaries, flashcards, and written explanations.")
    elif "social" in preferred_style:
        tips.append("Study with a partner or group and explain difficult concepts out loud.")

    if goal:
        tips.append(f"Keep your revision closely linked to your goal: {goal}.")

    return tips


def predict_quiz_score(
    quiz_scores: Iterable[float],
    target_grade: float,
    hours_studied: float,
) -> QuizStudyRecommendation:
    """Estimate a score from quiz results and return study tips."""
    quiz_scores = list(quiz_scores)
    if not quiz_scores:
        raise ValueError("at least one quiz score is required")

    scores: list[float] = []
    for score in quiz_scores:
        try:
            numeric_score = float(score)
        except (TypeError, ValueError) as error:
            raise ValueError("quiz scores must be numbers") from error
        if not math.isfinite(numeric_score) or not 0 <= numeric_score <= 100:
            raise ValueError("quiz scores must be finite values between 0 and 100")
        scores.append(numeric_score)

    try:
        numeric_target = float(target_grade)
        numeric_hours = float(hours_studied)
    except (TypeError, ValueError) as error:
        raise ValueError("target grade and hours studied must be numbers") from error

    if not math.isfinite(numeric_target) or not 0 <= numeric_target <= 100:
        raise ValueError("target grade must be a finite value between 0 and 100")
    if not math.isfinite(numeric_hours) or numeric_hours < 0:
        raise ValueError("hours studied must be a finite, non-negative number")

    quiz_average = sum(scores) / len(scores)
    predicted_score = round(quiz_average * 0.7 + numeric_target * 0.3, 1)
    study_tips = generate_study_guidance(
        {
            "hours_studied": numeric_hours,
            "goal": "Reach your target grade",
            "preferred_learning_style": "",
            "motivation": "medium",
            "question_papers": 0,
            "sleep_hours": 7,
        },
        predicted_score,
    )

    return {
        "predicted_score": predicted_score,
        "study_tips": study_tips,
    }


def simulate_course_outcome(data: Mapping[str, object]) -> CourseOutcome:
    """Backwards-compatible course prediction and guidance generator."""
    predicted_score = predict_course_score(data)
    guidance_tips = generate_study_guidance(data, predicted_score)
    study_guide = "<ul>" + "".join(f"<li>{escape(tip)}</li>" for tip in guidance_tips) + "</ul>"

    return {
        "predicted_score": predicted_score,
        "study_guide": study_guide,
    }
