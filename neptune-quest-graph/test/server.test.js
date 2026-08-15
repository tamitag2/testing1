import test from "node:test";
import assert from "node:assert/strict";
import { once } from "node:events";
import http from "node:http";

process.env.NODE_ENV = "test";
const { handle } = await import("../src/server.js");

test("rejects an empty quest before touching the graph", async () => {
  const server = http.createServer(handle).listen(0);
  await once(server, "listening");
  const { port } = server.address();
  const response = await fetch(`http://127.0.0.1:${port}/quests`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ id: " ", title: "Nope" })
  });
  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), { error: "id and title are required" });
  server.close();
});

test("health endpoint is independent of the graph", async () => {
  const server = http.createServer(handle).listen(0);
  await once(server, "listening");
  const { port } = server.address();
  const response = await fetch(`http://127.0.0.1:${port}/health`);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { ok: true });
  server.close();
});
