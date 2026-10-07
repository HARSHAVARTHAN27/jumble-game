"""Server-only bank: never import this JSON into a frontend bundle."""
import json
from pathlib import Path
from app.schemas.content import GameContent


def question_bank(version=0):
    document = json.loads((Path(__file__).resolve().parents[1] / 'data/question_bank_v2.json').read_text(encoding='utf-8'))
    document['version'] = version
    return GameContent(**document).model_dump()
