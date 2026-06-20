const API = '/api';

let allEntries = [];
let editingId  = null;
let deletingId = null;

// ── Utilities ────────────────────────────────────────────────────────────────

function esc(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function authorLabel(a) {
    return a.first_name ? `${a.first_name} ${a.last_name}` : a.last_name;
}

// ── Data loading ─────────────────────────────────────────────────────────────

async function loadEntries() {
    document.getElementById('loadingState').style.display = '';
    document.getElementById('entriesBody').innerHTML = '';
    document.getElementById('emptyState').style.display = 'none';

    try {
        const resp = await fetch(`${API}/entries`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        allEntries = await resp.json();
    } catch (err) {
        document.getElementById('loadingState').textContent = `Failed to load entries: ${err.message}`;
        return;
    }

    document.getElementById('loadingState').style.display = 'none';
    renderTable(applyFilter(allEntries));
}

// ── Filtering ─────────────────────────────────────────────────────────────────

function applyFilter(entries) {
    const q = document.getElementById('searchInput').value.toLowerCase().trim();
    if (!q) return entries;
    return entries.filter(e =>
        (e.title     || '').toLowerCase().includes(q) ||
        (e.bib_key   || '').toLowerCase().includes(q) ||
        (e.bib_type  || '').toLowerCase().includes(q) ||
        String(e.year || '').includes(q) ||
        (e.publisher || '').toLowerCase().includes(q) ||
        (e.journal   || '').toLowerCase().includes(q) ||
        (e.authors   || []).some(a => authorLabel(a).toLowerCase().includes(q))
    );
}

function filterEntries() {
    renderTable(applyFilter(allEntries));
}

// ── Rendering ────────────────────────────────────────────────────────────────

function renderTable(entries) {
    const tbody = document.getElementById('entriesBody');
    const empty = document.getElementById('emptyState');

    document.getElementById('entryCount').textContent =
        `${entries.length} entr${entries.length === 1 ? 'y' : 'ies'}`;

    if (!entries.length) {
        tbody.innerHTML = '';
        empty.style.display = '';
        return;
    }

    empty.style.display = 'none';
    tbody.innerHTML = entries.map(e => {
        const type = (e.bib_type || '').toLowerCase();

        const authorsHtml = (e.authors || []).length
            ? (e.authors || []).map(a => esc(authorLabel(a))).join(', ')
            : '—';

        const venueHtml = esc(e.publisher || e.journal || '—');

        return `<tr>
            <td class="td-key">${esc(e.bib_key)}</td>
            <td><span class="badge ${esc(type)}">${esc(e.bib_type)}</span></td>
            <td class="td-title">${esc(e.title || '—')}</td>
            <td>${e.year || '—'}</td>
            <td class="td-authors">${authorsHtml}</td>
            <td class="td-venue">${venueHtml}</td>
            <td class="actions">
                <button class="btn-icon"     onclick="openEditModal(${e.id})"                            title="Edit">&#9998;</button>
                <button class="btn-icon del" onclick="openDeleteModal(${e.id}, '${esc(e.bib_key)}')"  title="Delete">&#10005;</button>
            </td>
        </tr>`;
    }).join('');
}

// ── Add / Edit modal ─────────────────────────────────────────────────────────

function openAddModal() {
    editingId = null;
    document.getElementById('modalTitle').textContent  = 'Add Entry';
    document.getElementById('submitBtn').textContent   = 'Add';
    document.getElementById('entryForm').reset();
    document.getElementById('bib_key').disabled = false;
    document.getElementById('authorsList').innerHTML = '';
    addAuthorRow();
    document.getElementById('modal').style.display = 'flex';
    document.getElementById('bib_key').focus();
}

function openEditModal(id) {
    const entry = allEntries.find(e => e.id === id);
    if (!entry) return;

    editingId = id;
    document.getElementById('modalTitle').textContent  = 'Edit Entry';
    document.getElementById('submitBtn').textContent   = 'Save';

    document.getElementById('bib_key').value    = entry.bib_key;
    document.getElementById('bib_key').disabled = true;
    document.getElementById('bib_type').value   = entry.bib_type  || '';
    document.getElementById('title').value      = entry.title     || '';
    document.getElementById('year').value       = entry.year      || '';
    document.getElementById('publisher').value  = entry.publisher || '';
    document.getElementById('journal').value    = entry.journal   || '';

    const list = document.getElementById('authorsList');
    list.innerHTML = '';
    const authors = entry.authors || [];
    authors.length ? authors.forEach(a => addAuthorRow(a.first_name, a.last_name))
                   : addAuthorRow();

    document.getElementById('modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

function closeModalOnOverlay(e) {
    if (e.target === document.getElementById('modal')) closeModal();
}

function addAuthorRow(firstName = '', lastName = '') {
    const row = document.createElement('div');
    row.className = 'author-row';
    row.innerHTML = `
        <input type="text" placeholder="First name" value="${esc(firstName)}" class="author-first">
        <input type="text" placeholder="Last name"  value="${esc(lastName)}"  class="author-last">
        <button type="button" class="btn-icon del" onclick="this.parentElement.remove()" title="Remove">&#10005;</button>
    `;
    document.getElementById('authorsList').appendChild(row);
}

async function submitEntry(e) {
    e.preventDefault();

    const authors = [...document.querySelectorAll('#authorsList .author-row')]
        .map(row => ({
            first_name: row.querySelector('.author-first').value.trim(),
            last_name:  row.querySelector('.author-last').value.trim(),
        }))
        .filter(a => a.last_name);

    const payload = {
        bib_key:   document.getElementById('bib_key').value.trim(),
        bib_type:  document.getElementById('bib_type').value,
        title:     document.getElementById('title').value.trim()     || null,
        year:      parseInt(document.getElementById('year').value)   || null,
        publisher: document.getElementById('publisher').value.trim() || null,
        journal:   document.getElementById('journal').value.trim()   || null,
        authors,
    };

    const url    = editingId ? `${API}/entries/${editingId}` : `${API}/entries`;
    const method = editingId ? 'PUT' : 'POST';

    const btn = document.getElementById('submitBtn');
    btn.disabled = true;

    try {
        const resp = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (resp.ok || resp.status === 201) {
            closeModal();
            await loadEntries();
        } else {
            const err = await resp.json().catch(() => ({}));
            alert(err.detail || 'Error saving entry.');
        }
    } finally {
        btn.disabled = false;
    }
}

// ── Delete modal ─────────────────────────────────────────────────────────────

function openDeleteModal(id, key) {
    deletingId = id;
    document.getElementById('deleteMessage').textContent =
        `Are you sure you want to delete "${key}"? This action cannot be undone.`;
    document.getElementById('deleteModal').style.display = 'flex';
}

function closeDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
    deletingId = null;
}

async function confirmDelete() {
    if (!deletingId) return;
    const resp = await fetch(`${API}/entries/${deletingId}`, { method: 'DELETE' });
    if (resp.ok || resp.status === 204) {
        closeDeleteModal();
        await loadEntries();
    } else {
        alert('Error deleting entry.');
    }
}

// ── Keyboard shortcuts ────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        closeModal();
        closeDeleteModal();
    }
});

