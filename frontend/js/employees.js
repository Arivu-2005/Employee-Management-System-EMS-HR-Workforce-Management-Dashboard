/**
 * EMS - Employees Module
 */

let currentPage = 1;
let currentLimit = 10;
let totalPages = 1;

document.addEventListener('DOMContentLoaded', async () => {
  await loadDepartmentsDropdown();
  await loadEmployees();

  // Search input with debounce
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        currentPage = 1;
        loadEmployees();
      }, 300);
    });
  }

  // Filters
  const deptFilter = document.getElementById('filter-department');
  const statusFilter = document.getElementById('filter-status');
  const typeFilter = document.getElementById('filter-type');

  [deptFilter, statusFilter, typeFilter].forEach(el => {
    if (el) {
      el.addEventListener('change', () => {
        currentPage = 1;
        loadEmployees();
      });
    }
  });

  // Salary real-time calculator in employee form
  setupSalaryCalculators();

  // Photo upload & preview handlers
  setupPhotoUploadPreview();

  // Form submit handler
  const empForm = document.getElementById('employeeForm');
  if (empForm) {
    empForm.addEventListener('submit', handleEmployeeFormSubmit);
  }
});

async function loadDepartmentsDropdown() {
  const res = await apiFetch('/departments');
  if (res && res.success) {
    const filterSelect = document.getElementById('filter-department');
    const formSelect = document.getElementById('emp-department');

    const optionsHtml = res.data.map(d => `<option value="${d.name}">${d.name}</option>`).join('');

    if (filterSelect) {
      filterSelect.innerHTML = `<option value="All">All Departments</option>` + optionsHtml;
    }
    if (formSelect) {
      formSelect.innerHTML = `<option value="" disabled selected>Select Department</option>` + optionsHtml;
    }
  }
}

