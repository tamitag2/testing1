from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from backend.app import app, get_table


class Batch:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def delete_item(self, Key):
        self.db.delete_item(Key=Key)


class FakeTable:
    def __init__(self):
        self.items = {}
        self.query_calls = []

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        return {"Items": list(self.items.values())[: kwargs["Limit"]]}

    def put_item(self, Item):
        self.items[Item["id"]] = Item

    def update_item(self, Key, ExpressionAttributeValues, **_):
        item = self.items[Key["id"]]
        item["completed"] = ExpressionAttributeValues[":completed"]
        return {"Attributes": item}

    def delete_item(self, Key):
        self.items.pop(Key["id"], None)

    def batch_writer(self):
        return Batch(self)


def test_todo_flow():
    db = FakeTable()
    app.dependency_overrides[get_table] = lambda: db
    client = TestClient(app)
    assert client.post("/api/todos", json={"title": "   "}).status_code == 422

    created = client.post("/api/todos", json={"title": " Ship it "})
    assert created.status_code == 201
    todo = created.json()
    assert todo["title"] == "Ship it"

    page = client.get(
        "/api/todos?page_size=1&completed=false&q=SHIP&sort_by=title&order=desc"
    ).json()
    assert page == {"items": [todo], "page_size": 1, "next_cursor": None}
    query = db.query_calls[-1]
    assert query["IndexName"] == "title-index"
    assert query["Limit"] == 1
    assert query["ScanIndexForward"] is False
    assert "FilterExpression" in query
    assert client.get("/api/todos?cursor=not-base64").status_code == 400
    completed = client.patch(f"/api/todos/{todo['id']}", json={"completed": True})
    assert completed.json()["completed"] is True

    assert client.delete("/api/todos").status_code == 204
    assert client.get("/api/todos").json()["items"] == []
    app.dependency_overrides.clear()


def test_storage_errors_are_mapped_without_leaking_details():
    class FailingTable:
        def query(self, **_):
            raise ClientError(
                {"Error": {"Code": "ThrottlingException", "Message": "secret detail"}},
                "Query",
            )

    app.dependency_overrides[get_table] = FailingTable
    response = TestClient(app).get("/api/todos")
    assert response.status_code == 503
    assert response.json() == {"detail": "Todo storage is temporarily unavailable"}
    app.dependency_overrides.clear()
