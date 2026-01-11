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
2.  **Verification**: Ensure tests pass locally (`uv run pytest` or script).
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
