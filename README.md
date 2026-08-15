# Today

A FastAPI todo list backed by DynamoDB Local.

```bash
docker compose up --build
```

Then open http://localhost:8000.

The todo API supports cursor pagination plus `page_size`, `completed`, `q`,
`sort_by`, and `order` query parameters. Interactive API docs are at
http://localhost:8000/docs.

Run the API tests locally with:

```bash
uv sync
uv run pytest
```

For frontend development:

```bash
cd frontend
pnpm install
pnpm dev
```

Run all local quality checks with:

```bash
uv run ruff check . && uv run ruff format --check . && uv run ty check backend tests
uv run pytest -q
cd frontend && pnpm check
```

GitHub Actions runs the same checks on every push and pull request.

Project-local agent skills are stored in `.agents/skills`:

- `backend-engineer`
- `caveman`
- `dynamodb-query-first-api`
- `frontend-design`
- `fullstack-quality-gates`
- `ponytail`
