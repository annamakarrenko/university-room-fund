const state = {
  user: null,
  buildings: [],
  departments: [],
  rooms: [],
  section: "overview",
  editing: null,
};

const titles = {
  overview: ["Обзор фонда", "Обзор"],
  buildings: ["Корпуса", "Корпуса"],
  rooms: ["Помещения", "Помещения"],
  departments: ["Подразделения", "Подразделения"],
};

const entityConfig = {
  buildings: { singular: "корпус", title: "Корпус", endpoint: "/buildings" },
  rooms: { singular: "помещение", title: "Помещение", endpoint: "/rooms" },
  departments: { singular: "подразделение", title: "Подразделение", endpoint: "/departments" },
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function errorMessage(payload) {
  if (!payload) return "Не удалось выполнить запрос";
  if (typeof payload.detail === "string") {
    const known = {
      "Incorrect username or password": "Неверный логин или пароль",
      "Username already exists": "Такой логин уже занят",
      "Room number already exists in this building": "В этом корпусе уже есть помещение с таким номером",
      "Building contains rooms and cannot be deleted": "Сначала удалите помещения из этого корпуса",
      "Department owns rooms and cannot be deleted": "Сначала перенесите или удалите помещения подразделения",
      "Authentication required": "Сначала войдите в систему",
    };
    return known[payload.detail] || payload.detail;
  }
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg.replace("Value error, ", "")).join(". ");
  }
  return "Проверьте введённые данные";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (response.status === 401 && !path.startsWith("/auth/")) {
    showAuth();
    throw new Error("Сессия завершена. Войдите снова.");
  }
  if (!response.ok) {
    let payload;
    try { payload = await response.json(); } catch { payload = null; }
    throw new Error(errorMessage(payload));
  }
  return response.status === 204 ? null : response.json();
}

function setBusy(form, busy) {
  const button = form.querySelector('button[type="submit"]');
  button.disabled = busy;
  button.dataset.label ||= button.textContent;
  button.textContent = busy ? "Подождите…" : button.dataset.label;
}

function showAuth() {
  $("#app-view").hidden = true;
  $("#auth-view").hidden = false;
  state.user = null;
}

function showApp(user) {
  state.user = user;
  $("#auth-view").hidden = true;
  $("#app-view").hidden = false;
  $("#user-name").textContent = user.display_name;
  $("#user-login").textContent = `@${user.username}`;
  $("#user-avatar").textContent = user.display_name.charAt(0).toUpperCase();
  $("#welcome-name").textContent = user.display_name.split(" ")[0];
}

function switchAuthTab(tab) {
  const register = tab === "register";
  $$(".auth-tab").forEach((button) => button.classList.toggle("is-active", button.dataset.authTab === tab));
  $("#login-form").hidden = register;
  $("#register-form").hidden = !register;
  $("#auth-title").textContent = register ? "Создание аккаунта" : "Вход в систему";
  $("#auth-subtitle").textContent = register ? "Заполните данные для первого входа" : "Введите данные своей учётной записи";
  $("#login-error").textContent = "";
  $("#register-error").textContent = "";
}

async function submitAuth(event, mode) {
  event.preventDefault();
  const form = event.currentTarget;
  const error = $(`#${mode}-error`);
  const data = Object.fromEntries(new FormData(form));
  error.textContent = "";
  setBusy(form, true);
  try {
    const user = await api(`/auth/${mode}`, { method: "POST", body: JSON.stringify(data) });
    showApp(user);
    form.reset();
    await loadData();
  } catch (requestError) {
    error.textContent = requestError.message;
  } finally {
    setBusy(form, false);
  }
}

async function loadData(showSuccess = false) {
  try {
    const [buildings, departments, rooms] = await Promise.all([
      api("/buildings"), api("/departments"), api("/rooms"),
    ]);
    state.buildings = buildings;
    state.departments = departments;
    state.rooms = rooms;
    renderAll();
    if (showSuccess) toast("Данные обновлены");
  } catch (requestError) {
    toast(requestError.message, true);
  }
}

function byId(collection, id) {
  return collection.find((item) => item.id === id);
}

function formatNumber(value, maximumFractionDigits = 1) {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits }).format(value || 0);
}

function renderAll() {
  renderOverview();
  renderBuildings();
  renderRooms();
  renderDepartments();
  applySearch();
}

