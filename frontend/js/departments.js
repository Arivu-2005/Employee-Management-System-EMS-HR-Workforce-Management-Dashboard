/**
 * EMS - Departments Module
 */

document.addEventListener('DOMContentLoaded', () => {
  loadDepartments();

  const form = document.getElementById('departmentForm');
  if (form) {
    form.addEventListener('submit', handleDepartmentFormSubmit);
  }
});

async function loadDepartments() {
  const container = document.getElementById('departments-grid');
  const tableBody = document.getElementById('departments-table-body');
  if (!container || !tableBody) return;

  container.innerHTML = `<div class="col-12 text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading departments...</div>`;
  tableBody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading...</td></tr>`;

  const res = await apiFetch('/departments');
  if (res && res.success) {
    const depts = res.data;

    if (depts.length === 0) {
      container.innerHTML = `<div class="col-12 text-center py-5 text-muted">No departments created yet.</div>`;
      tableBody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">No departments found.</td></tr>`;
      return;
    }

    // Render Department Cards
    container.innerHTML = depts.map(d => `
      <div class="col-xl-4 col-md-6">
        <div class="card card-custom h-100">
          <div class="card-custom-body d-flex flex-column justify-content-between">
            <div>
              <div class="d-flex align-items-center justify-content-between mb-3">
                <div class="stat-icon primary" style="width: 44px; height: 44px; font-size: 1.25rem;">
                  <i class="bi bi-diagram-3-fill"></i>
                </div>
                <div class="dropdown">
                  <button class="btn btn-action-icon" type="button" data-bs-toggle="dropdown">
                    <i class="bi bi-three-dots-vertical"></i>
                  </button>
                  <ul class="dropdown-menu dropdown-menu-end shadow-sm">
                    <li><a class="dropdown-item" href="javascript:void(0)" onclick="openEditDepartmentModal('${d._id}', '${escapeHtml(d.name)}', '${escapeHtml(d.description || '')}', '${escapeHtml(d.manager_name || '')}')"><i class="bi bi-pencil me-2"></i> Edit Details</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item text-danger" href="javascript:void(0)" onclick="deleteDepartment('${d._id}', '${escapeHtml(d.name)}', ${d.employee_count})"><i class="bi bi-trash me-2"></i> Delete Unit</a></li>
                  </ul>
                </div>
              </div>

              <h5 class="fw-bold text-dark mb-1">${d.name}</h5>
              <p class="text-muted small mb-3">${d.description || 'No description provided.'}</p>
            </div>

            <div>
              <div class="p-2 bg-light rounded small mb-3">
                <div class="d-flex justify-content-between mb-1">
                  <span class="text-muted">Head of Dept:</span>
                  <span class="fw-semibold text-dark">${d.manager_name || 'Unassigned'}</span>
                </div>
                <div class="d-flex justify-content-between">
                  <span class="text-muted">Staff Allocation:</span>
                  <span class="fw-bold text-primary">${d.employee_count} Members</span>
                </div>
              </div>

              <div class="d-flex justify-content-between align-items-center">
                <span class="badge bg-light text-success border">
                  <i class="bi bi-person-check-fill me-1"></i> ${d.active_count || 0} Active
                </span>
                <span class="badge bg-light text-info border">
                  <i class="bi bi-person-dash me-1"></i> ${d.on_leave_count || 0} On Leave
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `).join('');

    // Render Table View
    tableBody.innerHTML = depts.map(d => `
      <tr>
        <td>
          <div class="fw-bold text-dark">${d.name}</div>
          <div class="text-muted small">${d.description || '-'}</div>
        </td>
        <td>
          <span class="fw-medium text-dark">${d.manager_name || 'Unassigned'}</span>
        </td>
        <td>
          <span class="badge bg-primary text-white">${d.employee_count} Employees</span>
        </td>
        <td>
          <span class="badge-status active">${d.active_count || 0} Active</span>
        </td>
        <td class="text-end">
          <div class="d-inline-flex gap-1">
            <button class="btn-action-icon" title="Edit Department" onclick="openEditDepartmentModal('${d._id}', '${escapeHtml(d.name)}', '${escapeHtml(d.description || '')}', '${escapeHtml(d.manager_name || '')}')">
              <i class="bi bi-pencil"></i>
            </button>
            <button class="btn-action-icon text-danger" title="Delete Department" onclick="deleteDepartment('${d._id}', '${escapeHtml(d.name)}', ${d.employee_count})">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  }
}

function openAddDepartmentModal() {
  const form = document.getElementById('departmentForm');
  if (form) form.reset();

  document.getElementById('dept-edit-id').value = '';
  document.getElementById('departmentModalTitle').textContent = 'Create New Department';

  const modal = new bootstrap.Modal(document.getElementById('departmentModal'));
  modal.show();
}

function openEditDepartmentModal(id, name, desc, manager) {
  document.getElementById('dept-edit-id').value = id;
  document.getElementById('dept-name').value = name;
  document.getElementById('dept-description').value = desc;
  document.getElementById('dept-manager').value = manager;

  document.getElementById('departmentModalTitle').textContent = `Edit Department: ${name}`;
  const modal = new bootstrap.Modal(document.getElementById('departmentModal'));
  modal.show();
}

async function handleDepartmentFormSubmit(e) {
  e.preventDefault();

  const editId = document.getElementById('dept-edit-id').value;
  const isEdit = Boolean(editId);

  const payload = {
    name: document.getElementById('dept-name').value.trim(),
    description: document.getElementById('dept-description').value.trim(),
    manager_name: document.getElementById('dept-manager').value.trim()
  };

  const endpoint = isEdit ? `/departments/${editId}` : '/departments';
  const method = isEdit ? 'PUT' : 'POST';

  const res = await apiFetch(endpoint, {
    method,
    body: JSON.stringify(payload)
  });

  if (res && res.success) {
    showToast('success', isEdit ? 'Department updated successfully!' : 'Department created successfully!');
    const modalEl = document.getElementById('departmentModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
    loadDepartments();
  } else {
    Swal.fire({
      icon: 'error',
      title: 'Action Failed',
      text: res ? res.message : 'Could not save department.',
      confirmButtonColor: '#2563eb'
    });
  }
}

async function deleteDepartment(id, name, empCount) {
  if (empCount > 0) {
    Swal.fire({
      icon: 'warning',
      title: 'Active Employees Assigned',
      text: `Cannot delete '${name}' because ${empCount} employee(s) are currently assigned to it. Please reassign the employees first.`,
      confirmButtonColor: '#2563eb'
    });
    return;
  }

  const confirm = await confirmDialog(
    'Delete Department?',
    `Are you sure you want to delete department '${name}'?`,
    'Yes, Delete'
  );

  if (confirm.isConfirmed) {
    const res = await apiFetch(`/departments/${id}`, { method: 'DELETE' });
    if (res && res.success) {
      showToast('success', `Department '${name}' deleted.`);
      loadDepartments();
    } else {
      Swal.fire({
        icon: 'error',
        title: 'Delete Failed',
        text: res ? res.message : 'Could not delete department.',
        confirmButtonColor: '#2563eb'
      });
    }
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}
