"use strict";

const state = {
    user: null,
    buildings: [],
    rooms: [],
    departments: [],
    authMode: "login",
    currentSection: "overview",
    dialogEntity: null,
    editingId: null,
};

const pageTitles = {
    overview: "Обзор фонда",
    buildings: "Корпуса",
    rooms: "Помещения",
    departments: "Подразделения",
};

const endpoints = {
    building: "/buildings",
    room: "/rooms",
    department: "/departments",
};

const entityNames = {
    building: "корпус",
    room: "помещение",
    department: "подразделение",
};

let toastTimer;

function element(id) {
    return document.getElementById(id);
}

function escapeHtml(value) {
    return String(value ?? "").replace(
        /[&<>"']/g,
        (symbol) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;",
        })[symbol],
    );
}

function errorMessage(data, statusCode) {
    if (Array.isArray(data?.detail)) {
        return data.detail
            .map((error) => error.msg)
            .join(", ");
    }

    if (typeof data?.detail === "string") {
        return data.detail;
    }

    if (typeof data === "string" && data) {
        return data;
    }

    return `Ошибка запроса: ${statusCode}`;
}

async function api(path, options = {}) {
    const headers = {
        ...(options.headers || {}),
    };

    let body = options.body;

    if (body && typeof body !== "string") {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(body);
    }

    const response = await fetch(path, {
        ...options,
        headers,
        body,
        credentials: "same-origin",
    });

    let data = null;

    if (response.status !== 204) {
        const contentType =
            response.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
            data = await response.json();
        } else {
            data = await response.text();
        }
    }

    if (!response.ok) {
        const requestError = new Error(
            errorMessage(data, response.status),
        );

        requestError.status = response.status;
        throw requestError;
    }

    return data;
}

function showToast(message, isError = false) {
    const toast = element("toast");

    clearTimeout(toastTimer);

    toast.textContent = message;
    toast.classList.toggle("error", isError);
    toast.hidden = false;

    toastTimer = setTimeout(() => {
        toast.hidden = true;
    }, 3500);
}

function showAuth() {
    state.user = null;

    element("app-view").hidden = true;
    element("auth-view").hidden = false;

    element("auth-form").reset();
    element("auth-error").hidden = true;
}

async function showApplication(user) {
    state.user = user;

    element("auth-view").hidden = true;
    element("app-view").hidden = false;

    const username = user.username;

    element("profile-name").textContent = username;
    element("profile-login").textContent = `@${username}`;
    element("welcome-name").textContent = username;
    element("profile-letter").textContent =
        username.charAt(0).toUpperCase();

    try {
        await loadData();
        showSection("overview");
    } catch (error) {
        if (error.status === 401) {
            showAuth();
            return;
        }

        showToast(error.message, true);
    }
}

function setAuthMode(mode) {
    state.authMode = mode;

    document
        .querySelectorAll("[data-auth-mode]")
        .forEach((button) => {
            button.classList.toggle(
                "active",
                button.dataset.authMode === mode,
            );
        });

    const isLogin = mode === "login";

    element("auth-title").textContent = isLogin
        ? "Вход в систему"
        : "Создание аккаунта";

    element("auth-description").textContent = isLogin
        ? "Введите данные своей учётной записи"
        : "Придумайте логин и пароль для входа";

    element("auth-submit-text").textContent = isLogin
        ? "Войти в систему"
        : "Зарегистрироваться";

    element("auth-error").hidden = true;
}

async function handleAuthSubmit(event) {
    event.preventDefault();

    const username = element("username").value.trim();
    const password = element("password").value;
    const submitButton =
        event.currentTarget.querySelector("button[type='submit']");
    const errorBox = element("auth-error");

    errorBox.hidden = true;
    submitButton.disabled = true;

    try {
        const user = await api(
            state.authMode === "login"
                ? "/auth/login"
                : "/auth/register",
            {
                method: "POST",
                body: {
                    username,
                    password,
                },
            },
        );

        await showApplication(user);
    } catch (error) {
        errorBox.textContent = error.message;
        errorBox.hidden = false;
    } finally {
        submitButton.disabled = false;
    }
}

async function checkSession() {
    try {
        const user = await api("/auth/me");
        await showApplication(user);
    } catch {
        showAuth();
    }
}

async function loadData() {
    const [buildings, departments, rooms] =
        await Promise.all([
            api("/buildings"),
            api("/departments"),
            api("/rooms"),
        ]);

    state.buildings = buildings;
    state.departments = departments;
    state.rooms = rooms;

    renderDashboard();
    renderTables();
}

