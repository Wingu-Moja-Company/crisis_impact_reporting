# Contributing

Thank you for your interest in contributing to the Crisis Impact Reporting Platform.

## Workflow

1. Clone the repository (internal team — no fork needed)
2. Follow the [development setup](README.md#development-setup) instructions
3. Make your changes on a feature branch: `git checkout -b feat/your-feature`
4. Ensure tests pass locally (see below)
5. Push to `main` (or merge your branch) — GitHub Actions deploys automatically

**There are no manual deployment steps.** Push to `main` and CI handles everything. See [docs/deployment.md](docs/deployment.md).

## Commit messages

Follow the format: `type(scope): description`

- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Examples: `feat(bot): add what3words validation`, `fix(pipeline): handle missing EXIF data`
- No emojis in commit messages
- No co-author attributions

## Before pushing

```bash
# Python tests
cd functions && pytest tests/ -v
cd bot       && pytest tests/ -v

# Frontend builds (CI will reject broken builds)
cd pwa       && npm run build
cd dashboard && npm run build
```

## Monitoring a deployment

After pushing to `main`:

```bash
gh run list --limit 5          # see recent runs
gh run watch <run-id>          # stream live output
gh run view <run-id> --log-failed   # diagnose failures
```

## Adding a new crisis type / schema

Custom fields are now managed through the Schema Editor in the admin dashboard — no code changes or deployments needed. Log in to the dashboard, open Admin, select a crisis event, click Schema, and publish a new version.

## Adding a new language

The platform supports the 6 official UN languages. To add an additional language:

1. Add a locale file: `pwa/src/i18n/locales/{lang}.json` (copy `en.json` as template)
2. Add the same strings to `bot/i18n/strings.py`
3. Register the language in `pwa/src/i18n/index.ts` and `bot/utils.py`
4. Push to `main` — CI deploys automatically

## Security issues

Please do not open public issues for security vulnerabilities. Contact the maintainers directly.

## Licence

By contributing, you agree that your contributions will be licensed under the MIT Licence.
