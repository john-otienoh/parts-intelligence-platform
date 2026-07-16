
#### `CONTRIBUTING.md`

```markdown
# Contributing to AutoIntel

We welcome contributions! Please follow these guidelines to ensure a smooth collaboration.

## Getting Started

1. Fork the repository and clone your fork.
2. Create a virtual environment and install dev dependencies:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r backend/requirements/development.txt
   ```
3. Install pre‑commit hooks: `pre-commit install`

## Development Workflow

- Branch from `develop` for features, `main` for hotfixes.
- Follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`).
- Write tests for new functionality and ensure all tests pass.
- Update documentation if you change any public APIs or architecture.

## Pull Request Process

1. Ensure your branch is up to date with `develop`.
2. Fill out the PR template, including screenshots for UI changes.
3. Obtain at least one review from a CODEOWNER.
4. CI must pass (linting, tests, coverage threshold).
5. Squash and merge after approval.

## Code Style

- **Python**: PEP 8, type hints, formatted with Black and isort.
- **Frontend**: ESLint + Prettier, functional components, TypeScript.

## Reporting Issues

Use the provided issue templates. Include environment details, steps to reproduce, and expected vs actual behavior.

## License

By contributing, you agree that your contributions will be licensed under the project’s MIT License.
```