function buildingName(id) {
    return (
        state.buildings.find(
            (building) => building.id === id,
        )?.name || `Корпус #${id}`
    );
}

function departmentName(id) {
    return (
        state.departments.find(
            (department) => department.id === id,
        )?.name || `Подразделение #${id}`
    );
}

function formatNumber(value) {
    return new Intl.NumberFormat("ru-RU", {
        maximumFractionDigits: 1,
    }).format(Number(value) || 0);
}

function renderDashboard() {
    const totalArea = state.rooms.reduce(
        (sum, room) => sum + Number(room.area),
        0,
    );

    const totalCapacity = state.rooms.reduce(
        (sum, room) => sum + Number(room.capacity),
        0,
    );

    element("buildings-count").textContent =
        state.buildings.length;

    element("rooms-count").textContent =
        state.rooms.length;

    element("total-area").textContent =
        formatNumber(totalArea);

    element("total-capacity").textContent =
        formatNumber(totalCapacity);

    renderRecentRooms();
    renderBuildingStructure();
}

function renderRecentRooms() {
    const container = element("recent-rooms");

    const rooms = [...state.rooms]
        .sort((first, second) => second.id - first.id)
        .slice(0, 5);

    if (rooms.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                Помещения пока не добавлены
            </div>
        `;
        return;
    }

    container.innerHTML = rooms
        .map(
            (room) => `
                <div class="recent-item">
                    <span class="room-number">
                        ${escapeHtml(room.number)}
                    </span>

                    <div>
                        <strong>
                            Аудитория ${escapeHtml(room.number)}
                        </strong>
                        <small>
                            ${escapeHtml(buildingName(room.building_id))}
                            ·
                            ${escapeHtml(
                                departmentName(room.department_id),
                            )}
                        </small>
                    </div>

                    <span class="recent-area">
                        ${formatNumber(room.area)} м²
                    </span>
                </div>
            `,
        )
        .join("");
}

function renderBuildingStructure() {
    const container = element("building-structure");

    if (state.buildings.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                Корпуса пока не добавлены
            </div>
        `;
        return;
    }

    const structures = state.buildings.map((building) => ({
        building,
        count: state.rooms.filter(
            (room) => room.building_id === building.id,
        ).length,
    }));

    const maximum = Math.max(
        1,
        ...structures.map((item) => item.count),
    );

    container.innerHTML = structures
        .map((item) => {
            const percentage =
                (item.count / maximum) * 100;

            return `
                <div class="structure-item">
                    <div class="structure-row">
                        <strong>
                            ${escapeHtml(item.building.name)}
                        </strong>
                        <span>
                            ${item.count} помещ.
                        </span>
                    </div>

                    <div class="progress-track">
                        <div
                            class="progress-value"
                            style="width: ${percentage}%"
                        ></div>
                    </div>
                </div>
            `;
        })
        .join("");
}

function emptyRow(columns, message) {
    return `
        <tr>
            <td colspan="${columns}">
                <div class="empty-state">
                    ${escapeHtml(message)}
                </div>
            </td>
        </tr>
    `;
}

function actionButtons(entity, id) {
    return `
        <div class="action-buttons">
            <button
                class="edit-button"
                data-edit="${entity}"
                data-id="${id}"
                type="button"
            >
                Изменить
            </button>

            <button
                class="delete-button"
                data-delete="${entity}"
                data-id="${id}"
                type="button"
            >
                Удалить
            </button>
        </div>
    `;
}

