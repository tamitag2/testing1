interface Todo {
  id: string;
  title: string;
  completed: boolean;
  created_at: string;
}

interface TodoPage {
  items: Todo[];
}

type Filter = "all" | "active" | "completed";

const form = document.querySelector<HTMLFormElement>("#todo-form")!;
const input = document.querySelector<HTMLInputElement>("#todo-input")!;
const list = document.querySelector<HTMLUListElement>("#todo-list")!;
const empty = document.querySelector<HTMLElement>("#empty-state")!;
const count = document.querySelector<HTMLElement>("#count")!;
const summary = document.querySelector<HTMLElement>("#summary")!;
const errorBox = document.querySelector<HTMLElement>("#error")!;
const clearButton = document.querySelector<HTMLButtonElement>("#clear-completed")!;
const filterButtons = [...document.querySelectorAll<HTMLButtonElement>("[data-filter]")];
let todos: Todo[] = [];
let filter: Filter = "all";

async function request<T>(path = "", options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/todos${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error((await response.json()).detail || "Something went wrong");
  return response.status === 204 ? (undefined as T) : response.json();
}

function render() {
  const shown = todos.filter(todo => filter === "all" || (filter === "completed") === todo.completed);
  const remaining = todos.filter(todo => !todo.completed).length;
  list.replaceChildren(...shown.map(todo => {
    const item = document.createElement("li");
    item.className = todo.completed ? "done" : "";
    item.innerHTML = `<label><input type="checkbox" ${todo.completed ? "checked" : ""}><span></span></label><button class="delete" aria-label="Delete task">×</button>`;
    item.querySelector("span")!.textContent = todo.title;
    item.querySelector("input")!.addEventListener("change", () => change(async () => {
      const updated = await request<Todo>(`/${todo.id}`, { method: "PATCH", body: JSON.stringify({ completed: !todo.completed }) });
      todos = todos.map(item => item.id === updated.id ? updated : item);
    }));
    item.querySelector(".delete")!.addEventListener("click", () => change(async () => {
      await request<void>(`/${todo.id}`, { method: "DELETE" });
      todos = todos.filter(item => item.id !== todo.id);
    }));
    return item;
  }));
  empty.hidden = shown.length > 0;
  count.textContent = `${remaining} task${remaining === 1 ? "" : "s"} left`;
  summary.textContent = remaining ? `${remaining} thing${remaining === 1 ? "" : "s"} waiting for you.` : "Nothing waiting. Enjoy the quiet.";
  clearButton.disabled = !todos.some(todo => todo.completed);
}

async function change(action: () => Promise<void>) {
  errorBox.hidden = true;
  try {
    await action();
    render();
  } catch (error) {
    errorBox.textContent = error instanceof Error ? error.message : "Something went wrong";
    errorBox.hidden = false;
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  const title = input.value.trim();
  if (!title) return input.focus();
  change(async () => {
    const todo = await request<Todo>("", { method: "POST", body: JSON.stringify({ title }) });
    todos.push(todo);
    input.value = "";
    input.focus();
  });
});

clearButton.addEventListener("click", () => change(async () => {
  await request<void>("", { method: "DELETE" });
  todos = todos.filter(todo => !todo.completed);
}));

filterButtons.forEach(button => button.addEventListener("click", () => {
  filter = button.dataset.filter as Filter;
  filterButtons.forEach(item => item.classList.toggle("active", item === button));
  render();
}));

change(async () => { todos = (await request<TodoPage>("?page_size=100")).items; });
