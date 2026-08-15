# Today

A FastAPI todo list backed by DynamoDB Local.

```bash
docker compose up --build
```

Then open http://localhost:8000.

The todo API supports `page`, `page_size`, `completed`, `q`, `sort_by`, and
`order` query parameters. Interactive API docs are at http://localhost:8000/docs.

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

Project-local agent skills are stored in `.agents/skills`:

- `backend-engineer`
- `caveman`
- `ponytail`

An additional local graph backend lives in [`neptune-quest-graph`](./neptune-quest-graph).
