# Neptune Quest Graph

A tiny backend that treats work as a dependency graph. It finds quests that are
currently unblocked and shows every downstream quest affected by a delay.

Amazon Neptune does not ship a local emulator. This app uses Apache TinkerPop
Gremlin Server in Docker, exercising the Gremlin API and graph model used by
Neptune without contacting AWS.

## Run

```bash
docker compose up --build
```

The API listens on `http://localhost:3001` and the local graph on port `8182`.

```bash
curl -X POST localhost:3001/quests -H 'content-type: application/json' -d '{"id":"map","title":"Draw the dungeon map"}'
curl -X POST localhost:3001/quests -H 'content-type: application/json' -d '{"id":"dragon","title":"Defeat the dragon"}'
curl -X POST localhost:3001/quests/dragon/requires/map
curl localhost:3001/quests/next
curl localhost:3001/quests/map/impact
curl -X POST localhost:3001/quests/map/complete
```

Run the focused checks with `npm test` from this directory.
