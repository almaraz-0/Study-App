"""In-memory stand-in for AnkiConnect, used as the Anki client's transport."""

import itertools
import re
from urllib.error import URLError

import pytest

TOKEN = re.compile(r'(-?)(?:(\w+):(?:"([^"]*)"|(\S+))|"((?:[^"\\]|\\.)*)"|(\S+))')


def _unescape(term):
    return re.sub(r"\\(.)", r"\1", term)


class FakeAnki:
    def __init__(self):
        self.decks = {"Default"}
        self.cards = {}  # cid -> {"deck", "nid", "suspended"}
        self.notes = {}  # nid -> {"model", "fields": {name: value}, "tags": set}
        self.models = {}  # name -> {"fields": [...], "isCloze": bool}
        self.calls = []
        self.down = False
        self.fail_actions = set()
        self.lose_reply = set()  # actions that succeed but whose reply never arrives
        self._ids = itertools.count(1000)

    # ---- test helpers -------------------------------------------------
    def add(self, deck, fields, model="Basic", tags=(), suspended=False, n_cards=1):
        nid = next(self._ids)
        self.notes[nid] = {"model": model, "fields": dict(fields), "tags": set(tags)}
        self.decks.add(deck)
        cids = []
        for _ in range(n_cards):
            cid = next(self._ids)
            self.cards[cid] = {"deck": deck, "nid": nid, "suspended": suspended}
            cids.append(cid)
        return nid, cids

    def writes(self):
        reads = {"version", "deckNames", "findCards", "findNotes", "getDecks",
                 "modelNames", "notesInfo", "cardsToNotes"}
        return [c for c in self.calls if c[0] not in reads]

    # ---- search ---------------------------------------------------------
    def _card_matches(self, cid, query):
        card = self.cards[cid]
        note = self.notes[card["nid"]]
        for neg, key, qval, val, quoted, bare in TOKEN.findall(query):
            if key:
                value = qval if qval else val
                key = key.lower()
                if key == "deck":
                    if value == "*":
                        ok = True
                    elif value.endswith("::*"):
                        ok = card["deck"].startswith(value[:-1])
                    else:
                        ok = card["deck"] == value or card["deck"].startswith(value + "::")
                elif key == "is":
                    ok = value == "suspended" and card["suspended"]
                elif key == "note":
                    ok = note["model"] == value
                elif key == "tag":
                    ok = value.lower() in {t.lower() for t in note["tags"]}
                else:
                    field = next((v for k, v in note["fields"].items() if k.lower() == key), None)
                    ok = field is not None and field.lower() == _unescape(value).lower()
            else:
                raw = quoted if quoted else bare
                fm = re.match(r"^(\w+):(.*)$", raw)
                if fm:  # quoted field search: "Word:me da pena"
                    field = next((v for k, v in note["fields"].items() if k.lower() == fm.group(1).lower()), None)
                    ok = field is not None and field.lower() == _unescape(fm.group(2)).lower()
                else:
                    term = _unescape(raw).lower()
                    ok = any(term in v.lower() for v in note["fields"].values())
            if bool(neg) == ok:
                return False
        return True

    # ---- transport --------------------------------------------------------
    def __call__(self, payload):
        if self.down:
            raise URLError("connection refused")
        action, params = payload["action"], payload.get("params", {})
        self.calls.append((action, params))
        if action in self.fail_actions:
            return {"result": None, "error": f"{action} failed"}
        try:
            result = getattr(self, "_" + action)(**params)
        except Exception as e:  # mirror AnkiConnect: errors come back in the body
            return {"result": None, "error": str(e)}
        if action in self.lose_reply:
            raise TimeoutError("reply lost")
        return {"result": result, "error": None}

    def _version(self):
        return 6

    def _deckNames(self):
        return sorted(self.decks)

    def _createDeck(self, deck):
        self.decks.add(deck)
        return 1

    def _findCards(self, query):
        return [cid for cid in self.cards if self._card_matches(cid, query)]

    def _findNotes(self, query):
        return sorted({self.cards[c]["nid"] for c in self._findCards(query)})

    def _getDecks(self, cards):
        out = {}
        for cid in cards:
            out.setdefault(self.cards[cid]["deck"], []).append(cid)
        return out

    def _changeDeck(self, cards, deck):
        self.decks.add(deck)
        for cid in cards:
            self.cards[cid]["deck"] = deck

    def _suspend(self, cards):
        for cid in cards:
            self.cards[cid]["suspended"] = True
        return True

    def _addTags(self, notes, tags):
        for nid in notes:
            self.notes[nid]["tags"].update(tags.split())

    def _deleteDecks(self, decks, cardsToo=False):
        for d in decks:
            for cid in [c for c, v in self.cards.items() if v["deck"] == d or v["deck"].startswith(d + "::")]:
                del self.cards[cid]
            self.decks = {x for x in self.decks if not (x == d or x.startswith(d + "::"))}

    def _cardsToNotes(self, cards):
        return sorted({self.cards[c]["nid"] for c in cards})

    def _modelNames(self):
        return sorted(self.models)

    def _createModel(self, modelName, inOrderFields, cardTemplates, css="", isCloze=False):
        self.models[modelName] = {"fields": inOrderFields, "isCloze": isCloze, "templates": cardTemplates, "css": css}
        return {"name": modelName}

    def _addNote(self, note):
        if note["modelName"] not in self.models:
            raise ValueError("model was not found")
        if note["deckName"] not in self.decks:
            raise ValueError("deck was not found: " + note["deckName"])
        nid, _ = self.add(note["deckName"], note["fields"], model=note["modelName"], tags=note.get("tags", []))
        return nid

    def _notesInfo(self, notes):
        out = []
        for nid in notes:
            if nid not in self.notes:  # real AnkiConnect returns {} for a missing note
                out.append({})
                continue
            n = self.notes[nid]
            out.append({
                "noteId": nid,
                "modelName": n["model"],
                "tags": sorted(n["tags"]),
                "fields": {k: {"value": v, "order": i} for i, (k, v) in enumerate(n["fields"].items())},
            })
        return out

    def _updateNoteFields(self, note):
        self.notes[note["id"]]["fields"].update(note["fields"])


@pytest.fixture
def fake_anki():
    return FakeAnki()
