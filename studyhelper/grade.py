"""Grade quiz answers. Case never matters; a missing accent counts but is flagged."""

import unicodedata


def _norm(s: str) -> str:
    return " ".join((s or "").split()).casefold()


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def grade(quiz: dict, given: dict[str, str]) -> dict:
    answers, keep = [], []
    for q in quiz["questions"]:
        g = given.get(q["id"], "") or ""
        accent_only = False
        if q["type"] == "choice":
            correct = g == q["answer"]
        else:
            a, b = _norm(g), _norm(q["answer"])
            correct = a == b
            if not correct and a and _strip_accents(a) == _strip_accents(b):
                correct = accent_only = True
        answers.append({"id": q["id"], "given": g, "correct": correct, "accent_only": accent_only})
        if not correct and q["item"] not in keep:
            keep.append(q["item"])
    return {
        "answers": answers,
        "score": sum(a["correct"] for a in answers),
        "total": len(answers),
        "keep": keep,
    }
