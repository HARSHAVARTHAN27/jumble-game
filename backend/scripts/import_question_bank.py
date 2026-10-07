"""Extract the supplied v2 bank and its updated visuals into project assets.

Run from the repository root with the source DOCX path. Does not write to a database.
"""
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def extract(source):
    with zipfile.ZipFile(source) as archive:
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        xml = ET.fromstring(archive.read('word/document.xml'))
        text = '\n'.join(''.join(t.text or '' for t in p.findall('.//w:t', ns)) for p in xml.findall('.//w:p', ns))
        kinds = ['memory', 'emoji', 'connection', 'target', 'drawing', 'technical']
        names = ['Memory Grid', 'Emoji Decode', 'Connection Hunt', 'Target Drop', 'Draw & Guess', 'Technical Showdown']
        rounds = []
        clues = [['Gmail', 'Maps', 'Drive', 'YouTube'], ['Keyboard', 'Piano', 'Typewriter', 'Calculator'], ['Mercury', 'Gemini', 'Apollo', 'Artemis'], ['Apple', 'BlackBerry', 'Raspberry', 'Orange'], ['Tesla', 'Faraday', 'Watt', 'Hertz'], ['Python', 'Ruby', 'Swift', 'Rust'], ['200', '301', '404', '500']]
        targets = [24, 73, 96, 101, 118, 121, 130]
        numbers = [[8, 6, 4, 2], [9, 8, 7, 4, 2], [12, 9, 7, 5, 3], [10, 9, 7, 6, 3], [15, 12, 8, 5, 4], [14, 13, 8, 5, 3], [17, 10, 7, 4, 2]]
        options = [['200', '301', '404', '500'], ['[18, 12]', '[15, 9]', '[15, 12, 9]', '[18, 15, 12]'], ['Engineering only', 'HR only', 'Engineering and HR', 'Engineering and Sales'], ['192.168.10.0/26', '192.168.10.64/26', '192.168.10.77/26', '192.168.10.128/26'], ['The last commit is removed and its changes stay staged', 'The last commit and changes are deleted', 'The working tree is reset but the commit stays', 'Only untracked files are removed'], ['POST /orders to create a new order', 'PUT /users/42 with the full user representation', 'POST /payments to charge a card', 'PATCH /counter with “increment by 1”'], ['70.0%', '76.4%', '84.0%', '91.3%']]
        codes = {1: 'x = [3, 6, 9, 12, 15, 18]\nprint(x[-2:0:-2])', 2: 'Employees after WHERE salary > 50000:\nEngineering: 70000\nEngineering: 65000\nHR: 60000\nSales: 75000\n\nSELECT department\nFROM employees\nWHERE salary > 50000\nGROUP BY department\nHAVING COUNT(*) >= 2;'}
        assets = ROOT / 'frontend/public/images/questions'
        assets.mkdir(parents=True, exist_ok=True)
        for ri, (kind, name) in enumerate(zip(kinds, names)):
            questions = []
            for j in range(7):
                label = 'Demo' if j == 0 else f'Q{j}'
                match = re.search(re.escape(f'{name} — {label}') + r'\n+Player prompt\n(.*?)\nCorrect answer\n(.*?)\nPoints\n', text, re.S)
                if not match:
                    raise ValueError(f'Missing {name} {label}')
                prompt, answer = match.groups()
                q = dict(id=f'r{ri+1}-' + ('demo' if j == 0 else f'q{j}'), prompt=prompt, answerType='text', options=[], acceptedAnswers=[answer], data={}, hard=kind == 'technical' and j == 6, isDemo=j == 0, memoryTime=10, answerTime=30, scoringRule='bank-v2', lockAfterAttempt=kind in ('memory', 'technical'), instructions='Practice only: try the interaction, then continue to Question 1.' if j == 0 else '')
                if kind in ('memory', 'emoji'):
                    # Images 1–14 are superseded by the UPDATED images 43–56.
                    image_number = 43 + j if kind == 'memory' else 50 + j
                    filename = f'{kind}-' + ('demo' if j == 0 else f'q{j}') + '.png'
                    (assets / filename).write_bytes(archive.read(f'word/media/image{image_number}.png'))
                    q['data']['image'] = '/images/questions/' + filename
                if kind == 'memory':
                    q['memoryTime'] = [10, 12, 12, 12, 15, 15, 18][j]
                    q['instructions'] += ' Memorize the visual without screenshots or notes. It will disappear before the question appears. Submit one team answer; include every requested detail.'
                    if 1 <= j <= 5:
                        parts = answer.split(' AND ')
                        q['acceptedAnswers'] += [' and '.join(parts), ', '.join(parts), ' & '.join(parts)]
                    if j == 6:
                        q['acceptedAnswers'] += ['Database 84%, Backup 100%, Inventory 79%', '84%, 100%, 79%', '84 100 79']
                if kind == 'emoji':
                    q['answerTime'] = 20
                    q['acceptedAnswers'] += [a.strip() for a in answer.split(' / ')]
                    if j == 1: q['acceptedAnswers'] += ['Two-Factor Authentication', 'Two Factor Authentication', '2FA']
                    if j == 2: q['acceptedAnswers'] += ['Phishing']
                    if j == 6: q['acceptedAnswers'] += ['CI/CD', 'Continuous Integration and Continuous Deployment']
                    q['instructions'] += ' Decode the technology or workplace concept and type your answer.'
                if kind == 'connection':
                    q['data']['clues'] = clues[j]
                    q['acceptedAnswers'] += [a.strip() for a in answer.split(' / ')]
                    if j == 0: q['acceptedAnswers'] += ['Google products', 'Google services', 'Google']
                    if j == 1: q['acceptedAnswers'] += ['Keys', 'They have keys']
                    if j == 2: q['acceptedAnswers'] += ['NASA programs', 'NASA human-spaceflight programs']
                    if j == 3: q['acceptedAnswers'] += ['Fruit names', 'Fruit technology brands']
                    if j == 4: q['acceptedAnswers'] += ['Scientists named after units', 'Scientists associated with scientific units']
                    q['instructions'] += ' Clues arrive one at a time. Earlier correct answers earn 40 / 30 / 20 / 10 points. Existing retry rules apply.'
                if kind == 'target':
                    q['answerType'] = 'expression'
                    q['answerTime'] = 45
                    q['acceptedAnswers'] = []
                    q['data'] = dict(target=targets[j], numbers=numbers[j], operators=['+', '-', '*', '/'], useAllNumbers=True, exampleSolution=answer.split(' = ')[0])
                    q['instructions'] += ' Use every supplied number exactly once with +, −, ×, ÷ and parentheses. Exact earns 40. If nobody is exact, closest valid teams rank 30 / 20 / 10.'
                if kind == 'drawing':
                    q['prompt'] = answer
                    q['answerTime'] = 45
                    if j == 1: q['acceptedAnswers'] += ['Broken WiFi', 'Broken Wi Fi']
                    q['instructions'] += ' No speaking. No writing the actual word. No letters or numbers. No mouthing the answer or spelling through gestures. Do not show the secret card.'
                if kind == 'technical':
                    q['answerType'] = 'mcq'
                    q['options'] = options[j]
                    q['answerTime'] = 30 if j == 6 else 20
                    q['data']['code'] = codes.get(j, '')
                    q['instructions'] += ' Select one answer. Your team answer locks after submission.'
                q['acceptedAnswers'] = list(dict.fromkeys(q['acceptedAnswers']))
                questions.append(q)
            rounds.append(dict(gameType=kind, questions=questions))
        output = ROOT / 'backend/app/data/question_bank_v2.json'
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(dict(version=0, rounds=rounds), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    extract(sys.argv[1])
