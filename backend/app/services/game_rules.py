"""Pure scoring and arithmetic rules; no eval(), code execution, or client clocks."""
import ast
import unicodedata
from collections import Counter
from fractions import Fraction
from app.exceptions import AppError


def normalized(answer, output=False):
    text = unicodedata.normalize('NFKC', answer).replace('\r\n', '\n').strip()
    return text if output else ' '.join(text.casefold().split())


def matches(question, answer):
    if question['answerType'] == 'mcq':
        return answer in question['acceptedAnswers']
    output = question['answerType'] == 'output'
    return normalized(answer, output) in [normalized(a, output) for a in question['acceptedAnswers']]


def expression_value(expression, numbers, operators=None, use_all=False):
    try:
        tree = ast.parse(expression.replace('×', '*').replace('÷', '/').replace('−', '-'), mode='eval')
        if len(expression) > 200 or sum(1 for _ in ast.walk(tree)) > 80:
            raise ValueError()
        used = Counter()
        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) is int and node.value > 0:
                used[node.value] += 1
                if used[node.value] > Counter(numbers)[node.value]:
                    raise ValueError()
                return Fraction(node.value)
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                symbol = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/'}[type(node.op)]
                if operators is not None and symbol not in operators: raise ValueError()
                left, right = visit(node.left), visit(node.right)
                if isinstance(node.op, ast.Add): result = left + right
                elif isinstance(node.op, ast.Sub): result = left - right
                elif isinstance(node.op, ast.Mult): result = left * right
                else: result = left / right
                if abs(result.numerator) > 10**15 or result.denominator > 10**15:
                    raise ValueError()
                return result
            raise ValueError()
        result = visit(tree.body)
        if use_all and used != Counter(numbers): raise ValueError()
        if result.denominator != 1:
            raise ValueError()
        return int(result)
    except (ValueError, SyntaxError, ZeroDivisionError, RecursionError, OverflowError):
        raise AppError('INVALID_EXPRESSION', 'Use the supplied numbers ' + ('exactly once' if use_all else 'at most once') + ' with the permitted operators and parentheses. The result must be an integer.') from None


def points(kind, elapsed, hard=False, distance=None):
    if kind == 'memory': return 20 + (5 if elapsed <= 5 else 0)
    if kind == 'emoji': return 20
    if kind == 'connection': return [40, 30, 20, 10][min(3, int(elapsed // 7))]
    if kind == 'target':
        return 40 if distance == 0 else 30 if distance == 1 else 20 if distance <= 3 else 10 if distance <= 5 else 0
    if kind == 'drawing': return 30 if elapsed <= 15 else 20
    return 50 if hard else 30


def score_question(question, kind, submissions, teams, overrides=None):
    """Choose one scoring submission per team, deterministically by receipt order."""
    overrides = overrides or {}
    candidates = {team: [] for team in teams}
    for sub in submissions:
        if sub['teamId'] not in candidates: continue
        if kind == 'target' or overrides.get(sub['id'], sub['correct']):
            candidates[sub['teamId']].append(sub)
    winners = {}
    for team, attempts in candidates.items():
        if attempts:
            winners[team] = min(attempts, key=lambda s: (s['distance'], s['receivedAt'], s['sequence'])) if kind == 'target' else min(attempts, key=lambda s: (s['receivedAt'], s['sequence']))
    first = min(winners, key=lambda t: (winners[t]['receivedAt'], winners[t]['sequence'])) if winners else None
    if question.get('isDemo'):
        return {team: {'points': 0, 'playerId': None} for team in teams}
    if kind == 'target' and question.get('scoringRule') == 'bank-v2':
        exact = any(s['distance'] == 0 for s in winners.values())
        ranked = sorted(winners, key=lambda t: (winners[t]['distance'], winners[t]['receivedAt'], winners[t]['sequence']))
        return {team: {'points': (40 if winners[team]['distance'] == 0 else 0) if exact else [30, 20, 10][ranked.index(team)] if ranked.index(team) < 3 else 0, 'playerId': winners[team]['playerId']} if team in winners else {'points': 0, 'playerId': None} for team in teams}
    if kind == 'memory' and question.get('scoringRule') == 'bank-v2':
        # The document's fastest bonus is optional; use its 20-point base.
        return {team: {'points': 20, 'playerId': winners[team]['playerId']} if team in winners else {'points': 0, 'playerId': None} for team in teams}
    if kind == 'drawing' and question.get('scoringRule') == 'bank-v2':
        return {team: {'points': 30 if winners[team]['elapsed'] <= 15 else 20 if winners[team]['elapsed'] <= 30 else 10, 'playerId': winners[team]['playerId']} if team in winners else {'points': 0, 'playerId': None} for team in teams}
    return {team: {'points': points(kind, winners[team]['elapsed'], question.get('hard', False), winners[team].get('distance')) + (10 if kind in ('emoji', 'technical') and team == first else 0), 'playerId': winners[team]['playerId']} if team in winners else {'points': 0, 'playerId': None} for team in teams}