// ── Init ─────────────────────────────────────────────────────────────────────
loadEntries();


// ── Utilities ────────────────────────────────────────────────────────────────

function esc(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function authorLabel(a) {
    return a.first_name ? `${a.first_name} ${a.last_name}` : a.last_name;
}

// ── Data loading ─────────────────────────────────────────────────────────────

async function loadEntries() {
    document.getElementById('loadingState').style.display = '';
    document.getElementById('entriesBody').innerHTML = '';
    document.getElementById('emptyState').style.display = 'none';

    try {
        const resp = await fetch(`${API}/entries`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        allEntries = await resp.json();
    } catch (err) {
        document.getElementById('loadingState').textContent = `Failed to load entries: ${err.message}`;
        return;
    }

    document.getElementById('loadingState').style.display = 'none';
    renderTable(applyFilter(allEntries));
}

function applyFilter(entries) {
    const q = document.getElementById('searchInput').value.toLowerCase().trim();
    if (!q) return entries;
    return entries.filter(e =>
        (e.title     || '').toLowerCase().includes(q) ||
        (e.bib_key   || '').toLowerCase().includes(q) ||
        (e.bib_type  || '').toLowerCase().includes(q) ||
        String(e.year || '').includes(q) ||
        (e.publisher || '').toLowerCase().includes(q) ||
        (e.journal   || '').toLowerCase().includes(q) ||
        (e.authors   || []).some(a => authorLabel(a).toLowerCase().includes(q))
    );
}

function filterEntries() {
    renderTable(applyFilter(allEntries));
}

// ── Rendering ────────────────────────────────────────────────────────────────

function renderTable(entries) {
    const tbody = document.getElementById('entriesBody');
    const empty = document.getElementById('emptyState');

    document.getElementById('entryCount').textContent =
        `${entries.length} entr${entries.length === 1 ? 'y' : 'ies'}`;

    if (!entries.length) {
        tbody.innerHTML = '';
        empty.style.display = '';
        return;
    }

    empty.style.display = 'none';
    tbody.innerHTML = entries.map(e => {
        const authors = (e.authors || []).map(authorLabel).join('; ');
        const venue   = e.journal || e.publisher || '';
        const type    = (e.bib_type || '').toLowerCase();

        return `<tr>
            <td class="td-key">${esc(e.bib_key)}</td>
            <td><span class="badge ${esc(type)}">${esc(e.bib_type)}</span></td>
            <td class="td-title">${esc(e.title || '—')}</td>
            <td>${e.year || '—'}</td>
            <td class="td-authors">${esc(authors) || '—'}</td>
            <td class="td-venue">${esc(venue) || '—'}</td>
            <td class="actions">
                <button class="btn-icon"     onclick="openEditModal(${e.id})"                           title="Edit">&#9998;</button>
                <button class="btn-icon del" onclick="openDeleteModal(${e.id}, '${esc(e.bib_key)}')" title="Delete">&#10005;</button>
            </td>
        </tr>`;
    }).join('');
}

// ── Add / Edit modal ─────────────────────────────────────────────────────────

function openAddModal() {
    editingId = null;
    document.getElementById('modalTitle').textContent  = 'Add Entry';
    document.getElementById('submitBtn').textContent   = 'Add';
    document.getElementById('entryForm').reset();
    document.getElementById('bib_key').disabled = false;
    document.getElementById('authorsList').innerHTML = '';
    addAuthorRow();
    document.getElementById('modal').style.display = 'flex';
    document.getElementById('bib_key').focus();
}

function openEditModal(id) {
    const entry = allEntries.find(e => e.id === id);
    if (!entry) return;

    editingId = id;
    document.getElementById('modalTitle').textContent  = 'Edit Entry';
    document.getElementById('submitBtn').textContent   = 'Save';

    document.getElementById('bib_key').value    = entry.bib_key;
    document.getElementById('bib_key').disabled = true;
    document.getElementById('bib_type').value   = entry.bib_type  || '';
    document.getElementById('title').value      = entry.title     || '';
    document.getElementById('year').value       = entry.year      || '';
    document.getElementById('publisher').value  = entry.publisher || '';
    document.getElementById('journal').value    = entry.journal   || '';

    const list = document.getElementById('authorsList');
    list.innerHTML = '';
    const authors = entry.authors || [];
    authors.length ? authors.forEach(a => addAuthorRow(a.first_name, a.last_name))
                   : addAuthorRow();

    document.getElementById('modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

function closeModalOnOverlay(e) {
    if (e.target === document.getElementById('modal')) closeModal();
}

function addAuthorRow(firstName = '', lastName = '') {
    const row = document.createElement('div');
    row.className = 'author-row';
    row.innerHTML = `
        <input type="text" placeholder="First name" value="${esc(firstName)}" class="author-first">
        <input type="text" placeholder="Last name"  value="${esc(lastName)}"  class="author-last">
        <button type="button" class="btn-icon del" onclick="this.parentElement.remove()" title="Remove">&#10005;</button>
    `;
    document.getElementById('authorsList').appendChild(row);
}

async function submitEntry(e) {
    e.preventDefault();

    const authors = [...document.querySelectorAll('#authorsList .author-row')]
        .map(row => ({
            first_name: row.querySelector('.author-first').value.trim(),
            last_name:  row.querySelector('.author-last').value.trim(),
        }))
        .filter(a => a.last_name);

    const payload = {
        bib_key:   document.getElementById('bib_key').value.trim(),
        bib_type:  document.getElementById('bib_type').value,
        title:     document.getElementById('title').value.trim()     || null,
        year:      parseInt(document.getElementById('year').value)   || null,
        publisher: document.getElementById('publisher').value.trim() || null,
        journal:   document.getElementById('journal').value.trim()   || null,
        authors,
    };

    const url    = editingId ? `${API}/entries/${editingId}` : `${API}/entries`;
    const method = editingId ? 'PUT' : 'POST';

    const btn = document.getElementById('submitBtn');
    btn.disabled = true;

    try {
        const resp = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (resp.ok || resp.status === 201) {
            closeModal();
            await loadEntries();
        } else {
            const err = await resp.json().catch(() => ({}));
            alert(err.detail || 'Error saving entry.');
        }
    } finally {
        btn.disabled = false;
    }
}

// ── Delete modal ─────────────────────────────────────────────────────────────

function openDeleteModal(id, key) {
    deletingId = id;
    document.getElementById('deleteMessage').textContent =
        `Are you sure you want to delete "${key}"? This action cannot be undone.`;
    document.getElementById('deleteModal').style.display = 'flex';
}

function closeDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
    deletingId = null;
}

async function confirmDelete() {
    if (!deletingId) return;
    const resp = await fetch(`${API}/entries/${deletingId}`, { method: 'DELETE' });
    if (resp.ok || resp.status === 204) {
        closeDeleteModal();
        await loadEntries();
    } else {
        alert('Error deleting entry.');
    }
}

// ── Keyboard shortcuts ────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        closeModal();
        closeDeleteModal();
    }
});

// ── Init ─────────────────────────────────────────────────────────────────────
loadEntries();
