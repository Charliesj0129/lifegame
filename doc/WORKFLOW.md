# Development Workflow & Standards

## 1. Branching Strategy
We follow a simplified Feature Branch workflow.

- **Main Branch**: `main` (Protected, always deployable).
- **Feature Branches**: `feat/<desc>` (e.g., `feat/add-quest-chain`).
- **Bug Fixes**: `fix/<desc>` (e.g., `fix/shop-concurrency`).
- **Refactoring**: `refactor/<desc>` (e.g., `refactor/game-dispatcher`).
- **Docs/Chore**: `docs/<desc>`, `chore/<desc>`.

## 2. Commit Convention
Matches [Conventional Commits](https://www.conventionalcommits.org/).

Format: `<type>(<scope>): <subject>`

**Types**:
- `feat`: New feature.
- `fix`: Bug fix.
- `refactor`: Code change that neither fixes a bug nor adds a feature.
- `test`: Adding missing tests or correcting existing tests.
- `docs`: Documentation only changes.
- `chore`: Changes to build process or auxiliary tools (e.g., task.md, config).

**Examples**:
- `feat(quest): Implement recursive requirement check`
- `fix(shop): Add select_for_update to buy_item`
- `refactor(core): Decouple logic from FastAP`

## 3. Pull Request (PR) Protocol
1.  **Development**: Work on your feature branch.
2.  **Verification**:
    - **Tests**: Ensure tests pass locally (`uv run pytest`).
    - **Linting**: Run linter (`uv run ruff check .`) and formatter (`uv run ruff format . --check`).
3.  **Description**: Generate a PR Description (Markdown) summarizing:
    - **Summary**: What changed?
    - **Type**: Bug/Feature/Docs?
    - **Verification**: How was it tested?
4.  **Review**: User reviews the PR Description and Code Diff.
5.  **Merge**:
    - Standard: **Squash and Merge** (Recommended to keep history linear).
    - Or Merge Commit (if preserving individual commit history is preferred).

## 4. Task Management
- Update `task.md` frequently to reflect progress.
- Mark items as `[/]` (In Progress) and `[x]` (Done).

## 5. CI/CD Standards & Troubleshooting

### Critical Rules
1.  **NO Absolute Paths**: Never use `/home/charlie/...` in tests. Use `os.getcwd()` or generic paths.
2.  **Formatter Mandatory**: CI runs `ruff format --check`. You MUST run `uv run ruff format .` before pushing.
3.  **Mock Safely**: Mock databases/paths with care. Ensure `NamedTemporaryFile` or `tmp_path` are cleaned up correctly.

### Troubleshooting Guide
If CI fails:
1.  **List Runs**: `gh run list --limit 5`
2.  **Watch Logs**: `gh run watch <RUN_ID> --exit-status`
3.  **View Errors**: `gh run view <RUN_ID> --log-failed`

### Emergency Fix Protocol
If `main` is broken:
1.  Create `fix/<issue>` branch.
2.  Apply fix.
3.  Run local verification with CI flags: `TESTING=1 SQLALCHEMY_DATABASE_URI="sqlite+aiosqlite:///:memory:" KUZU_DATABASE_PATH=":memory:" uv run pytest tests/unit`
4.  Merge immediately if local tests pass.

## 6. Enhanced Protocols

### 6.1 Local Guardrails (Pre-commit)

Developers MUST ensure code quality *before* committing.

- **Requirement**: Zero lint errors locally.
- **Tooling**: Use `pre-commit` or run `uv run ruff check --fix && uv run ruff format` manually.
- **Impact**: Prevents "lint nitpick" CI failures.

### 6.2 Test Strategy Segregation

Tests are strictly categorized to optimize CI speed and reliability.

- **Unit Tests (`@pytest.mark.unit`)**:
  - Must be fast (<0.1s).
  - Must NOT touch disk/network/DB (use mocks).
  - CI Job: `Run Unit Tests` (Runs on every push).
- **Integration Tests (`@pytest.mark.integration`)**:
  - Can touch DB/Docker.
  - CI Job: `Run Integration Tests` (Runs on PR merge or nightly).

### 6.3 Dependency Hygiene

We stop "It works on my machine" bugs by enforcing strict versioning.

- **Lockfile**: `uv.lock` is the source of truth.
- **CI Command**: MUST use `uv sync --locked`.
- **Update Protocol**: Explicitly run `uv lock --upgrade` to update dependencies, do not let CI auto-resolve new versions.