function renderOverview() {
  const area = state.rooms.reduce((sum, room) => sum + room.area, 0);
  const capacity = state.rooms.reduce((sum, room) => sum + room.capacity, 0);
  $("#stat-buildings").textContent = formatNumber(state.buildings.length, 0);
  $("#stat-rooms").textContent = formatNumber(state.rooms.length, 0);
  $("#stat-area").textContent = formatNumber(area);
  $("#stat-capacity").textContent = formatNumber(capacity, 0);

  const recent = [...state.rooms].sort((a, b) => b.id - a.id).slice(0, 5);
  $("#recent-rooms").innerHTML = recent.length ? recent.map((room) => {
    const building = byId(state.buildings, room.building_id);
    const department = byId(state.departments, room.department_id);
    return `<div class="recent-item"><span class="recent-item__icon">${escapeHtml(room.number)}</span><div><strong>Аудитория ${escapeHtml(room.number)}</strong><small>${escapeHtml(building?.name || "Корпус не найден")} · ${escapeHtml(department?.name || "Без подразделения")}</small></div><span>${formatNumber(room.area)} м²</span></div>`;
  }).join("") : '<div class="empty-cell">Добавьте первое помещение — оно появится здесь</div>';

  const maxRooms = Math.max(1, ...state.buildings.map((building) => state.rooms.filter((room) => room.building_id === building.id).length));
  $("#building-chart").innerHTML = state.buildings.length ? state.buildings.slice(0, 6).map((building) => {
    const count = state.rooms.filter((room) => room.building_id === building.id).length;
    return `<div class="chart-row"><div class="chart-row__meta"><span>${escapeHtml(building.name)}</span><span>${count} помещ.</span></div><div class="chart-track"><div class="chart-fill" style="width:${Math.max(4, count / maxRooms * 100)}%"></div></div></div>`;
  }).join("") : '<div class="empty-cell">Нет данных о корпусах</div>';
}

function actionButtons(type, id) {
  return `<div class="row-actions"><button class="row-action" data-edit="${type}" data-id="${id}" title="Изменить">✎</button><button class="row-action row-action--danger" data-delete="${type}" data-id="${id}" title="Удалить">×</button></div>`;
}

function renderBuildings() {
  $("#building-count").textContent = state.buildings.length;
  $("#buildings-table").innerHTML = state.buildings.length ? state.buildings.map((building) => {
    const count = state.rooms.filter((room) => room.building_id === building.id).length;
    return `<tr><td class="table-primary"><span class="entity-badge">${escapeHtml(building.name)}</span></td><td>${escapeHtml(building.address)}</td><td>${count}</td><td>${actionButtons("buildings", building.id)}</td></tr>`;
  }).join("") : emptyRow(4, "Корпуса ещё не добавлены");
}

function renderRooms() {
  $("#room-count").textContent = state.rooms.length;
  $("#rooms-table").innerHTML = state.rooms.length ? state.rooms.map((room) => {
    const building = byId(state.buildings, room.building_id);
    const department = byId(state.departments, room.department_id);
    return `<tr><td class="table-primary"><span class="entity-badge">Ауд. ${escapeHtml(room.number)}</span></td><td>${escapeHtml(building?.name || "—")}</td><td>${escapeHtml(department?.name || "—")}</td><td>${formatNumber(room.area)} м²</td><td>${room.capacity}</td><td>${actionButtons("rooms", room.id)}</td></tr>`;
  }).join("") : emptyRow(6, "Помещения ещё не добавлены");
}

function renderDepartments() {
  $("#department-count").textContent = state.departments.length;
  $("#departments-table").innerHTML = state.departments.length ? state.departments.map((department) => {
    const rooms = state.rooms.filter((room) => room.department_id === department.id);
    const area = rooms.reduce((sum, room) => sum + room.area, 0);
    return `<tr><td class="table-primary"><span class="entity-badge">${escapeHtml(department.name)}</span></td><td>${rooms.length}</td><td>${formatNumber(area)} м²</td><td>${actionButtons("departments", department.id)}</td></tr>`;
  }).join("") : emptyRow(4, "Подразделения ещё не добавлены");
}

function emptyRow(columns, text) {
  return `<tr><td class="empty-cell" colspan="${columns}">${text}</td></tr>`;
}

function goToSection(section) {
  state.section = section;
  $$(".page-section").forEach((node) => { node.hidden = node.id !== `section-${section}`; });
  $$(".nav-item[data-section]").forEach((node) => node.classList.toggle("is-active", node.dataset.section === section));
  $("#page-title").textContent = titles[section][0];
  $("#breadcrumb-current").textContent = titles[section][1];
  $("#add-button").hidden = section === "overview";
  $("#search-input").value = "";
  $("#search-input").disabled = section === "overview";
  $(".sidebar").classList.remove("is-open");
  applySearch();
}

function getEntity(type, id) {
  return state[type].find((item) => item.id === Number(id));
}