async function loadEmployees() {
  const tbody = document.getElementById('employees-table-body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading employees...</td></tr>`;

  const search = document.getElementById('search-input')?.value.trim() || '';
  const dept = document.getElementById('filter-department')?.value || 'All';
  const status = document.getElementById('filter-status')?.value || 'All';
  const type = document.getElementById('filter-type')?.value || 'All';

  const queryParams = new URLSearchParams({
    page: currentPage,
    limit: currentLimit,
    search,
    department: dept,
    status,
    type
  });

  const res = await apiFetch(`/employees?${queryParams.toString()}`);
  if (res && res.success) {
    const { employees, pagination } = res.data;
    totalPages = pagination.total_pages;

    if (employees.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted">No employees found matching the filter criteria.</td></tr>`;
      renderPagination(0, 0, 0);
      return;
    }

    tbody.innerHTML = employees.map(emp => {
      const sal = emp.salary || {};
      const statusClass = emp.status === 'Active' ? 'active' : (emp.status === 'On Leave' ? 'on-leave' : 'inactive');

      return `
        <tr>
          <td>
            <div class="d-flex align-items-center gap-2">
              <img src="${emp.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=300&q=80'}" alt="${emp.name}" class="avatar-sm">
              <div>
                <span class="badge bg-light text-dark border font-monospace" style="font-size: 0.75rem;">${emp.employee_id}</span>
              </div>
            </div>
          </td>
          <td>
            <div class="fw-semibold text-dark">${emp.name}</div>
            <div class="text-muted small">${emp.email}</div>
          </td>
          <td>
            <div class="text-dark fw-medium">${emp.department || '-'}</div>
            <div class="text-muted small">${emp.designation || '-'}</div>
          </td>
          <td>
            <span class="badge bg-light text-muted border">${emp.employment_type || 'Full-Time'}</span>
          </td>
          <td>
            <span class="badge-status ${statusClass}">
              <i class="bi bi-circle-fill" style="font-size: 6px;"></i> ${emp.status}
            </span>
          </td>
          <td>
            <span class="fw-bold text-dark">${formatCurrency(sal.net || 0)}</span>
            <div class="text-muted small" style="font-size: 0.72rem;">Gross: ${formatCurrency(sal.gross || 0)}</div>
          </td>
          <td class="text-end">
            <div class="d-inline-flex gap-1">
              <button class="btn-action-icon" title="View Profile" onclick="viewEmployeeProfile('${emp.employee_id}')">
                <i class="bi bi-eye"></i>
              </button>
              <button class="btn-action-icon" title="Edit Employee" onclick="openEditEmployeeModal('${emp.employee_id}')">
                <i class="bi bi-pencil"></i>
              </button>
              <button class="btn-action-icon text-danger" title="Delete Employee" onclick="deleteEmployee('${emp.employee_id}', '${emp.name}')">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    renderPagination(pagination.page, pagination.total_pages, pagination.total);
  }
}

function renderPagination(page, pages, total) {
  const container = document.getElementById('pagination-container');
  const info = document.getElementById('pagination-info');
  if (!container) return;

  if (info) {
    info.textContent = `Showing page ${page} of ${pages} (${total} total records)`;
  }

  if (pages <= 1) {
    container.innerHTML = '';
    return;
  }

  let html = `
    <li class="page-item ${page <= 1 ? 'disabled' : ''}">
      <button class="page-link" onclick="changePage(${page - 1})"><i class="bi bi-chevron-left"></i></button>
    </li>
  `;

  for (let i = 1; i <= pages; i++) {
    if (i === 1 || i === pages || (i >= page - 1 && i <= page + 1)) {
      html += `
        <li class="page-item ${i === page ? 'active' : ''}">
          <button class="page-link" onclick="changePage(${i})">${i}</button>
        </li>
      `;
    } else if (i === page - 2 || i === page + 2) {
      html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
    }
  }

  html += `
    <li class="page-item ${page >= pages ? 'disabled' : ''}">
      <button class="page-link" onclick="changePage(${page + 1})"><i class="bi bi-chevron-right"></i></button>
    </li>
  `;

  container.innerHTML = html;
}

function changePage(p) {
  if (p >= 1 && p <= totalPages) {
    currentPage = p;
    loadEmployees();
  }
}

function setupSalaryCalculators() {
  const basic = document.getElementById('emp-basic');
  const hra = document.getElementById('emp-hra');
  const allowances = document.getElementById('emp-allowances');
  const deductions = document.getElementById('emp-deductions');
  const grossDisplay = document.getElementById('emp-gross-display');
  const netDisplay = document.getElementById('emp-net-display');

  function calculate() {
    const b = parseFloat(basic?.value || 0) || 0;
    const h = parseFloat(hra?.value || 0) || 0;
    const a = parseFloat(allowances?.value || 0) || 0;
    const d = parseFloat(deductions?.value || 0) || 0;

    const gross = b + h + a;
    const net = Math.max(0, gross - d);

    if (grossDisplay) grossDisplay.textContent = formatCurrency(gross);
    if (netDisplay) netDisplay.textContent = formatCurrency(net);
  }

  [basic, hra, allowances, deductions].forEach(el => {
    if (el) el.addEventListener('input', calculate);
  });
}

function setupPhotoUploadPreview() {
  const photoFileInput = document.getElementById('emp-photo-file');
  const photoUrlInput = document.getElementById('emp-avatar');
  const photoPreview = document.getElementById('emp-photo-preview');

  if (photoFileInput) {
    photoFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        // Validate max 10MB
        if (file.size > 10 * 1024 * 1024) {
          Swal.fire({
            icon: 'warning',
            title: 'File Too Large',
            text: 'Image file size cannot exceed 10MB.',
            confirmButtonColor: '#2563eb'
          });
          photoFileInput.value = '';
          return;
        }

        const reader = new FileReader();
        reader.onload = (event) => {
          if (photoPreview) photoPreview.src = event.target.result;
        };
        reader.readAsDataURL(file);
      }
    });
  }

  if (photoUrlInput) {
    photoUrlInput.addEventListener('input', (e) => {
      const val = e.target.value.trim();
      if (val && photoPreview) {
        photoPreview.src = val;
      }
    });
  }
}

function openAddEmployeeModal() {
  const form = document.getElementById('employeeForm');
  if (form) form.reset();

  document.getElementById('emp-id-input').value = '';
  document.getElementById('emp-edit-id').value = '';
  document.getElementById('employeeModalTitle').textContent = 'Add New Employee';
  document.getElementById('emp-gross-display').textContent = '$0.00';
  document.getElementById('emp-net-display').textContent = '$0.00';

  const defaultAvatar = 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=300&q=80';
  const preview = document.getElementById('emp-photo-preview');
  if (preview) preview.src = defaultAvatar;
  const fileInput = document.getElementById('emp-photo-file');
  if (fileInput) fileInput.value = '';

  const modal = new bootstrap.Modal(document.getElementById('employeeModal'));
  modal.show();
}

async function openEditEmployeeModal(empId) {
  const res = await apiFetch(`/employees/${empId}`);
  if (res && res.success) {
    const emp = res.data;
    document.getElementById('emp-edit-id').value = emp.employee_id;
    document.getElementById('emp-id-input').value = emp.employee_id;
    document.getElementById('emp-first-name').value = emp.first_name || '';
    document.getElementById('emp-last-name').value = emp.last_name || '';
    document.getElementById('emp-email').value = emp.email || '';
    document.getElementById('emp-phone').value = emp.phone || '';
    document.getElementById('emp-gender').value = emp.gender || 'Male';
    document.getElementById('emp-dob').value = emp.dob || '';
    document.getElementById('emp-address').value = emp.address || '';
    document.getElementById('emp-department').value = emp.department || '';
    document.getElementById('emp-designation').value = emp.designation || '';
    document.getElementById('emp-employment-type').value = emp.employment_type || 'Full-Time';
    document.getElementById('emp-joining-date').value = emp.joining_date || '';
    document.getElementById('emp-status').value = emp.status || 'Active';
    document.getElementById('emp-avatar').value = emp.avatar || '';

    const defaultAvatar = 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=300&q=80';
    const preview = document.getElementById('emp-photo-preview');
    if (preview) preview.src = emp.avatar || defaultAvatar;
    const fileInput = document.getElementById('emp-photo-file');
    if (fileInput) fileInput.value = '';

    const sal = emp.salary || {};
    document.getElementById('emp-basic').value = sal.basic || 0;
    document.getElementById('emp-hra').value = sal.hra || 0;
    document.getElementById('emp-allowances').value = sal.allowances || 0;
    document.getElementById('emp-deductions').value = sal.deductions || 0;

    document.getElementById('emp-gross-display').textContent = formatCurrency(sal.gross || 0);
    document.getElementById('emp-net-display').textContent = formatCurrency(sal.net || 0);

    document.getElementById('employeeModalTitle').textContent = `Edit Employee: ${emp.name}`;
    const modal = new bootstrap.Modal(document.getElementById('employeeModal'));
    modal.show();
  }
}

async function handleEmployeeFormSubmit(e) {
  e.preventDefault();

  const saveBtn = document.getElementById('saveEmployeeBtn');
  const originalBtnHtml = saveBtn ? saveBtn.innerHTML : '';
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Saving...`;
  }

  try {
    const editId = document.getElementById('emp-edit-id').value;
    const isEdit = Boolean(editId);

    let avatarUrl = document.getElementById('emp-avatar').value.trim();

    // Check if an image file was selected for upload
    const fileInput = document.getElementById('emp-photo-file');
    if (fileInput && fileInput.files && fileInput.files[0]) {
      const formData = new FormData();
      formData.append('photo', fileInput.files[0]);

      const token = localStorage.getItem('ems_token');
      const uploadRes = await fetch(`${API_BASE}/employees/upload-photo`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      const uploadData = await uploadRes.json();

      if (uploadData && uploadData.success && uploadData.data?.url) {
        avatarUrl = uploadData.data.url;
      } else {
        Swal.fire({
          icon: 'error',
          title: 'Photo Upload Failed',
          text: uploadData ? uploadData.message : 'Could not upload photo file.',
          confirmButtonColor: '#2563eb'
        });
        return;
      }
    }

    const payload = {
      employee_id: document.getElementById('emp-id-input').value.trim() || undefined,
      first_name: document.getElementById('emp-first-name').value.trim(),
      last_name: document.getElementById('emp-last-name').value.trim(),
      email: document.getElementById('emp-email').value.trim(),
      phone: document.getElementById('emp-phone').value.trim(),
      gender: document.getElementById('emp-gender').value,
      dob: document.getElementById('emp-dob').value,
      address: document.getElementById('emp-address').value.trim(),
      department: document.getElementById('emp-department').value,
      designation: document.getElementById('emp-designation').value.trim(),
      employment_type: document.getElementById('emp-employment-type').value,
      joining_date: document.getElementById('emp-joining-date').value,
      status: document.getElementById('emp-status').value,
      avatar: avatarUrl || undefined,
      basic_salary: parseFloat(document.getElementById('emp-basic').value || 0),
      hra: parseFloat(document.getElementById('emp-hra').value || 0),
      allowances: parseFloat(document.getElementById('emp-allowances').value || 0),
      deductions: parseFloat(document.getElementById('emp-deductions').value || 0)
    };

    const endpoint = isEdit ? `/employees/${editId}` : '/employees';
    const method = isEdit ? 'PUT' : 'POST';

    const res = await apiFetch(endpoint, {
      method,
      body: JSON.stringify(payload)
    });

    if (res && res.success) {
      showToast('success', isEdit ? 'Employee updated successfully!' : 'Employee registered successfully!');
      const modalEl = document.getElementById('employeeModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();
      loadEmployees();
    } else {
      Swal.fire({
        icon: 'error',
        title: 'Action Failed',
        text: res ? res.message : 'Unable to save employee details.',
        confirmButtonColor: '#2563eb'
      });
    }
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.innerHTML = originalBtnHtml;
    }
  }
}

async function viewEmployeeProfile(empId) {
  const res = await apiFetch(`/employees/${empId}`);
  if (res && res.success) {
    const emp = res.data;
    const sal = emp.salary || {};
    const leaves = emp.leave_balance || {};

    const container = document.getElementById('profile-modal-body');
    if (!container) return;

    container.innerHTML = `
      <div class="text-center pb-3 border-bottom mb-3">
        <img src="${emp.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=300&q=80'}" class="rounded-circle shadow-sm mb-2" style="width: 80px; height: 80px; object-fit: cover;">
        <h5 class="fw-bold text-dark mb-0">${emp.name}</h5>
        <div class="text-muted small">${emp.designation} • <span class="text-primary">${emp.department}</span></div>
        <div class="mt-2">
          <span class="badge bg-light text-dark border font-monospace me-2">${emp.employee_id}</span>
          <span class="badge-status ${emp.status === 'Active' ? 'active' : 'inactive'}">${emp.status}</span>
        </div>
      </div>

      <div class="row g-3 small mb-3">
        <div class="col-sm-6">
          <div class="text-muted">Email</div>
          <div class="fw-semibold text-dark">${emp.email}</div>
        </div>
        <div class="col-sm-6">
          <div class="text-muted">Phone</div>
          <div class="fw-semibold text-dark">${emp.phone || '-'}</div>
        </div>
        <div class="col-sm-6">
          <div class="text-muted">Employment Type</div>
          <div class="fw-semibold text-dark">${emp.employment_type}</div>
        </div>
        <div class="col-sm-6">
          <div class="text-muted">Joining Date</div>
          <div class="fw-semibold text-dark">${formatDate(emp.joining_date)}</div>
        </div>
        <div class="col-sm-6">
          <div class="text-muted">Gender / DOB</div>
          <div class="fw-semibold text-dark">${emp.gender} (${emp.dob || '-'})</div>
        </div>
        <div class="col-sm-6">
          <div class="text-muted">Address</div>
          <div class="fw-semibold text-dark text-truncate">${emp.address || '-'}</div>
        </div>
      </div>

      <h6 class="fw-bold text-dark border-bottom pb-2 mb-2"><i class="bi bi-wallet2 me-1 text-primary"></i> Salary Configuration</h6>
      <div class="row g-2 small mb-3 bg-light p-2 rounded">
        <div class="col-4">Basic: <strong class="text-dark">${formatCurrency(sal.basic)}</strong></div>
        <div class="col-4">HRA: <strong class="text-dark">${formatCurrency(sal.hra)}</strong></div>
        <div class="col-4">Allowances: <strong class="text-dark">${formatCurrency(sal.allowances)}</strong></div>
        <div class="col-4">Deductions: <strong class="text-danger">-${formatCurrency(sal.deductions)}</strong></div>
        <div class="col-4">Gross: <strong class="text-dark">${formatCurrency(sal.gross)}</strong></div>
        <div class="col-4">Net: <strong class="text-success">${formatCurrency(sal.net)}</strong></div>
      </div>

      <h6 class="fw-bold text-dark border-bottom pb-2 mb-2"><i class="bi bi-calendar-range me-1 text-primary"></i> Leave Balances</h6>
      <div class="d-flex gap-2 small">
        <span class="badge bg-white text-dark border p-2 flex-grow-1 text-center">Casual: <strong>${leaves.casual ?? 12}</strong></span>
        <span class="badge bg-white text-dark border p-2 flex-grow-1 text-center">Sick: <strong>${leaves.sick ?? 10}</strong></span>
        <span class="badge bg-white text-dark border p-2 flex-grow-1 text-center">Earned: <strong>${leaves.earned ?? 15}</strong></span>
      </div>
    `;

    const modal = new bootstrap.Modal(document.getElementById('viewProfileModal'));
    modal.show();
  }
}

async function deleteEmployee(empId, name) {
  const confirm = await confirmDialog(
    'Delete Employee?',
    `Are you sure you want to permanently remove ${name} (${empId})? All corresponding attendance, payroll, and leave records will be cleaned up.`,
    'Yes, Delete'
  );

  if (confirm.isConfirmed) {
    const res = await apiFetch(`/employees/${empId}`, { method: 'DELETE' });
    if (res && res.success) {
      showToast('success', `Employee ${empId} removed.`);
      loadEmployees();
    } else {
      Swal.fire({
        icon: 'error',
        title: 'Delete Failed',
        text: res ? res.message : 'Unable to delete employee.',
        confirmButtonColor: '#2563eb'
      });
    }
  }
}
