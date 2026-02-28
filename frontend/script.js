let isLoginMode = true;
let TOKEN = localStorage.getItem("token");
let ROLE = localStorage.getItem("role") || "student";
let currentNoteId = null;

window.onload = function() {
    if (!TOKEN) {
        document.getElementById("authOverlay").style.display = "flex";
    } else {
        document.getElementById("authOverlay").style.display = "none";
        const savedName = localStorage.getItem("username");
        if (savedName) document.getElementById("displayUsername").innerText = savedName;
        setupInterfaceByRole();
    }
};

function setupInterfaceByRole() {
    const roleLabel = document.getElementById("roleLabel");
    const sidebarBtnText = document.getElementById("sidebarBtnText");
    const sidebarHeader = document.getElementById("sidebar-header");
    const addBtn = document.getElementById("addBtn");

    if (ROLE === 'teacher') {
        roleLabel.innerText = "| Преподаватель";
        sidebarBtnText.innerText = "Студенты";
        sidebarHeader.innerText = "Список студентов";
        addBtn.style.display = "none";
        fetchStudents();
    } else {
        roleLabel.innerText = "";
        sidebarBtnText.innerText = "Все отчёты";
        sidebarHeader.innerText = "Мои отчёты";
        addBtn.style.display = "inline-block";
        fetchNotes();
    }
}

// аунтефикация

function toggleAuthMode() {
    isLoginMode = !isLoginMode;
    document.getElementById("authTitle").innerText = isLoginMode ? "Вход в Time Report" : "Регистрация";
    document.getElementById("authPrimaryBtn").innerText = isLoginMode ? "Войти" : "Создать аккаунт";
    document.getElementById("authSwitchText").innerHTML = isLoginMode
        ? 'Нет аккаунта? <span onclick="toggleAuthMode()">Зарегистрироваться</span>'
        : 'Уже есть аккаунт? <span onclick="toggleAuthMode()">Войти</span>';

    document.getElementById("teacherCheckWrapper").style.display = isLoginMode ? "none" : "flex";
    document.getElementById("authError").innerText = "";
}

async function submitAuth() {
    const username = document.getElementById("loginUsername").value;
    const password = document.getElementById("loginPassword").value;
    const isTeacher = document.getElementById("isTeacherReg").checked;
    const errorDiv = document.getElementById("authError");

    if (!username || !password) {
        errorDiv.innerText = "Заполните все поля";
        return;
    }

    const endpoint = isLoginMode ? '/login' : '/register';
    const body = { username, password };
    if (!isLoginMode) body.is_teacher = isTeacher;

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const data = await response.json();

        if (response.ok) {
            if (isLoginMode) {
                TOKEN = data.access_token;
                ROLE = data.role;
                localStorage.setItem("token", TOKEN);
                localStorage.setItem("username", username);
                localStorage.setItem("role", ROLE);

                document.getElementById("displayUsername").innerText = username;
                document.getElementById("authOverlay").style.display = "none";
                setupInterfaceByRole();
            } else {
                alert("Регистрация успешна! Войдите в систему.");
                toggleAuthMode();
            }
        } else {
            errorDiv.innerText = data.detail || "Ошибка доступа";
        }
    } catch (err) {
        errorDiv.innerText = "Сервер недоступен";
        console.error(err);
    }
}

function logout() {
    localStorage.clear();
    location.reload();
}

// сайдбар

function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const icon = document.getElementById("toggle-icon");
    sidebar.classList.toggle("collapsed");
    icon.classList.toggle("fa-chevron-right");
    icon.classList.toggle("fa-chevron-left");
}

function ensureSidebarOpen() {
    const sidebar = document.getElementById("sidebar");
    if(sidebar.classList.contains("collapsed")) toggleSidebar();

    if (ROLE === 'teacher') fetchStudents();
    else fetchNotes();
}

function openModal() { document.getElementById("noteModal").style.display = "flex"; }
function closeModal() { document.getElementById("noteModal").style.display = "none"; }


