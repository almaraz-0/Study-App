"""The two note types the new system writes: Learn Vocab and Learn Grammar."""

from studyhelper import config

VOCAB_FIELDS = ["Word", "Meaning", "Prompt", "Sentence", "SentenceEN", "Tip", "Examples", "Source", "Recognize"]
GRAMMAR_FIELDS = ["Text", "Rule", "Reference", "Source"]

CSS = """
.card {
  font-family: "Iowan Old Style", "Palatino", Georgia, serif;
  font-size: 20px; line-height: 1.5; text-align: left;
  color: #1b1d33; background: #f6f6fa;
  max-width: 640px; margin: 0 auto; padding: 18px 16px;
}
.card.nightMode { color: #ecedf6; background: #16172a; }
b { color: #d1006f; }
.nightMode b { color: #ff5ca8; }
.word { font-family: -apple-system, "Helvetica Neue", sans-serif; font-weight: 700; font-size: 1.6em; line-height: 1.1; }
.meaning { font-family: -apple-system, "Helvetica Neue", sans-serif; font-weight: 600; font-size: 1.05em; margin-bottom: 10px; }
.prompt { font-size: 1.15em; }
.blank { color: #d1006f; font-weight: 700; }
.nightMode .blank { color: #ff5ca8; }
.en, .muted { color: #5d6180; font-style: italic; font-size: 0.9em; }
.nightMode .en, .nightMode .muted { color: #9ea2c0; }
.tip { background: #fbe3ef; border-radius: 10px; padding: 10px 12px; margin: 14px 0; font-size: 0.92em; }
.nightMode .tip { background: #3a1a2e; }
.label { font-family: ui-monospace, Menlo, monospace; font-size: 0.65em; letter-spacing: .08em; text-transform: uppercase; color: #d1006f; display: block; }
.nightMode .label { color: #ff5ca8; }
.examples ul { padding-left: 1.1em; margin: 6px 0; }
.examples li { margin: 6px 0; }
.source { font-size: 0.7em; color: #5d6180; margin-top: 16px; }
.nightMode .source { color: #9ea2c0; }
.source a { color: inherit; }
.cloze { color: #d1006f; font-weight: 700; }
.nightMode .cloze { color: #ff5ca8; }
.rule { margin-top: 14px; }
hr#answer { border: 0; border-top: 1px solid #dcdeea; margin: 16px 0; }
"""

_EXTRAS = """
{{#Tip}}<div class="tip"><span class="label">Tip</span>{{Tip}}</div>{{/Tip}}
{{#Examples}}<div class="examples"><span class="label">Más ejemplos</span>{{Examples}}</div>{{/Examples}}
{{#Source}}<div class="source">{{Source}}</div>{{/Source}}
"""

VOCAB_TEMPLATES = [
    {
        "Name": "Produce",
        "Front": '<div class="meaning">{{Meaning}}</div>\n<div class="prompt">{{Prompt}}</div>',
        "Back": (
            '<div class="meaning">{{Meaning}}</div>\n<div class="prompt">{{Prompt}}</div>\n<hr id="answer">\n'
            '<div class="word">{{Word}}</div>\n<div>{{Sentence}}</div>\n'
            '{{#SentenceEN}}<div class="en">{{SentenceEN}}</div>{{/SentenceEN}}' + _EXTRAS
        ),
    },
    {
        "Name": "Recognize",
        "Front": '{{#Recognize}}<div class="word">{{Word}}</div>{{/Recognize}}',
        "Back": (
            '<div class="word">{{Word}}</div>\n<hr id="answer">\n<div class="meaning">{{Meaning}}</div>\n'
            '<div>{{Sentence}}</div>\n{{#SentenceEN}}<div class="en">{{SentenceEN}}</div>{{/SentenceEN}}' + _EXTRAS
        ),
    },
]

GRAMMAR_TEMPLATES = [
    {
        "Name": "Cloze",
        "Front": '<div class="prompt">{{cloze:Text}}</div>',
        "Back": (
            '<div class="prompt">{{cloze:Text}}</div>\n<hr id="answer">\n'
            '{{#Rule}}<div class="tip rule"><span class="label">Regla</span>{{Rule}}</div>{{/Rule}}\n'
            '{{#Reference}}<div class="muted">{{Reference}}</div>{{/Reference}}\n'
            '{{#Source}}<div class="source">{{Source}}</div>{{/Source}}'
        ),
    },
]


def ensure_models(anki) -> list[str]:
    existing = set(anki.invoke("modelNames"))
    created = []
    for name, fields, templates, cloze in (
        (config.VOCAB_MODEL, VOCAB_FIELDS, VOCAB_TEMPLATES, False),
        (config.GRAMMAR_MODEL, GRAMMAR_FIELDS, GRAMMAR_TEMPLATES, True),
    ):
        if name in existing:
            continue
        anki.invoke(
            "createModel",
            modelName=name,
            inOrderFields=fields,
            css=CSS,
            isCloze=cloze,
            cardTemplates=templates,
        )
        created.append(name)
    return created
