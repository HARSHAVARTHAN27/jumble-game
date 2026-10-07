"""Read-only public deployment diagnostics. Never prints keys or player data."""
import argparse
import re
from urllib.parse import urljoin
import httpx


def check(frontend, backend):
    frontend, backend = frontend.rstrip('/'), backend.rstrip('/')
    with httpx.Client(timeout=45) as client:
        health = client.get(backend + '/health')
        print('Backend health:', health.status_code, health.text[:500])
        html = client.get(frontend).text
        scripts = re.findall(r'src="([^"]+\.js)"', html)
        code = '\n'.join(client.get(urljoin(frontend, path)).text for path in scripts)
        origins = sorted(set(re.findall(r'https?://(?:localhost:[0-9]+|[A-Za-z0-9.-]+\.onrender\.com)', code)))
        print('API origins in deployed frontend:', origins)
        print('Frontend Supabase projects:', sorted(set(re.findall(r'https://[A-Za-z0-9.-]+\.supabase\.co', code))))
        response = client.options(backend + '/api/player/join', headers={
            'Origin': frontend, 'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type',
        })
        print('CORS preflight:', response.status_code)
        print('Allowed frontend:', response.headers.get('access-control-allow-origin'))
        print('Credentials allowed:', response.headers.get('access-control-allow-credentials'))
        print('Frontend /control:', client.get(frontend + '/control').status_code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--frontend', required=True)
    parser.add_argument('--backend', required=True)
    args = parser.parse_args()
    check(args.frontend, args.backend)
