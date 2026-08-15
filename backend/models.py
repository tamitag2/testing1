from pydantic import BaseModel, Field, field_validator


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        if not (value := value.strip()):
            raise ValueError("title must not be blank")
        return value


class TodoUpdate(BaseModel):
    completed: bool


class Todo(BaseModel):
    id: str
    title: str
    completed: bool
    created_at: str


class TodoPage(BaseModel):
    items: list[Todo]
    page_size: int
    next_cursor: str | None
