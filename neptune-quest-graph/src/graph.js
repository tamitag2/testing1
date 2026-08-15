import gremlin from "gremlin";

const endpoint = process.env.GREMLIN_URL ?? "ws://localhost:8182/gremlin";
const client = new gremlin.driver.Client(endpoint, { traversalSource: "g" });

function plain(value) {
  if (value instanceof Map) return Object.fromEntries([...value].map(([key, item]) => [key, plain(item)]));
  if (Array.isArray(value)) return value.map(plain);
  return value;
}

export async function query(gremlin, bindings = {}) {
  return (await client.submit(gremlin, bindings)).toArray().map(plain);
}

export const graph = {
  addQuest: ({ id, title }) => query(
    "g.V().has('quest','id',questId).fold().coalesce(unfold(),addV('quest').property('id',questId)).property('title',title).property('done',false).valueMap(true)",
    { questId: id, title }
  ),
  require: (id, prerequisiteId) => query(
    "g.V().has('quest','id',questId).as('q').V().has('quest','id',prerequisiteQuestId).coalesce(__.inE('requires').where(outV().as('q')),addE('requires').from('q')).iterate()",
    { questId: id, prerequisiteQuestId: prerequisiteId }
  ),
  complete: (id) => query(
    "g.V().has('quest','id',questId).property('done',true).valueMap(true)",
    { questId: id }
  ),
  next: () => query(
    "g.V().hasLabel('quest').has('done',false).not(out('requires').has('done',false)).order().by('title').valueMap(true)"
  ),
  impact: (id) => query(
    "g.V().has('quest','id',questId).repeat(in('requires').simplePath()).emit().dedup().valueMap(true)",
    { questId: id }
  )
};
