---
description: Validate the build and push changes to git
---
This workflow ensures that the code follows linting rules and builds successfully before committing and pushing to the repository.

1. Navigate to the frontend directory.
2. Run `npm run lint`.
   - If there are errors, fix them before proceeding.
3. Run `npm run build`.
   - If there are errors, fix them before proceeding.
4. Show a summary of changes to the USER.
5. Stage and commit changes using Conventional Commits (e.g., `feat: ...`, `fix: ...`).
// turbo
6. Push to the current remote branch: `git push origin $(git branch --show-current)`.
