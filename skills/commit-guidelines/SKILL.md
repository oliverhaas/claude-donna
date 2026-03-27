---
name: commit-guidelines
description: Conventional commit message format and guidelines. Use when creating commits or writing commit messages.
user-invocable: false
---
 # Commit Message Guidelines

When creating commit messages, follow these conventions:

- Follow mostly the Conventional Commits specification (https://www.conventionalcommits.org/)
- Format: `<type>[optional scope]: <description>`
- Example: `feat(products): add endpoint for bulk price update`
- Example: `fix: correct calculation for shipping costs`
- Example: `refactor: simplify login view logic`
- Example: `docs: update setup instructions`
- Example: `perf(products): reduce N+1 queries in product list`
- Example: `ai: improved cursor rule for unit tests`
- Example: `test(merchants): add unit tests for merchant model`
- Example: `chore(deps): update django to 4.2.1`
- Keep commit messages rather brief
- No fill words
- No long descriptions
- Use type `feat` for actually user-facing feature additions
- Use type `fix` for actual bug fixes
- Use type `perf` for performance improvements
- Use type `ai` for anything regarding ai rules, instructions, or commands
- Tags and version bumps will only happen according to `feat` and `fix`, so please keep in mind to use the commit types properly
- **Do NOT add** "Co-Authored-By" or "Generated with AI" footers to commit messages, *especially* if you did not do the implementation and were just in charge of running the tests and finishing the commit workflow

---
