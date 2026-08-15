import test from "node:test";
import assert from "node:assert/strict";
import { addTodo, toggleTodo, deleteTodo, clearCompleted, visibleTodos } from "./app.js";

test("todo operations", () => {
  const added = addTodo([], "  Ship it  ", "1");
  assert.deepEqual(added, [{ id: "1", title: "Ship it", completed: false }]);
  assert.equal(addTodo(added, "   "), added);

  const completed = toggleTodo(added, "1");
  assert.equal(completed[0].completed, true);
  assert.deepEqual(visibleTodos(completed, "active"), []);
  assert.deepEqual(visibleTodos(completed, "completed"), completed);
  assert.deepEqual(clearCompleted(completed), []);
  assert.deepEqual(deleteTodo(added, "1"), []);
});
