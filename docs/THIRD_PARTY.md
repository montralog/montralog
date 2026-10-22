# Third-party components

Original gateway/UI code, with unmodified Apache-2.0 license text. No external
browser scripts, images, fonts or CDNs are loaded.

Separate upstream dependencies obtained during Docker build/deployment:

| Component | Intended license | Upstream |
|---|---|---|
| Python | PSF | https://www.python.org/psf/license/ |
| Gunicorn | MIT | https://github.com/benoitc/gunicorn |
| psycopg / psycopg-binary | LGPL-3.0; bundled libraries retain their licenses | https://github.com/psycopg/psycopg |
| joserfc | BSD-3-Clause | https://github.com/authlib/joserfc |
| cryptography | Apache-2.0 OR BSD-3-Clause | https://github.com/pyca/cryptography |
| cffi / pycparser | MIT-0 / BSD-3-Clause; verify resolved versions | https://github.com/python-cffi/cffi / https://github.com/eliben/pycparser |
| psutil | BSD-3-Clause | https://github.com/giampaolo/psutil |
| Prometheus | Apache-2.0 | https://github.com/prometheus/prometheus |
| Alertmanager | Apache-2.0 | https://github.com/prometheus/alertmanager |
| OTel Collector/contrib | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-collector-contrib |
| Debian image packages | Multiple | https://www.debian.org/legal/licenses/ |

This direct-component inventory is not an SBOM/license audit. Before redistributing
images, generate an SBOM, verify resolved transitive licenses, retain upstream
license/NOTICE files and scan immutable images.
