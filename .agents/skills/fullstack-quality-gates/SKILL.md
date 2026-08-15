---
name: fullstack-quality-gates
description: Add or repair repository-wide linting, formatting checks, static type checking, tests, builds, and matching GitHub Actions using each ecosystem's package manager and current stable tools. Use when creating a repo, adding CI, standardizing quality checks across repos, introducing uv/pnpm tooling, or when code lacks automated lint/type gates.
---

# Full-Stack Quality Gates

Make local commands and CI run the same locked toolchain.

## Workflow

1. Inventory repositories and languages. Do not assume one folder equals one repository.
2. Reuse the existing package managers and lockfiles. Query official registries for current stable versions; lock resolved versions rather than running floating `latest` in CI.
3. Prefer one fast tool per job:
   - Python with `uv`: Ruff lint/format, ty typecheck, existing tests.
   - JavaScript/TypeScript with `pnpm`: Oxlint, TypeScript strict checking, existing tests/build.
4. Run checks immediately. Fix findings in source; do not weaken strictness or add blanket ignores. Exclude only vendored/generated directories.
5. Add concise local `check` commands and document them.
6. Add `.github/workflows/checks.yml` for pushes and pull requests. Use lockfile caching, frozen/locked installs, and the exact local commands.
7. Confirm referenced GitHub Action majors from their official latest releases.
8. Run the whole matrix locally, build containers if present, inspect the diff, then commit.

## Release gate

- Lint, format check, typecheck, tests, and production build all pass.
- CI installs from committed lockfiles.
- CI and local commands match.
- Generated environments, caches, and build output are ignored.
