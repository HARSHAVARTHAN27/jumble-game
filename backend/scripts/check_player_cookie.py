"""Check an existing player's join/restore cookie without printing credentials.

Rejoining restores the existing membership; it can refresh its activity status.
"""
import argparse
import httpx
from app.database import supabase


def check(backend, frontend, player_id):
    players = supabase.from_('players').select('employee_id').eq('id', player_id).execute().data
    if not players:
        raise SystemExit('Existing player not found; no join attempted.')
    employees = supabase.from_('employees').select('name,employee_code').eq('id', players[0]['employee_id']).execute().data
    if not employees:
        raise SystemExit('Existing employee not found; no join attempted.')
    employee = employees[0]
    with httpx.Client(timeout=30, headers={'Origin': frontend}) as client:
        response = client.post(backend.rstrip('/') + '/api/player/join', json={
            'name': employee['name'], 'employee_code': employee['employee_code'],
        })
        print('Existing player rejoin:', response.status_code)
        cookie = response.headers.get('set-cookie', '')
        print('Cookie attributes:', cookie.split(';', 1)[1] if ';' in cookie else 'No cookie returned')
        if response.status_code != 200:
            raise SystemExit('Join failed; no state check attempted.')
        data = response.json()['data']
        restored = client.get(backend.rstrip('/') + '/api/player/state', params={
            'player_id': data['player']['id'], 'game_id': data['game']['id'],
        })
        print('State with returned cookie:', restored.status_code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', required=True)
    parser.add_argument('--frontend', required=True)
    parser.add_argument('--player', required=True)
    args = parser.parse_args()
    check(args.backend, args.frontend, args.player)
