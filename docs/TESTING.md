# Tests and release evidence

Run from a source checkout using an isolated Python environment:

```sh
python -m pip install -e ".[server]" -r requirements-dev.txt
python -m unittest discover -s tests -v
node --test tests/test_studio_rendering.cjs
python scripts/functional_review_smoke.py
```

PostgreSQL tests require `MONTRALOG_TEST_DATABASE_URL` pointing to a disposable database named `montralog_test`; they clear its records. Hosted CI creates its own database. Never provide production database credentials.

## Browser acceptance

```sh
cd tests/browser
npm ci
npx playwright install chromium
npm test
```

The browser configuration starts its own loopback server on port 8099, uses a temporary SQLite database and synthetic fixture accounts/events, and refuses to reuse an existing server. It never reads an operator `.env` or database. Chromium runs headlessly. Reports are in `tests/browser/playwright-report`; CI uploads them and the release attaches the report for public review. Fixture passwords and sessions are disposable test data, not production credentials.

The cases assert: rejected login and valid session; profile persistence and logout revocation; saved timeline panel reopening; literal/escaped log rendering and filtering; and viewer restrictions in both UI and API.

## Image and deployment gates

CI verifies Docker context exclusions against the built image, collector/backend configuration and real ingestion. Kubernetes tests use only `kind-montralog-verify`, install SQLite and PostgreSQL profiles, check retained/shared data across restarts and verify the operator-managed encryption Secret.

Security checks include pip-audit, Bandit and the pinned Trivy scanner. `scripts/check_security_report.py` rejects incomplete inventories, unsupported/end-of-life OS scans and every HIGH/CRITICAL finding, including unfixed findings. Unit tests verify that these cases fail closed. The release publishes the exact image archive from the passing scan job, checks its ID/source revision, verifies the native driver/non-root/required-key startup and tests anonymous pull access against the exact manifest digest.

Release assets include the full scan reports, dependency inventory, image digest and checksums. GitHub provenance links the container to its source workflow. Scan success is not a capacity guarantee or independent security certification. Record organization-specific acceptance with the rollout checklist.
