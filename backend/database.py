import os
import time

import boto3
from botocore.exceptions import EndpointConnectionError

TABLE_NAME = os.getenv("DYNAMODB_TABLE", "todos")


def connect_table():
    resource = boto3.resource(
        "dynamodb",
        endpoint_url=os.getenv("DYNAMODB_ENDPOINT"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "local"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "local"),
    )
    for attempt in range(20):
        try:
            existing = resource.meta.client.list_tables()["TableNames"]
            if TABLE_NAME not in existing:
                resource.create_table(
                    TableName=TABLE_NAME,
                    KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
                    AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
                    BillingMode="PAY_PER_REQUEST",
                ).wait_until_exists()
            return resource.Table(TABLE_NAME)
        except EndpointConnectionError:
            if attempt == 19:
                raise
            time.sleep(1)


def scan_all(table) -> list[dict]:
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))
    while key := response.get("LastEvaluatedKey"):
        response = table.scan(ExclusiveStartKey=key)
        items.extend(response.get("Items", []))
    return items
