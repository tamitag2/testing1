import base64
import json
import os
import time
from typing import Literal

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import EndpointConnectionError

TABLE_NAME = os.getenv("DYNAMODB_TABLE", "todos")
INDEXES = {
    "created_at-index": "created_at",
    "title-index": "title_sort",
}


def _client():
    return boto3.resource(
        "dynamodb",
        endpoint_url=os.getenv("DYNAMODB_ENDPOINT"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "local"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "local"),
    )


def _index(name: str, sort_key: str) -> dict:
    return {
        "IndexName": name,
        "KeySchema": [
            {"AttributeName": "entity_type", "KeyType": "HASH"},
            {"AttributeName": sort_key, "KeyType": "RANGE"},
        ],
        "Projection": {"ProjectionType": "ALL"},
    }


def _wait_for_index(client, name: str) -> None:
    while True:
        indexes = client.describe_table(TableName=TABLE_NAME)["Table"].get(
            "GlobalSecondaryIndexes", []
        )
        if any(
            index["IndexName"] == name and index["IndexStatus"] == "ACTIVE"
            for index in indexes
        ):
            return
        time.sleep(0.5)


def _backfill_index_fields(table) -> None:
    response = table.scan(ProjectionExpression="id, title")
    while True:
        for item in response.get("Items", []):
            table.update_item(
                Key={"id": item["id"]},
                UpdateExpression="SET entity_type = :type, title_sort = :title, title_search = :title",
                ExpressionAttributeValues={
                    ":type": "TODO",
                    ":title": item["title"].casefold(),
                },
            )
        if "LastEvaluatedKey" not in response:
            return
        response = table.scan(
            ProjectionExpression="id, title",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )


def _ensure_indexes(table) -> None:
    client = table.meta.client
    existing = {
        index["IndexName"]
        for index in client.describe_table(TableName=TABLE_NAME)["Table"].get(
            "GlobalSecondaryIndexes", []
        )
    }
    missing = INDEXES.keys() - existing
    if not missing:
        return
    _backfill_index_fields(table)
    for name in missing:
        sort_key = INDEXES[name]
        client.update_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=[
                {"AttributeName": "entity_type", "AttributeType": "S"},
                {"AttributeName": sort_key, "AttributeType": "S"},
            ],
            GlobalSecondaryIndexUpdates=[{"Create": _index(name, sort_key)}],
        )
        _wait_for_index(client, name)


def connect_table():
    resource = _client()
    for attempt in range(20):
        try:
            if TABLE_NAME not in resource.meta.client.list_tables()["TableNames"]:
                resource.create_table(
                    TableName=TABLE_NAME,
                    KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
                    AttributeDefinitions=[
                        {"AttributeName": "id", "AttributeType": "S"},
                        {"AttributeName": "entity_type", "AttributeType": "S"},
                        {"AttributeName": "created_at", "AttributeType": "S"},
                        {"AttributeName": "title_sort", "AttributeType": "S"},
                    ],
                    GlobalSecondaryIndexes=[
                        _index(name, sort_key) for name, sort_key in INDEXES.items()
                    ],
                    BillingMode="PAY_PER_REQUEST",
                ).wait_until_exists()
            table = resource.Table(TABLE_NAME)
            _ensure_indexes(table)
            return table
        except EndpointConnectionError:
            if attempt == 19:
                raise
            time.sleep(1)


def _decode_cursor(cursor: str | None) -> dict | None:
    if not cursor:
        return None
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid cursor") from error
    if not isinstance(value, dict):
        raise TypeError("Invalid cursor")
    return value


def _encode_cursor(key: dict | None) -> str | None:
    if not key:
        return None
    return base64.urlsafe_b64encode(json.dumps(key).encode()).decode()


def query_todos(
    table,
    page_size: int,
    cursor: str | None,
    completed: bool | None,
    search: str | None,
    sort_by: Literal["created_at", "title"],
    order: Literal["asc", "desc"],
) -> dict:
    filters = None
    if completed is not None:
        filters = Attr("completed").eq(completed)
    if search:
        search_filter = Attr("title_search").contains(search.casefold())
        filters = search_filter if filters is None else filters & search_filter

    query = {
        "IndexName": "title-index" if sort_by == "title" else "created_at-index",
        "KeyConditionExpression": Key("entity_type").eq("TODO"),
        "Limit": page_size,
        "ScanIndexForward": order == "asc",
    }
    if filters is not None:
        query["FilterExpression"] = filters
    if start_key := _decode_cursor(cursor):
        query["ExclusiveStartKey"] = start_key

    response = table.query(**query)
    return {
        "items": response.get("Items", []),
        "page_size": page_size,
        "next_cursor": _encode_cursor(response.get("LastEvaluatedKey")),
    }


def delete_completed_items(table) -> None:
    cursor = None
    with table.batch_writer() as batch:
        while True:
            page = query_todos(table, 100, cursor, True, None, "created_at", "asc")
            for item in page["items"]:
                batch.delete_item(Key={"id": item["id"]})
            if not (cursor := page["next_cursor"]):
                return
