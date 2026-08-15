const STORAGE_KEY = "today.todos";

export function addTodo(todos, title, id = crypto.randomUUID()) {
  const cleanTitle = title.trim();
  return cleanTitle ? [...todos, { id, title: cleanTitle, completed: false }] : todos;
}

export const toggleTodo = (todos, id) =>
  todos.map(todo => todo.id === id ? { ...todo, completed: !todo.completed } : todo);

export const deleteTodo = (todos, id) => todos.filter(todo => todo.id !== id);
export const clearCompleted = todos => todos.filter(todo => !todo.completed);
export const visibleTodos = (todos, filter) =>
  todos.filter(todo => filter === "all" || (filter === "completed") === todo.completed);

if (typeof document !== "undefined") {
  const form = document.querySelector("#todo-form");
  const input = document.querySelector("#todo-input");
  const list = document.querySelector("#todo-list");
  const empty = document.querySelector("#empty-state");
  const count = document.querySelector("#count");
  const summary = document.querySelector("#summary");
  const clearButton = document.querySelector("#clear-completed");
  const filterButtons = [...document.querySelectorAll("[data-filter]")];
  let todos = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  let filter = "all";

  const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
  const render = () => {
    const shown = visibleTodos(todos, filter);
    const remaining = todos.filter(todo => !todo.completed).length;
    list.replaceChildren(...shown.map(todo => {
      const item = document.createElement("li");
      item.className = todo.completed ? "done" : "";
      item.innerHTML = `<label><input type="checkbox" ${todo.completed ? "checked" : ""}><span></span></label><button class="delete" aria-label="Delete task">×</button>`;
      item.querySelector("span").textContent = todo.title;
      item.querySelector("input").addEventListener("change", () => update(toggleTodo(todos, todo.id)));
      item.querySelector(".delete").addEventListener("click", () => update(deleteTodo(todos, todo.id)));
      return item;
    }));
    empty.hidden = shown.length > 0;
    count.textContent = `${remaining} task${remaining === 1 ? "" : "s"} left`;
    summary.textContent = remaining ? `${remaining} thing${remaining === 1 ? "" : "s"} waiting for you.` : "Nothing waiting. Enjoy the quiet.";
    clearButton.disabled = !todos.some(todo => todo.completed);
  };
  const update = next => { todos = next; save(); render(); };

  form.addEventListener("submit", event => {
    event.preventDefault();
    const next = addTodo(todos, input.value);
    if (next !== todos) { update(next); input.value = ""; }
    input.focus();
  });
  clearButton.addEventListener("click", () => update(clearCompleted(todos)));
  filterButtons.forEach(button => button.addEventListener("click", () => {
    filter = button.dataset.filter;
    filterButtons.forEach(item => item.classList.toggle("active", item === button));
    render();
  }));
  render();
}
