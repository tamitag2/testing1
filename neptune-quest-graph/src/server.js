import http from "node:http";
import { graph } from "./graph.js";

const json = (response, status, body) => {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
};

async function body(request) {
  let raw = "";
  for await (const chunk of request) {
    raw += chunk;
    if (raw.length > 10_000) throw new Error("Request body too large");
  }
  return JSON.parse(raw || "{}");
}

export async function handle(request, response) {
  try {
    const url = new URL(request.url, "http://localhost");
    let match;

    if (request.method === "GET" && url.pathname === "/health") return json(response, 200, { ok: true });
    if (request.method === "GET" && url.pathname === "/quests/next") return json(response, 200, await graph.next());
    if (request.method === "GET" && (match = url.pathname.match(/^\/quests\/([^/]+)\/impact$/))) {
      return json(response, 200, await graph.impact(decodeURIComponent(match[1])));
    }
    if (request.method === "POST" && url.pathname === "/quests") {
      const quest = await body(request);
      if (!quest.id?.trim() || !quest.title?.trim()) return json(response, 400, { error: "id and title are required" });
      return json(response, 201, await graph.addQuest({ id: quest.id.trim(), title: quest.title.trim() }));
    }
    if (request.method === "POST" && (match = url.pathname.match(/^\/quests\/([^/]+)\/requires\/([^/]+)$/))) {
      await graph.require(decodeURIComponent(match[1]), decodeURIComponent(match[2]));
      return json(response, 204, null);
    }
    if (request.method === "POST" && (match = url.pathname.match(/^\/quests\/([^/]+)\/complete$/))) {
      return json(response, 200, await graph.complete(decodeURIComponent(match[1])));
    }
    return json(response, 404, { error: "not found" });
  } catch (error) {
    return json(response, error instanceof SyntaxError ? 400 : 500, { error: error.message });
  }
}

if (process.env.NODE_ENV !== "test") {
  http.createServer(handle).listen(Number(process.env.PORT ?? 3001), "0.0.0.0", () => {
    console.log(`Quest graph listening on :${process.env.PORT ?? 3001}`);
  });
}
