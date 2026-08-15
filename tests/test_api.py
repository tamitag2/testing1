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

    def scan(self, **_):
        return {"Items": list(self.items.values())}

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

    page = client.get("/api/todos?page=1&page_size=1&sort_by=title&order=desc").json()
    assert page == {"items": [todo], "page": 1, "page_size": 1, "total": 1, "pages": 1}
    assert client.get("/api/todos?completed=true").json()["items"] == []
    assert client.get("/api/todos?q=SHIP").json()["items"] == [todo]
    completed = client.patch(f"/api/todos/{todo['id']}", json={"completed": True})
    assert completed.json()["completed"] is True

    assert client.delete("/api/todos").status_code == 204
    assert client.get("/api/todos").json()["items"] == []
    app.dependency_overrides.clear()
