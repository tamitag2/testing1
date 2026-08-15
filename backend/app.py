from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.database import connect_table, scan_all
from backend.models import Todo, TodoCreate, TodoPage, TodoUpdate

STATIC_DIR = Path(__file__).parent.parent / "static"
table = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global table
    table = connect_table()
    yield


app = FastAPI(title="Today Todo API", lifespan=lifespan)


def get_table():
    return table


Table = Annotated[object, Depends(get_table)]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/todos", response_model=TodoPage)
def list_todos(
    db: Table,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    completed: bool | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    sort_by: Literal["created_at", "title"] = "created_at",
    order: Literal["asc", "desc"] = "asc",
):
    items = scan_all(db)
    if completed is not None:
        items = [item for item in items if item["completed"] is completed]
    if q:
        items = [item for item in items if q.casefold() in item["title"].casefold()]
    items.sort(key=lambda item: item[sort_by].casefold(), reverse=order == "desc")
    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@app.post("/api/todos", response_model=Todo, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate, db: Table):
    item = {
        "id": str(uuid4()),
        "title": payload.title,
        "completed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db.put_item(Item=item)
    return item


@app.patch("/api/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: str, payload: TodoUpdate, db: Table):
    try:
        response = db.update_item(
            Key={"id": todo_id},
            UpdateExpression="SET completed = :completed",
            ExpressionAttributeValues={":completed": payload.completed},
            ConditionExpression="attribute_exists(id)",
            ReturnValues="ALL_NEW",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(status_code=404, detail="Todo not found") from error
        raise
    return response["Attributes"]


@app.delete("/api/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: str, db: Table):
    db.delete_item(Key={"id": todo_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/api/todos", status_code=status.HTTP_204_NO_CONTENT)
def delete_completed(db: Table):
    with db.batch_writer() as batch:
        for item in scan_all(db):
            if item["completed"]:
                batch.delete_item(Key={"id": item["id"]})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets", check_dir=False), name="assets")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
