document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('taskForm');
    const list = document.getElementById('taskList');
    const search = document.getElementById('search');
    const clearBtn = document.getElementById('clearCompleted');
    const toggleAdd = document.getElementById('toggleAddTask');
    const toggleShow = document.getElementById('toggleShowTasks');
    const taskSection = document.getElementById('taskSection');

    toggleAdd.addEventListener('click', () => {
        form.style.display = form.style.display === 'none' ? 'block' : 'none';
    });

    toggleShow.addEventListener('click', () => {
        taskSection.style.display = taskSection.style.display === 'none' ? 'block' : 'none';
        if (taskSection.style.display === 'block') loadTasks();
    });

    async function loadTasks() {
        const res = await fetch('/api/tasks');
        const tasks = await res.json();
        displayTasks(tasks);
    }

    function displayTasks(tasks) {
        list.innerHTML = '';
        const searchTerm = search.value.toLowerCase();
        tasks.forEach(task => {
            if (task.title.toLowerCase().includes(searchTerm)) {
                const li = document.createElement('li');
                li.className = `task-item ${task.priority} ${isOverdue(task.due_date) && !task.done ? 'overdue' : ''}`;
                if (task.done) li.classList.add('completed');
                li.innerHTML = `
                    <div>
                        <input type="checkbox" ${task.done ? 'checked' : ''} onclick="toggleDone(${task.id})">
                        <span class="bullet ${task.priority}"></span>
                        <strong>${task.title}</strong>
                        ${task.category ? ` | ${task.category}` : ''}
                        ${task.due_date ? ` | Due: ${task.due_date}` : ''}
                    </div>
                    <div class="task-actions">
                        <button onclick="editTask(${task.id})">✏️</button>
                        <button onclick="deleteTask(${task.id})">🗑️</button>
                    </div>
                `;
                list.appendChild(li);
            }
        });
    }

    function isOverdue(dateStr) {
        if (!dateStr) return false;
        const today = new Date().toISOString().split('T')[0];
        return dateStr < today;
    }

    form.onsubmit = async e => {
        e.preventDefault();
        const task = {
            title: document.getElementById('title').value,
            due_date: document.getElementById('dueDate').value,
            priority: document.getElementById('priority').value,
            category: document.getElementById('category').value
        };
        await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(task)
        });
        form.reset();
        loadTasks();
    };

    window.toggleDone = async id => {
        const res = await fetch('/api/tasks');
        const tasks = await res.json();
        const task = tasks.find(t => t.id === id);
        if (!task) return;
        task.done = !task.done;
        await fetch(`/api/tasks/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(task)
        });
        loadTasks();
    };

    window.deleteTask = async id => {
        await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
        loadTasks();
    };

    window.editTask = async id => {
        const newTitle = prompt("Edit Task Title:");
        if (!newTitle) return;
        const res = await fetch('/api/tasks');
        const tasks = await res.json();
        const task = tasks.find(t => t.id === id);
        if (!task) return;
        task.title = newTitle;
        await fetch(`/api/tasks/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(task)
        });
        loadTasks();
    };

    search.addEventListener('input', loadTasks);

    clearBtn.addEventListener('click', async () => {
        await fetch('/api/tasks/clear', { method: 'POST' });
        loadTasks();
    });
});
