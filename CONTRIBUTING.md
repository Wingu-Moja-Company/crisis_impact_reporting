# Contributing

Thank you for your interest in contributing to the Crisis Impact Reporting Platform.

## Getting started

1. Fork the repository and clone your fork
2. Follow the [development setup](README.md#development-setup) instructions
3. Create a feature branch: `git checkout -b feat/your-feature`
4. Make your changes and ensure tests pass
5. Open a pull request against `main`

## Pull request requirements

- All Python tests must pass: `pytest`
- PWA and dashboard must build: `npm run build`
- New Python code should include unit tests in the appropriate `tests/` directory
- Commit messages should follow the format: `type(scope): description`
  - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
  - Examples: `feat(bot): add what3words validation`, `fix(pipeline): handle missing EXIF data`

## Adding a new crisis schema

To add modular fields for a new crisis type (e.g. tsunami):

1. Create `schemas/tsunami-schema.json` following the pattern in `schemas/flood-schema.json`
2. Include labels in all 6 UN languages: `ar`, `zh`, `en`, `fr`, `ru`, `es`
3. Submit a PR — no code deployment is needed to add a schema

## Adding a new language

The platform supports the 6 official UN languages. To add an additional language:

1. Add a locale file: `pwa/src/i18n/locales/{lang}.json` (copy `en.json` as template)
2. Add the same strings to `bot/i18n/strings.py`
3. Register the language in `pwa/src/i18n/index.ts` and `bot/utils.py`

## Security issues

Please do not open public issues for security vulnerabilities. Contact the maintainers directly.

## Licence

By contributing, you agree that your contributions will be licensed under the MIT Licence.