async function fetchNotes() {
    try {
        const response = await fetch('/notes', { headers: {'Authorization': `Bearer ${TOKEN}`} });
        if (response.status === 401) return logout();
        const notes = await response.json();
        renderTaskList(notes, false);
    } catch (err) { console.error(err); }
}

async function saveNote() {
    const title = document.getElementById("noteTitle").value;
    const content = document.getElementById("noteText").value;
    const fileInput = document.getElementById("noteAttachment");

    if(!title || !content) return alert("Заполните поля!");

    const formData = new FormData();
    formData.append("title", title);
    formData.append("content", content);
    if (fileInput && fileInput.files.length > 0) {
        formData.append("attachment", fileInput.files[0]);
    }

    const response = await fetch('/notes', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${TOKEN}` },
        body: formData
    });

    if(response.ok) {
        closeModal();
        document.getElementById("noteTitle").value = "";
        document.getElementById("noteText").value = "";
        if (fileInput) fileInput.value = "";
        fetchNotes();
    }
}

async function deleteNote(event, id) {
    event.stopPropagation();
    if(!confirm("Удалить отчёт?")) return;
    const response = await fetch(`/notes/${id}`, {
        method: 'DELETE',
        headers: {'Authorization': `Bearer ${TOKEN}`}
    });
    if(response.ok) {
        fetchNotes();
        document.getElementById("view-title").innerText = "Выберите отчёт";
        document.getElementById("view-content").innerText = "Отчёт удален.";
    }
}

// препододователь

async function fetchStudents() {
    try {
        const response = await fetch('/teacher/students', { headers: {'Authorization': `Bearer ${TOKEN}`} });
        if (response.status === 401) return logout();
        const students = await response.json();

        const list = document.getElementById("task-list");
        list.innerHTML = students.map(u => `
            <div class="task-item" onclick="fetchStudentNotes(${u.id}, '${u.username}', this)">
                <span class="task-item-text"><i class="fa-solid fa-user"></i> ${u.username}</span>
                <i class="fa-solid fa-chevron-right" style="font-size: 0.8rem"></i>
            </div>
        `).join("");

        document.getElementById("view-title").innerText = "Студенты";
        document.getElementById("view-content").innerText = "Выберите студента, чтобы увидеть его отчёты.";
        document.getElementById("teacherControls").style.display = "none";
        document.getElementById("status-display").innerHTML = "";
    } catch (err) { console.error(err); }
}

async function fetchStudentNotes(studentId, studentName, element) {
    document.querySelectorAll('.task-item').forEach(i => i.classList.remove('active'));
    if(element) element.classList.add('active');

    try {
        const response = await fetch(`/teacher/students/${studentId}/notes`, { headers: {'Authorization': `Bearer ${TOKEN}`} });
        const notes = await response.json();

        const list = document.getElementById("task-list");
        document.getElementById("sidebar-header").innerText = `Задачи: ${studentName}`;

        let html = `
            <div class="task-item" onclick="fetchStudents(); document.getElementById('sidebar-header').innerText='Список студентов'" style="background: #34495e; color:white;">
                <i class="fa-solid fa-arrow-left"></i> Назад ко всем
            </div>
        `;

        html += notes.length ? notes.map(n => `
            <div class="task-item" onclick="viewNote(${n.id}, this, true)">
                <span class="task-item-text">${n.title}</span>
                ${getStatusBadge(n.status)}
            </div>
        `).join("") : `<div style="padding:20px; text-align:center; color:#777">Нет отчётов</div>`;

        list.innerHTML = html;

    } catch(err) { console.error(err); }
}

async function updateNoteStatus(status) {
    if (!currentNoteId) return;
    try {
        const response = await fetch(`/teacher/notes/${currentNoteId}/status`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${TOKEN}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: status })
        });

        if (response.ok) {
            const statusDiv = document.getElementById("status-display");
            if (status === 'accepted') {
                statusDiv.innerHTML = '<span style="color:var(--success); font-weight:bold; border: 2px solid var(--success); padding: 5px 10px; border-radius: 5px;">✔ Принято</span>';
            } else if (status === 'rejected') {
                statusDiv.innerHTML = '<span style="color:var(--red); font-weight:bold; border: 2px solid var(--red); padding: 5px 10px; border-radius: 5px;">✖ Не принято</span>';
            } else {
                statusDiv.innerHTML = '<span style="color:#f39c12; font-weight:bold; border: 2px solid #f39c12; padding: 5px 10px; border-radius: 5px;">⏳ Проверяется</span>';
            }
            alert("Статус обновлен!");
        }
    } catch (err) {
        alert("Ошибка обновления статуса");
    }
}


function getStatusBadge(status) {
    if (status === 'accepted' || status === 'verified') return '<span class="status-badge status-verified">Принято</span>';
    if (status === 'rejected') return '<span class="status-badge" style="background: var(--red); color: white;">Не принято</span>';
    return '<span class="status-badge status-unverified">Проверяется</span>';
}

function renderTaskList(notes, isTeacherView) {
    const list = document.getElementById("task-list");
    list.innerHTML = notes.map(n => `
        <div class="task-item" onclick="viewNote(${n.id}, this, ${isTeacherView})">
            <span class="task-item-text">${n.title}</span>
            ${getStatusBadge(n.status)}
            ${!isTeacherView ? `<button class="delete-btn" onclick="deleteNote(event, ${n.id})">Удалить</button>` : ''}
        </div>
    `).join("");
}

async function viewNote(id, element, isTeacherView) {
    document.querySelectorAll('.task-item').forEach(i => {
        if(!i.innerHTML.includes('fa-arrow-left')) i.classList.remove('active');
    });
    if(element) element.classList.add('active');

    currentNoteId = id;

    try {
        const response = await fetch(`/notes/${id}`, { headers: {'Authorization': `Bearer ${TOKEN}`} });

        if(!response.ok) {
            document.getElementById("view-content").innerText = "Ошибка загрузки или нет доступа.";
            return;
        }

        const note = await response.json();

        document.getElementById("view-title").innerText = note.title;
        document.getElementById("view-content").innerText = note.content;

        let existingAttachment = document.getElementById("view-attachment");
        if (existingAttachment) existingAttachment.remove();

        if (note.attachment_url) {
            const attachContainer = document.createElement("div");
            attachContainer.id = "view-attachment";
            attachContainer.style.marginTop = "25px";

            if (note.attachment_url.match(/\.(jpeg|jpg|gif|png)$/i)) {
                attachContainer.innerHTML = `<img src="${note.attachment_url}" style="max-width: 100%; max-height: 400px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">`;
            } else {
                attachContainer.innerHTML = `<a href="${note.attachment_url}" target="_blank" style="display: inline-block; padding: 10px 20px; background: var(--blue); color: white; text-decoration: none; border-radius: 6px; font-weight: bold;"><i class="fa-solid fa-paperclip"></i> Открыть вложение</a>`;
            }

            document.getElementById("view-content").insertAdjacentElement('afterend', attachContainer);
        }

        const statusDiv = document.getElementById("status-display");
        if (note.status === 'accepted' || note.status === 'verified') {
            statusDiv.innerHTML = '<span style="color:var(--success); font-weight:bold; border: 2px solid var(--success); padding: 5px 10px; border-radius: 5px;">✔ Принято</span>';
        } else if (note.status === 'rejected') {
            statusDiv.innerHTML = '<span style="color:var(--red); font-weight:bold; border: 2px solid var(--red); padding: 5px 10px; border-radius: 5px;">✖ Не принято</span>';
        } else {
            statusDiv.innerHTML = '<span style="color:#f39c12; font-weight:bold; border: 2px solid #f39c12; padding: 5px 10px; border-radius: 5px;">⏳ Проверяется</span>';
        }

        const controls = document.getElementById("teacherControls");
        if (ROLE === 'teacher') {
            controls.style.display = "flex";
        } else {
            controls.style.display = "none";
        }
    } catch (e) {
        console.error(e);
    }
}