/**
 * EMS - Attendance Module
 */

document.addEventListener('DOMContentLoaded', async () => {
  // Set default date input to today
  const today = new Date().toISOString().split('T')[0];
  const dateInput = document.getElementById('filter-attendance-date');
  if (dateInput) {
    dateInput.value = today;
  }

  await loadEmployeesDropdown();
  await loadAttendanceSummary(today);
  await loadAttendanceRecords();

  // Date change listener
  if (dateInput) {
    dateInput.addEventListener('change', (e) => {
      loadAttendanceSummary(e.target.value);
      loadAttendanceRecords();
    });
  }

  // Filter listeners
  const statusFilter = document.getElementById('filter-attendance-status');
  if (statusFilter) {
    statusFilter.addEventListener('change', () => loadAttendanceRecords());
  }

  // Attendance Form Submit
  const form = document.getElementById('attendanceForm');
  if (form) {
    form.addEventListener('submit', handleAttendanceFormSubmit);
  }

  // Auto calculate working hours on time inputs
  setupTimeCalculators();
});

async function loadEmployeesDropdown() {
  const res = await apiFetch('/employees?limit=100');
  if (res && res.success) {
    const select = document.getElementById('att-employee-id');
    if (select) {
      select.innerHTML = `<option value="" disabled selected>Choose Employee</option>` +
        res.data.employees.map(e => `<option value="${e.employee_id}">${e.name} (${e.employee_id}) - ${e.department}</option>`).join('');
    }
  }
}

async function loadAttendanceSummary(dateStr) {
  const res = await apiFetch(`/attendance/summary?date=${dateStr}`);
  if (res && res.success) {
    const s = res.data;
    document.getElementById('att-summary-present').textContent = s.present;
    document.getElementById('att-summary-late').textContent = s.late;
    document.getElementById('att-summary-halfday').textContent = s.half_day;
    document.getElementById('att-summary-absent').textContent = s.absent;
    document.getElementById('att-summary-leave').textContent = s.on_leave;
    document.getElementById('att-summary-rate').textContent = `${s.attendance_rate}%`;
  }
}

