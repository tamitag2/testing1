from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal
from uuid import uuid4

from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.database import connect_table, delete_completed_items, query_todos
from backend.models import Todo, TodoCreate, TodoPage, TodoUpdate

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

STATIC_DIR = Path(__file__).parent.parent / "static"
logger = logging.getLogger(__name__)
table: Table | None = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global table
    table = connect_table()
    yield


app = FastAPI(title="Today Todo API", lifespan=lifespan)


@app.exception_handler(EndpointConnectionError)
async def storage_unavailable(
    _: Request, error: EndpointConnectionError
) -> JSONResponse:
    logger.exception("DynamoDB is unavailable", exc_info=error)
    return JSONResponse(
        status_code=503, content={"detail": "Todo storage is unavailable"}
    )


@app.exception_handler(BotoCoreError)
async def storage_client_error(_: Request, error: BotoCoreError) -> JSONResponse:
    logger.exception("DynamoDB client failure", exc_info=error)
    return JSONResponse(
        status_code=503, content={"detail": "Todo storage is unavailable"}
    )


@app.exception_handler(ClientError)
async def storage_service_error(_: Request, error: ClientError) -> JSONResponse:
    code = error.response["Error"]["Code"]
    logger.exception("DynamoDB request failed with %s", code, exc_info=error)
    retryable = code in {
        "InternalServerError",
        "ProvisionedThroughputExceededException",
        "RequestLimitExceeded",
        "ResourceNotFoundException",
        "ThrottlingException",
    }
    return JSONResponse(
        status_code=503 if retryable else 500,
        content={
            "detail": "Todo storage is temporarily unavailable"
            if retryable
            else "Todo storage failed"
        },
    )


def get_table() -> Table:
    if table is None:
        raise RuntimeError("DynamoDB table is not initialized")
    return table


if TYPE_CHECKING:
    TableDependency = Annotated[Table, Depends(get_table)]
else:
    TableDependency = Annotated[object, Depends(get_table)]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/todos", response_model=TodoPage)
def list_todos(
    db: TableDependency,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
    completed: bool | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    sort_by: Literal["created_at", "title"] = "created_at",
    order: Literal["asc", "desc"] = "asc",
) -> TodoPage:
    try:
        return TodoPage.model_validate(
            query_todos(db, page_size, cursor, completed, q, sort_by, order)
        )
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=400, detail="Invalid pagination cursor"
        ) from error


@app.post("/api/todos", response_model=Todo, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate, db: TableDependency) -> Todo:
    item = {
        "id": str(uuid4()),
        "title": payload.title,
        "entity_type": "TODO",
        "title_sort": payload.title.casefold(),
        "title_search": payload.title.casefold(),
        "completed": False,
        "created_at": datetime.now(UTC).isoformat(),
    }
    db.put_item(Item=item)
    return Todo.model_validate(item)


@app.patch("/api/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: str, payload: TodoUpdate, db: TableDependency) -> Todo:
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
    return Todo.model_validate(response["Attributes"])


@app.delete("/api/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: str, db: TableDependency) -> Response:
    db.delete_item(Key={"id": todo_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/api/todos", status_code=status.HTTP_204_NO_CONTENT)
def delete_completed(db: TableDependency) -> Response:
    delete_completed_items(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


app.mount(
    "/assets",
    StaticFiles(directory=STATIC_DIR / "assets", check_dir=False),
    name="assets",
)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