function renderTables() {
    const search =
        element("search-input").value.trim().toLowerCase();

    const buildings = state.buildings.filter((building) =>
        `${building.name} ${building.address}`
            .toLowerCase()
            .includes(search),
    );

    const departments = state.departments.filter(
        (department) =>
            department.name.toLowerCase().includes(search),
    );

    const rooms = state.rooms.filter((room) =>
        [
            room.number,
            room.area,
            room.capacity,
            buildingName(room.building_id),
            departmentName(room.department_id),
        ]
            .join(" ")
            .toLowerCase()
            .includes(search),
    );

    element("buildings-table").innerHTML =
        buildings.length === 0
            ? emptyRow(4, "Корпуса не найдены")
            : buildings
                  .map(
                      (building) => `
                        <tr>
                            <td>${building.id}</td>
                            <td>
                                <strong>
                                    ${escapeHtml(building.name)}
                                </strong>
                            </td>
                            <td>
                                ${escapeHtml(building.address)}
                            </td>
                            <td>
                                ${actionButtons(
                                    "building",
                                    building.id,
                                )}
                            </td>
                        </tr>
                    `,
                  )
                  .join("");

    element("departments-table").innerHTML =
        departments.length === 0
            ? emptyRow(3, "Подразделения не найдены")
            : departments
                  .map(
                      (department) => `
                        <tr>
                            <td>${department.id}</td>
                            <td>
                                <strong>
                                    ${escapeHtml(department.name)}
                                </strong>
                            </td>
                            <td>
                                ${actionButtons(
                                    "department",
                                    department.id,
                                )}
                            </td>
                        </tr>
                    `,
                  )
                  .join("");

    element("rooms-table").innerHTML =
        rooms.length === 0
            ? emptyRow(7, "Помещения не найдены")
            : rooms
                  .map(
                      (room) => `
                        <tr>
                            <td>${room.id}</td>
                            <td>
                                <strong>
                                    ${escapeHtml(room.number)}
                                </strong>
                            </td>
                            <td>
                                ${escapeHtml(
                                    buildingName(room.building_id),
                                )}
                            </td>
                            <td>
                                ${escapeHtml(
                                    departmentName(
                                        room.department_id,
                                    ),
                                )}
                            </td>
                            <td>
                                ${formatNumber(room.area)} м²
                            </td>
                            <td>${room.capacity}</td>
                            <td>
                                ${actionButtons(
                                    "room",
                                    room.id,
                                )}
                            </td>
                        </tr>
                    `,
                  )
                  .join("");
}

function showSection(section) {
    state.currentSection = section;

    document
        .querySelectorAll(".content-section")
        .forEach((contentSection) => {
            const isCurrent =
                contentSection.id === `${section}-section`;

            contentSection.hidden = !isCurrent;
            contentSection.classList.toggle(
                "active",
                isCurrent,
            );
        });

    document
        .querySelectorAll(".nav-button")
        .forEach((button) => {
            button.classList.toggle(
                "active",
                button.dataset.section === section,
            );
        });

    element("page-title").textContent =
        pageTitles[section];

    element("search-input").hidden =
        section === "overview";

    element("search-input").value = "";

    renderTables();
}

function findRecord(entity, id) {
    const collection = {
        building: state.buildings,
        room: state.rooms,
        department: state.departments,
    }[entity];

    return collection.find((record) => record.id === id);
}

function optionMarkup(items, selectedId) {
    return items
        .map(
            (item) => `
                <option
                    value="${item.id}"
                    ${item.id === selectedId ? "selected" : ""}
                >
                    ${escapeHtml(item.name)}
                </option>
            `,
        )
        .join("");
}

function openDialog(entity, id = null) {
    if (
        entity === "room" &&
        (
            state.buildings.length === 0 ||
            state.departments.length === 0
        )
    ) {
        showToast(
            "Сначала добавьте хотя бы один корпус и подразделение",
            true,
        );
        return;
    }

    state.dialogEntity = entity;
    state.editingId = id;

    const record =
        id === null ? null : findRecord(entity, id);

    element("dialog-title").textContent =
        id === null
            ? `Новое ${entityNames[entity]}`
            : `Изменить ${entityNames[entity]}`;

    const fields = element("dialog-fields");

    if (entity === "building") {
        fields.innerHTML = `
            <label>
                Название корпуса
                <input
                    name="name"
                    type="text"
                    maxlength="100"
                    value="${escapeHtml(record?.name || "")}"
                    required
                >
            </label>

            <label>
                Адрес
                <input
                    name="address"
                    type="text"
                    maxlength="255"
                    value="${escapeHtml(record?.address || "")}"
                    required
                >
            </label>
        `;
    }

    if (entity === "department") {
        fields.innerHTML = `
            <label>
                Название подразделения
                <input
                    name="name"
                    type="text"
                    maxlength="100"
                    value="${escapeHtml(record?.name || "")}"
                    required
                >
            </label>
        `;
    }

    if (entity === "room") {
        fields.innerHTML = `
            <label>
                Номер помещения
                <input
                    name="number"
                    type="text"
                    maxlength="20"
                    value="${escapeHtml(record?.number || "")}"
                    required
                >
            </label>

            <label>
                Площадь, м²
                <input
                    name="area"
                    type="number"
                    min="0.1"
                    step="0.1"
                    value="${record?.area ?? ""}"
                    required
                >
            </label>

            <label>
                Вместимость
                <input
                    name="capacity"
                    type="number"
                    min="0"
                    step="1"
                    value="${record?.capacity ?? ""}"
                    required
                >
            </label>

            <label>
                Корпус
                <select name="building_id" required>
                    ${optionMarkup(
                        state.buildings,
                        record?.building_id,
                    )}
                </select>
            </label>

            <label>
                Подразделение
                <select name="department_id" required>
                    ${optionMarkup(
                        state.departments,
                        record?.department_id,
                    )}
                </select>
            </label>
        `;
    }

    element("dialog-error").hidden = true;
    element("record-dialog").showModal();
}

