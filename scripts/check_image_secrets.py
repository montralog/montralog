"""Build the image with disposable private-file sentinels and assert exclusion."""
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
files = ['.env.security-check', 'security-check.key', 'security-check.pem', 'security-check.db']
created = []
try:
    for name in files:
        path = root / name
        with path.open('x', encoding='utf-8') as fixture:
            fixture.write('PUBLIC_TEST_SENTINEL_NOT_A_REAL_CREDENTIAL')
        created.append(path)
    subprocess.run(['docker', 'compose', 'build', 'gateway'], cwd=root, check=True)
    check = 'from pathlib import Path; names=' + repr(files) + '; assert all(not (Path("/app")/name).exists() for name in names); assert Path("/app/.env.example").exists(); print("PASS: private files excluded from built image")'
    subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                    '--entrypoint', 'python', 'ghcr.io/montralog/montralog:0.7.0', '-c', check], check=True)
finally:
    for path in created:
        path.unlink()
