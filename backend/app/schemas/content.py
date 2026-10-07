"""Versioned host-authored game content. Secrets never enter public snapshots."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

ROUND_TYPES = ['memory', 'emoji', 'connection', 'target', 'drawing', 'technical']
ROUND_NAMES = ['Memory Grid', 'Emoji Decode', 'Connection Hunt', 'Target Drop', 'Draw & Guess', 'Technical Showdown']


class ContentData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rows: int = Field(default=3, ge=1, le=6, strict=True)
    cols: int = Field(default=3, ge=1, le=6, strict=True)
    cells: list[str] = Field(default_factory=list, max_length=36)
    clues: list[str] = Field(default_factory=list, max_length=4)
    puzzle: str = Field(default='', max_length=4000)
    code: str = Field(default='', max_length=12000)
    target: int = Field(default=50, ge=1, le=1000000, strict=True)
    numbers: list[int] = Field(default_factory=list, max_length=10)
    image: str = ''
    operators: list[Literal['+', '-', '*', '/']] = Field(default_factory=lambda: ['+', '-', '*', '/'])
    useAllNumbers: bool = False
    exampleSolution: str = ''


class ContentQuestion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=80)
    prompt: str = Field(default='', max_length=4000)
    answerType: Literal['mcq', 'text', 'output', 'expression'] = 'text'
    options: list[str] = Field(default_factory=list, max_length=8)
    acceptedAnswers: list[str] = Field(default_factory=list, max_length=30)
    data: ContentData = Field(default_factory=ContentData)
    hard: bool = False
    isDemo: bool = False
    memoryTime: int = Field(default=10, ge=1, le=120)
    answerTime: int = Field(default=30, ge=1, le=300)
    instructions: str = ''
    scoringRule: Literal['existing', 'bank-v2'] = 'existing'
    lockAfterAttempt: bool = False


class ContentRound(BaseModel):
    model_config = ConfigDict(extra='forbid')
    gameType: Literal['memory', 'emoji', 'connection', 'target', 'drawing', 'technical']
    questions: list[ContentQuestion] = Field(default_factory=list, max_length=50)


class GameContent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int = Field(default=0, ge=0)
    rounds: list[ContentRound] = Field(min_length=6, max_length=6)

    @model_validator(mode='after')
    def ordered_rounds(self):
        if [r.gameType for r in self.rounds] != ROUND_TYPES:
            raise ValueError('The six round types must follow the configured order.')
        ids = [q.id for r in self.rounds for q in r.questions]
        if len(ids) != len(set(ids)):
            raise ValueError('Question IDs must be unique.')
        return self


def empty_content():
    return {'version': 0, 'rounds': [{'gameType': t, 'questions': []} for t in ROUND_TYPES]}


def content_errors(document):
    errors = []
    def add(path, message):
        errors.append({'path': path, 'message': message})
    for i, round_ in enumerate(document['rounds']):
        kind = round_['gameType']
        if any(q.get('isDemo') or q.get('scoringRule') == 'bank-v2' for q in round_['questions']):
            if len(round_['questions']) != 7 or not round_['questions'][0].get('isDemo') or sum(bool(q.get('isDemo')) for q in round_['questions']) != 1:
                add(f'rounds.{i}', 'Use one demo first, followed by six scored questions.')
        if not round_['questions']:
            add(f'rounds.{i}', 'Add at least one question.')
        for j, q in enumerate(round_['questions']):
            path = f'rounds.{i}.questions.{j}'
            data = q['data']
            if not q['prompt'].strip():
                add(path + '.prompt', 'Enter a question or secret card.')
            if kind != 'target' and not any(a.strip() for a in q['acceptedAnswers']):
                add(path + '.acceptedAnswers', 'Enter at least one accepted answer.')
            allowed = {'memory': ['mcq', 'text'], 'emoji': ['text'], 'connection': ['text'],
                       'target': ['expression'], 'drawing': ['text'], 'technical': ['mcq', 'text', 'output']}
            if q['answerType'] not in allowed[kind]:
                add(path + '.answerType', 'Unsupported answer type for this round.')
            if q['answerType'] == 'mcq':
                choices = q['options']
                if len(choices) < 2 or len(set(choices)) != len(choices) or any(not c.strip() for c in choices):
                    add(path + '.options', 'Enter 2–8 distinct, nonempty choices.')
                if len(q['acceptedAnswers']) != 1 or q['acceptedAnswers'][0] not in choices:
                    add(path + '.acceptedAnswers', 'Choose one correct answer from the options.')
            if kind == 'memory':
                rows, cols, cells = data.get('rows', 3), data.get('cols', 3), data.get('cells', [])
                if type(rows) is not int or type(cols) is not int or not 1 <= rows <= 6 or not 1 <= cols <= 6:
                    add(path + '.data', 'Grid dimensions must be between 1 and 6.')
                elif not data.get('image') and (not isinstance(cells, list) or len(cells) != rows * cols or any(not isinstance(c, str) or not c.strip() for c in cells)):
                    add(path + '.data.cells', 'Fill every grid cell.')
            if kind == 'connection':
                clues = data.get('clues', [])
                if not isinstance(clues, list) or len(clues) != 4 or any(not isinstance(c, str) or not c.strip() for c in clues):
                    add(path + '.data.clues', 'Enter four clues.')
            if kind == 'emoji' and not data.get('image') and not str(data.get('puzzle', '')).strip():
                add(path + '.data.puzzle', 'Enter the emoji puzzle.')
            if kind == 'target':
                numbers = data.get('numbers', [])
                if type(data.get('target')) is not int or not 1 <= data['target'] <= 1000000:
                    add(path + '.data.target', 'Target must be a positive integer up to 1,000,000.')
                if not isinstance(numbers, list) or not 2 <= len(numbers) <= 10 or any(type(n) is not int or not 1 <= n <= 10000 for n in numbers):
                    add(path + '.data.numbers', 'Supply 2–10 positive integers up to 10,000.')
            if q['hard'] and (kind != 'technical' or j != len(round_['questions']) - 1):
                add(path + '.hard', 'Only the last technical question may be marked hard.')
    return errors
