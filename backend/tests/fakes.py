"""In-memory PostgREST boundary for deterministic foundation tests; no cloud writes."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
from postgrest.exceptions import APIError


def api_error(code):
    return APIError({"code": code, "message": "test database error", "details": None, "hint": None})


class Database:
    def __init__(self):
        self.tables = {
            "games": [{"id": "game-a", "status": "lobby", "allow_late_join": False}],
            "teams": [
                {"id": "team-a", "name": "Ctrl Alt Defeat", "slug": "ctrl-alt-defeat"},
                {"id": "team-b", "name": "Titans", "slug": "titans"},
                {"id": "team-c", "name": "Vibe Tribe", "slug": "vibe-tribe"},
            ],
            "employees": [{"id": "employee-a", "name": "Harsha Kumar", "normalized_name": "harsha kumar",
                           "employee_code": "EMP001", "team_id": "team-a", "is_active": True}],
            "players": [],
            "jumble_content": [],
            "jumble_runtime": [],
        }
        self.race = False
        self.insert_fail_name = None
        self.fault = None
        self.auth = SimpleNamespace(get_user=lambda token: SimpleNamespace(user=None))

    def from_(self, table):
        assert table in self.tables, f"Unexpected deferred table query: {table}"
        return Query(self, table)

    def rpc(self, name, params):
        db = self
        class Call:
            def execute(self):
                if name == 'jumble_create_game':
                    active = [g for g in db.tables['games'] if g['status'] in ('lobby', 'playing', 'paused')]
                    if active and not params['p_replace_active']: raise api_error('23505')
                    for game in active:
                        game.update(status='completed', ended_reason='replaced')
                        for runtime in db.tables['jumble_runtime']:
                            if runtime['game_id'] == game['id']:
                                runtime['version'] += 1
                                runtime['state'].update(phase='completed', endedReason='replaced')
                    game = {'id': str(uuid4()), 'title': params['p_title'], 'status': 'lobby'}
                    db.tables['games'].append(game)
                    return SimpleNamespace(data=deepcopy(game))
                table = 'jumble_content' if name == 'jumble_save_content' else 'jumble_runtime'
                game = next((g for g in db.tables['games'] if g['id'] == params['p_game']), None)
                row = next((r for r in db.tables[table] if r['game_id'] == params['p_game']), None)
                if not game or (row['version'] if row else 0) != params['p_expected']:
                    return SimpleNamespace(data=False)
                if table == 'jumble_content' and game['status'] not in ('lobby', 'draft'):
                    return SimpleNamespace(data=False)
                if table == 'jumble_runtime' and game['status'] not in ('lobby', 'playing', 'paused'):
                    return SimpleNamespace(data=False)
                if table == 'jumble_runtime' and params.get('p_content_version') is not None:
                    content = next((r for r in db.tables['jumble_content'] if r['game_id'] == game['id']), None)
                    if not content or content['version'] != params['p_content_version']: return SimpleNamespace(data=False)
                value_key = 'document' if table == 'jumble_content' else 'state'
                new_row = {'game_id': game['id'], 'version': params['p_expected'] + 1, value_key: deepcopy(params['p_document' if table == 'jumble_content' else 'p_state'])}
                if row: row.update(new_row)
                else: db.tables[table].append(new_row)
                if table == 'jumble_runtime': game.update(status=params['p_status'], current_round=params['p_round'], current_question=params['p_question'])
                return SimpleNamespace(data=True)
        return Call()


class Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.filters = []
        self.operation, self.payload, self.maximum = "select", None, None
        self.columns = "*"

    def select(self, columns="*", **kwargs):
        self.columns = columns
        return self

    def eq(self, field, value):
        self.filters.append(lambda row: row.get(field) == value)
        return self

    def in_(self, field, values):
        self.filters.append(lambda row: row.get(field) in values)
        return self

    def limit(self, maximum):
        self.maximum = maximum
        return self

    def insert(self, payload):
        self.operation, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.operation, self.payload = "update", payload
        return self

    def execute(self):
        if self.db.fault:
            raise self.db.fault
        rows = self.db.tables[self.table]
        if self.operation == "insert":
            if self.payload.get("name") == self.db.insert_fail_name and self.db.insert_fail_name:
                raise RuntimeError("do not expose private database details")
            row = {"id": str(uuid4()), **self.payload}
            rows.append(row)
            if self.table == "players" and self.db.race:
                self.db.race = False
                raise api_error("23505")
            return SimpleNamespace(data=[deepcopy(row)])
        selected = [r for r in rows if all(f(r) for f in self.filters)]
        if self.maximum is not None:
            selected = selected[:self.maximum]
        if self.operation == "update":
            for row in selected:
                row.update(self.payload)
        data = deepcopy(selected)
        if self.operation == "select" and self.columns != "*":
            data = [{column: row.get(column) for column in self.columns.split(",")} for row in data]
        return SimpleNamespace(data=data)