function roomOptions(collection, currentId) {
  return collection.map((item) => `<option value="${item.id}" ${item.id === currentId ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("");
}

function openDialog(type, id = null) {
  if (type === "rooms" && (!state.buildings.length || !state.departments.length)) {
    toast("Для помещения сначала добавьте корпус и подразделение", true);
    return;
  }
  const config = entityConfig[type];
  const entity = id ? getEntity(type, id) : null;
  state.editing = { type, id: entity?.id || null };
  $("#dialog-eyebrow").textContent = entity ? "Редактирование записи" : "Новая запись";
  $("#dialog-title").textContent = `${entity ? "Изменить" : "Добавить"} ${config.singular}`;
  $("#dialog-error").textContent = "";

  if (type === "buildings") {
    $("#dialog-fields").innerHTML = `<label class="full"><span>Название корпуса</span><input name="name" maxlength="100" value="${escapeHtml(entity?.name || "")}" placeholder="Например, Главный корпус" required></label><label class="full"><span>Адрес</span><input name="address" maxlength="255" value="${escapeHtml(entity?.address || "")}" placeholder="г. Москва, ул. Университетская, 1" required></label>`;
  } else if (type === "departments") {
    $("#dialog-fields").innerHTML = `<label class="full"><span>Название подразделения</span><input name="name" maxlength="100" value="${escapeHtml(entity?.name || "")}" placeholder="Например, Кафедра информатики" required></label>`;
  } else {
    $("#dialog-fields").innerHTML = `<label><span>Номер</span><input name="number" maxlength="20" value="${escapeHtml(entity?.number || "")}" placeholder="А-101" required></label><label><span>Площадь, м²</span><input name="area" type="number" min="0.1" step="0.1" value="${entity?.area || ""}" placeholder="48.5" required></label><label><span>Вместимость</span><input name="capacity" type="number" min="0" step="1" value="${entity?.capacity ?? ""}" placeholder="30" required></label><label><span>Корпус</span><select name="building_id" required>${roomOptions(state.buildings, entity?.building_id)}</select></label><label class="full"><span>Подразделение</span><select name="department_id" required>${roomOptions(state.departments, entity?.department_id)}</select></label>`;
  }
  $("#entity-dialog").showModal();
}

async function saveEntity(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const { type, id } = state.editing;
  const data = Object.fromEntries(new FormData(form));
  if (type === "rooms") {
    data.area = Number(data.area);
    data.capacity = Number(data.capacity);
    data.building_id = Number(data.building_id);
    data.department_id = Number(data.department_id);
  }
  setBusy(form, true);
  $("#dialog-error").textContent = "";
  try {
    await api(`${entityConfig[type].endpoint}${id ? `/${id}` : ""}`, { method: id ? "PUT" : "POST", body: JSON.stringify(data) });
    $("#entity-dialog").close();
    await loadData();
    toast(`Запись ${id ? "обновлена" : "добавлена"}`);
  } catch (requestError) {
    $("#dialog-error").textContent = requestError.message;
  } finally {
    setBusy(form, false);
  }
}

async function deleteEntity(type, id) {
  const entity = getEntity(type, id);
  const label = entity?.name || entity?.number || "запись";
  if (!window.confirm(`Удалить «${label}»? Это действие нельзя отменить.`)) return;
  try {
    await api(`${entityConfig[type].endpoint}/${id}`, { method: "DELETE" });
    await loadData();
    toast("Запись удалена");
  } catch (requestError) {
    toast(requestError.message, true);
  }
}

function applySearch() {
  if (state.section === "overview") return;
  const query = $("#search-input").value.trim().toLowerCase();
  $$(`#section-${state.section} tbody tr`).forEach((row) => {
    row.hidden = query && !row.textContent.toLowerCase().includes(query);
  });
}

let toastTimer;
function toast(message, isError = false) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.toggle("is-error", isError);
  node.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove("is-visible"), 3200);
}

function bindEvents() {
  $$("[data-auth-tab]").forEach((button) => button.addEventListener("click", () => switchAuthTab(button.dataset.authTab)));
  $$(".password-toggle").forEach((button) => button.addEventListener("click", () => {
    const input = button.previousElementSibling;
    input.type = input.type === "password" ? "text" : "password";
    button.textContent = input.type === "password" ? "Показать" : "Скрыть";
  }));
  $("#login-form").addEventListener("submit", (event) => submitAuth(event, "login"));
  $("#register-form").addEventListener("submit", (event) => submitAuth(event, "register"));
  $$(".nav-item[data-section]").forEach((button) => button.addEventListener("click", () => goToSection(button.dataset.section)));
  $$('[data-go]').forEach((button) => button.addEventListener("click", () => goToSection(button.dataset.go)));
  $("#menu-button").addEventListener("click", () => $(".sidebar").classList.toggle("is-open"));
  $("#add-button").addEventListener("click", () => openDialog(state.section));
  $("#refresh-button").addEventListener("click", () => loadData(true));
  $("#search-input").addEventListener("input", applySearch);
  $("#dialog-cancel").addEventListener("click", () => $("#entity-dialog").close());
  $("#dialog-close").addEventListener("click", () => $("#entity-dialog").close());
  $("#entity-form").addEventListener("submit", saveEntity);
  $("#logout-button").addEventListener("click", async () => {
    try { await api("/auth/logout", { method: "POST" }); } finally { showAuth(); }
  });
  document.addEventListener("click", (event) => {
    const edit = event.target.closest("[data-edit]");
    const remove = event.target.closest("[data-delete]");
    if (edit) openDialog(edit.dataset.edit, Number(edit.dataset.id));
    if (remove) deleteEntity(remove.dataset.delete, Number(remove.dataset.id));
  });
}

async function init() {
  bindEvents();
  try {
    const user = await api("/auth/me");
    showApp(user);
    await loadData();
  } catch {
    showAuth();
  }
}

init();
