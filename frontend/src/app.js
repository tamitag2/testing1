const form = document.querySelector("#todo-form");
const input = document.querySelector("#todo-input");
const list = document.querySelector("#todo-list");
const empty = document.querySelector("#empty-state");
const count = document.querySelector("#count");
const summary = document.querySelector("#summary");
const errorBox = document.querySelector("#error");
const clearButton = document.querySelector("#clear-completed");
const filterButtons = [...document.querySelectorAll("[data-filter]")];
let todos = [];
let filter = "all";

async function request(path = "", options) {
  const response = await fetch(`/api/todos${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error((await response.json()).detail || "Something went wrong");
  return response.status === 204 ? null : response.json();
}

function render() {
  const shown = todos.filter(todo => filter === "all" || (filter === "completed") === todo.completed);
  const remaining = todos.filter(todo => !todo.completed).length;
  list.replaceChildren(...shown.map(todo => {
    const item = document.createElement("li");
    item.className = todo.completed ? "done" : "";
    item.innerHTML = `<label><input type="checkbox" ${todo.completed ? "checked" : ""}><span></span></label><button class="delete" aria-label="Delete task">×</button>`;
    item.querySelector("span").textContent = todo.title;
    item.querySelector("input").addEventListener("change", () => change(async () => {
      const updated = await request(`/${todo.id}`, { method: "PATCH", body: JSON.stringify({ completed: !todo.completed }) });
      todos = todos.map(item => item.id === updated.id ? updated : item);
    }));
    item.querySelector(".delete").addEventListener("click", () => change(async () => {
      await request(`/${todo.id}`, { method: "DELETE" });
      todos = todos.filter(item => item.id !== todo.id);
    }));
    return item;
  }));
  empty.hidden = shown.length > 0;
  count.textContent = `${remaining} task${remaining === 1 ? "" : "s"} left`;
  summary.textContent = remaining ? `${remaining} thing${remaining === 1 ? "" : "s"} waiting for you.` : "Nothing waiting. Enjoy the quiet.";
  clearButton.disabled = !todos.some(todo => todo.completed);
}

async function change(action) {
  errorBox.hidden = true;
  try {
    await action();
    render();
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  const title = input.value.trim();
  if (!title) return input.focus();
  change(async () => {
    const todo = await request("", { method: "POST", body: JSON.stringify({ title }) });
    todos.push(todo);
    input.value = "";
    input.focus();
  });
});

clearButton.addEventListener("click", () => change(async () => {
  await request("", { method: "DELETE" });
  todos = todos.filter(todo => !todo.completed);
}));

filterButtons.forEach(button => button.addEventListener("click", () => {
  filter = button.dataset.filter;
  filterButtons.forEach(item => item.classList.toggle("active", item === button));
  render();
}));

change(async () => { todos = (await request("?page_size=100")).items; });
