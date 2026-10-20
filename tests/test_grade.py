from studyhelper.grade import grade

QUIZ = {
    "title": "Emociones",
    "questions": [
        {"id": "q1", "type": "cloze", "prompt": "Me siento ___.", "hint": "overwhelmed", "answer": "abrumado", "item": "abrumado"},
        {"id": "q2", "type": "cloze", "prompt": "Me quedé ___.", "hint": "astonished", "answer": "atónito", "item": "atónito"},
        {"id": "q3", "type": "choice", "prompt": "Me ___ rabia.", "hint": None, "answer": "da",
         "options": ["pone", "da", "deja"], "item": "me da rabia"},
    ],
}


def by_id(results):
    return {a["id"]: a for a in results["answers"]}


def test_grade_exact_and_case():
    a = by_id(grade(QUIZ, {"q1": "  Abrumado "}))["q1"]
    assert a["correct"] is True and a["accent_only"] is False


def test_grade_accent_only_is_correct_with_flag():
    a = by_id(grade(QUIZ, {"q2": "atonito"}))["q2"]
    assert a["correct"] is True and a["accent_only"] is True


def test_grade_wrong_goes_to_keep():
    r = grade(QUIZ, {"q1": "agobiado", "q2": "atónito", "q3": "pone"})
    assert r["score"] == 1 and r["total"] == 3
    assert r["keep"] == ["abrumado", "me da rabia"]


def test_grade_blank_is_wrong():
    r = grade(QUIZ, {})
    assert r["score"] == 0
    assert by_id(r)["q1"]["given"] == ""


def test_grade_choice_exact():
    assert by_id(grade(QUIZ, {"q3": "da"}))["q3"]["correct"] is True
    assert by_id(grade(QUIZ, {"q3": "Da "}))["q3"]["correct"] is False