async function loadAttendanceRecords() {
  const tbody = document.getElementById('attendance-table-body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading attendance...</td></tr>`;

  const dateVal = document.getElementById('filter-attendance-date')?.value || '';
  const statusVal = document.getElementById('filter-attendance-status')?.value || 'All';

  const queryParams = new URLSearchParams({
    date: dateVal,
    status: statusVal
  });

  const res = await apiFetch(`/attendance?${queryParams.toString()}`);
  if (res && res.success) {
    const records = res.data;

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted">No attendance records found for this date. Click "Mark Attendance" to record.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map(rec => {
      let badgeClass = 'present';
      if (rec.status === 'Absent') badgeClass = 'absent';
      else if (rec.status === 'Late') badgeClass = 'late';
      else if (rec.status === 'Half-Day') badgeClass = 'half-day';
      else if (rec.status === 'Leave') badgeClass = 'leave';

      return `
        <tr>
          <td>
            <div class="fw-semibold text-dark">${rec.employee_name}</div>
            <div class="small font-monospace text-muted">${rec.employee_id} • ${rec.department || '-'}</div>
          </td>
          <td>
            <span class="fw-medium text-dark">${formatDate(rec.date)}</span>
          </td>
          <td>
            <span class="badge-status ${badgeClass}">
              <i class="bi bi-circle-fill" style="font-size: 6px;"></i> ${rec.status}
            </span>
          </td>
          <td><span class="font-monospace text-dark">${rec.check_in || '-'}</span></td>
          <td><span class="font-monospace text-dark">${rec.check_out || '-'}</span></td>
          <td>
            <span class="fw-bold text-dark">${rec.working_hours ? rec.working_hours + ' hrs' : '-'}</span>
          </td>
          <td class="text-end">
            <div class="d-inline-flex gap-1">
              <button class="btn-action-icon" title="Edit Entry" onclick="openEditAttendanceModal('${rec._id}', '${rec.employee_id}', '${rec.date}', '${rec.status}', '${rec.check_in}', '${rec.check_out}', '${rec.working_hours || 0}', '${escapeQuotes(rec.notes || '')}')">
                <i class="bi bi-pencil"></i>
              </button>
              <button class="btn-action-icon text-danger" title="Delete Entry" onclick="deleteAttendance('${rec._id}')">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }
}

function setupTimeCalculators() {
  const inEl = document.getElementById('att-checkin');
  const outEl = document.getElementById('att-checkout');
  const hoursEl = document.getElementById('att-hours');
  const statusEl = document.getElementById('att-status');

  function update() {
    const tIn = inEl?.value;
    const tOut = outEl?.value;

    if (tIn && tOut && inEl.closest('.modal').classList.contains('show')) {
      const [h1, m1] = tIn.split(':').map(Number);
      const [h2, m2] = tOut.split(':').map(Number);
      const diffMinutes = (h2 * 60 + m2) - (h1 * 60 + m1);
      if (diffMinutes > 0) {
        const hours = (diffMinutes / 60).toFixed(1);
        if (hoursEl) hoursEl.value = hours;
      }
    }
  }

  if (inEl) inEl.addEventListener('change', update);
  if (outEl) outEl.addEventListener('change', update);

  if (statusEl) {
    statusEl.addEventListener('change', (e) => {
      const val = e.target.value;
      if (val === 'Absent' || val === 'Leave') {
        if (inEl) inEl.value = '';
        if (outEl) outEl.value = '';
        if (hoursEl) hoursEl.value = '0.0';
      } else if (val === 'Present' && (!inEl.value || inEl.value === '')) {
        if (inEl) inEl.value = '09:00';
        if (outEl) outEl.value = '17:30';
        if (hoursEl) hoursEl.value = '8.5';
      }
    });
  }
}

function openAddAttendanceModal() {
  const form = document.getElementById('attendanceForm');
  if (form) form.reset();

  document.getElementById('att-edit-id').value = '';
  document.getElementById('att-employee-id').disabled = false;
  document.getElementById('att-date').value = document.getElementById('filter-attendance-date')?.value || new Date().toISOString().split('T')[0];
  document.getElementById('att-status').value = 'Present';
  document.getElementById('att-checkin').value = '09:00';
  document.getElementById('att-checkout').value = '17:30';
  document.getElementById('att-hours').value = '8.5';
  document.getElementById('attendanceModalTitle').textContent = 'Mark Daily Attendance';

  const modal = new bootstrap.Modal(document.getElementById('attendanceModal'));
  modal.show();
}

function openEditAttendanceModal(id, empId, date, status, checkIn, checkOut, hours, notes) {
  document.getElementById('att-edit-id').value = id;
  document.getElementById('att-employee-id').value = empId;
  document.getElementById('att-employee-id').disabled = true;
  document.getElementById('att-date').value = date;
  document.getElementById('att-status').value = status;
  document.getElementById('att-checkin').value = checkIn !== '-' ? checkIn : '';
  document.getElementById('att-checkout').value = checkOut !== '-' ? checkOut : '';
  document.getElementById('att-hours').value = hours;
  document.getElementById('att-notes').value = notes;

  document.getElementById('attendanceModalTitle').textContent = `Edit Attendance: ${empId}`;
  const modal = new bootstrap.Modal(document.getElementById('attendanceModal'));
  modal.show();
}

async function handleAttendanceFormSubmit(e) {
  e.preventDefault();

  const editId = document.getElementById('att-edit-id').value;
  const isEdit = Boolean(editId);

  const payload = {
    employee_id: document.getElementById('att-employee-id').value,
    date: document.getElementById('att-date').value,
    status: document.getElementById('att-status').value,
    check_in: document.getElementById('att-checkin').value || '-',
    check_out: document.getElementById('att-checkout').value || '-',
    working_hours: parseFloat(document.getElementById('att-hours').value || 0),
    notes: document.getElementById('att-notes').value.trim()
  };

  const endpoint = isEdit ? `/attendance/${editId}` : '/attendance';
  const method = isEdit ? 'PUT' : 'POST';

  const res = await apiFetch(endpoint, {
    method,
    body: JSON.stringify(payload)
  });

  if (res && res.success) {
    showToast('success', isEdit ? 'Attendance updated!' : 'Attendance marked successfully!');
    const modalEl = document.getElementById('attendanceModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();

    const curDate = document.getElementById('filter-attendance-date')?.value;
    loadAttendanceSummary(curDate);
    loadAttendanceRecords();
  } else {
    Swal.fire({
      icon: 'error',
      title: 'Action Failed',
      text: res ? res.message : 'Could not record attendance.',
      confirmButtonColor: '#2563eb'
    });
  }
}

async function deleteAttendance(id) {
  const confirm = await confirmDialog('Delete Attendance Record?', 'Are you sure you want to delete this attendance entry?');
  if (confirm.isConfirmed) {
    const res = await apiFetch(`/attendance/${id}`, { method: 'DELETE' });
    if (res && res.success) {
      showToast('success', 'Attendance record deleted.');
      const curDate = document.getElementById('filter-attendance-date')?.value;
      loadAttendanceSummary(curDate);
      loadAttendanceRecords();
    }
  }
}

function escapeQuotes(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}
