"""Fail packaging when application, image, Python and Helm versions disagree."""
from pathlib import Path
import re
import tomllib
import yaml
root = Path(__file__).resolve().parents[1]
version = re.search(r"VERSION = '([^']+)'", (root/'src/montralog/config.py').read_text()).group(1)
assert version == '0.8.1'
assert tomllib.loads((root/'pyproject.toml').read_text())['project']['version'] == '0.8.1'
chart = yaml.safe_load((root/'deploy/helm/montralog/Chart.yaml').read_text())
assert chart['version'] == '0.8.1' and chart['appVersion'] == version
values = yaml.safe_load((root/'deploy/helm/montralog/values.yaml').read_text())
assert values['image']['tag'] == version
assert values['image']['repository'] == 'ghcr.io/montralog/montralog'
assert values['encryption']['existingSecret']
assert 'org.opencontainers.image.version="'+version+'"' in (root/'Dockerfile').read_text()
assert 'MONTRALOG_ENCRYPTION_REQUIRED=true' in (root/'Dockerfile').read_text()
compose = yaml.safe_load((root/'compose.yaml').read_text())
for service in compose['services'].values():
    if service.get('image', '').startswith('ghcr.io/montralog/montralog:'):
        assert service['image'] == 'ghcr.io/montralog/montralog:' + version
assert (root/'deploy/helm/montralog/README.md').is_file()
assert (root/'deploy/helm/montralog/LICENSE').is_file()
print('PASS: application, Python package, Compose images and Helm versions agree')