function formPayload(entity, formData) {
    if (entity === "building") {
        return {
            name: formData.get("name").trim(),
            address: formData.get("address").trim(),
        };
    }

    if (entity === "department") {
        return {
            name: formData.get("name").trim(),
        };
    }

    return {
        number: formData.get("number").trim(),
        area: Number(formData.get("area")),
        capacity: Number(formData.get("capacity")),
        building_id: Number(formData.get("building_id")),
        department_id: Number(
            formData.get("department_id"),
        ),
    };
}

async function saveRecord(event) {
    event.preventDefault();

    const errorBox = element("dialog-error");
    const formData = new FormData(event.currentTarget);
    const payload = formPayload(
        state.dialogEntity,
        formData,
    );

    const basePath = endpoints[state.dialogEntity];
    const path =
        state.editingId === null
            ? basePath
            : `${basePath}/${state.editingId}`;

    errorBox.hidden = true;

    try {
        await api(path, {
            method:
                state.editingId === null
                    ? "POST"
                    : "PUT",
            body: payload,
        });

        element("record-dialog").close();

        await loadData();

        showToast(
            state.editingId === null
                ? "Запись успешно добавлена"
                : "Изменения сохранены",
        );
    } catch (error) {
        errorBox.textContent = error.message;
        errorBox.hidden = false;
    }
}

async function deleteRecord(entity, id) {
    const record = findRecord(entity, id);

    const recordName =
        record?.name ||
        record?.number ||
        `#${id}`;

    const confirmed = window.confirm(
        `Удалить ${entityNames[entity]} «${recordName}»?`,
    );

    if (!confirmed) {
        return;
    }

    try {
        await api(`${endpoints[entity]}/${id}`, {
            method: "DELETE",
        });

        await loadData();
        showToast("Запись удалена");
    } catch (error) {
        showToast(error.message, true);
    }
}

function bindEvents() {
    document
        .querySelectorAll("[data-auth-mode]")
        .forEach((button) => {
            button.addEventListener("click", () => {
                setAuthMode(button.dataset.authMode);
            });
        });

    element("auth-form").addEventListener(
        "submit",
        handleAuthSubmit,
    );

    document
        .querySelectorAll(".nav-button")
        .forEach((button) => {
            button.addEventListener("click", () => {
                showSection(button.dataset.section);
            });
        });

    document
        .querySelectorAll("[data-open-section]")
        .forEach((button) => {
            button.addEventListener("click", () => {
                showSection(button.dataset.openSection);
            });
        });

    document
        .querySelectorAll("[data-create]")
        .forEach((button) => {
            button.addEventListener("click", () => {
                openDialog(button.dataset.create);
            });
        });



    document
        .querySelector(".main-content")
        .addEventListener("click", (event) => {
            const editButton =
                event.target.closest("[data-edit]");

            if (editButton) {
                openDialog(
                    editButton.dataset.edit,
                    Number(editButton.dataset.id),
                );
                return;
            }

            const deleteButton =
                event.target.closest("[data-delete]");

            if (deleteButton) {
                deleteRecord(
                    deleteButton.dataset.delete,
                    Number(deleteButton.dataset.id),
                );
            }
        });

    element("record-form").addEventListener(
        "submit",
        saveRecord,
    );

    element("dialog-close").addEventListener(
        "click",
        () => element("record-dialog").close(),
    );

    element("dialog-cancel").addEventListener(
        "click",
        () => element("record-dialog").close(),
    );

    element("refresh-button").addEventListener(
        "click",
        async () => {
            try {
                await loadData();
                showToast("Данные обновлены");
            } catch (error) {
                showToast(error.message, true);
            }
        },
    );

    element("search-input").addEventListener(
        "input",
        renderTables,
    );

    element("logout-button").addEventListener(
        "click",
        async () => {
            try {
                await api("/auth/logout", {
                    method: "POST",
                });
            } finally {
                showAuth();
            }
        },
    );
}

async function initialize() {
    bindEvents();
    setAuthMode("login");
    await checkSession();
}

document.addEventListener(
    "DOMContentLoaded",
    initialize,
);