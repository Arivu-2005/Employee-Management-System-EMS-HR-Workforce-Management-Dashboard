/**
 * EMS - Leaves Module
 */

document.addEventListener('DOMContentLoaded', async () => {
  await loadEmployeesDropdown();
  await loadLeaves();

  // Filters
  const statusFilter = document.getElementById('filter-leave-status');
  const typeFilter = document.getElementById('filter-leave-type');

  [statusFilter, typeFilter].forEach(el => {
    if (el) {
      el.addEventListener('change', () => loadLeaves());
    }
  });

  // Calculate days count automatically
  setupDateSpanCalculator();

  // Form Submit
  const form = document.getElementById('applyLeaveForm');
  if (form) {
    form.addEventListener('submit', handleApplyLeaveSubmit);
  }
});

async function loadEmployeesDropdown() {
  const res = await apiFetch('/employees?limit=100');
  if (res && res.success) {
    const select = document.getElementById('leave-emp-id');
    if (select) {
      select.innerHTML = `<option value="" disabled selected>Select Employee</option>` +
        res.data.employees.map(e => {
          const b = e.leave_balance || {};
          return `<option value="${e.employee_id}" data-casual="${b.casual ?? 12}" data-sick="${b.sick ?? 10}" data-earned="${b.earned ?? 15}">${e.name} (${e.employee_id}) - ${e.department}</option>`;
        }).join('');

      select.addEventListener('change', updateEmployeeBalanceIndicator);
    }
  }
}

function updateEmployeeBalanceIndicator() {
  const select = document.getElementById('leave-emp-id');
  const selected = select.options[select.selectedIndex];
  const indicator = document.getElementById('employee-leave-balances');

  if (selected && indicator) {
    const c = selected.getAttribute('data-casual') || 12;
    const s = selected.getAttribute('data-sick') || 10;
    const e = selected.getAttribute('data-earned') || 15;

    indicator.innerHTML = `
      <div class="p-2 bg-light rounded small mt-1 mb-2 d-flex justify-content-between">
        <span>Casual: <strong>${c}</strong></span>
        <span>Sick: <strong>${s}</strong></span>
        <span>Earned: <strong>${e}</strong></span>
      </div>
    `;
  }
}

function setupDateSpanCalculator() {
  const d1 = document.getElementById('leave-start-date');
  const d2 = document.getElementById('leave-end-date');
  const daysDisplay = document.getElementById('leave-days-count');

  function calculate() {
    if (d1?.value && d2?.value) {
      const dt1 = new Date(d1.value);
      const dt2 = new Date(d2.value);
      if (dt2 >= dt1) {
        const diffTime = Math.abs(dt2 - dt1);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
        if (daysDisplay) daysDisplay.textContent = `${diffDays} day(s)`;
      } else {
        if (daysDisplay) daysDisplay.textContent = 'Invalid range';
      }
    }
  }

  if (d1) d1.addEventListener('change', calculate);
  if (d2) d2.addEventListener('change', calculate);
}

async function loadLeaves() {
  const tbody = document.getElementById('leaves-table-body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading leave requests...</td></tr>`;

  const status = document.getElementById('filter-leave-status')?.value || 'All';
  const type = document.getElementById('filter-leave-type')?.value || 'All';

  const queryParams = new URLSearchParams({
    status,
    type
  });

  const res = await apiFetch(`/leaves?${queryParams.toString()}`);
  if (res && res.success) {
    const leaves = res.data;

    let pendingCount = 0;
    let approvedCount = 0;
    let rejectedCount = 0;

    leaves.forEach(l => {
      if (l.status === 'Pending') pendingCount++;
      else if (l.status === 'Approved') approvedCount++;
      else if (l.status === 'Rejected') rejectedCount++;
    });

    document.getElementById('kpi-pending-leaves').textContent = pendingCount;
    document.getElementById('kpi-approved-leaves').textContent = approvedCount;
    document.getElementById('kpi-rejected-leaves').textContent = rejectedCount;

    if (leaves.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted">No leave requests found matching criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = leaves.map(lv => {
      let badgeClass = 'pending';
      if (lv.status === 'Approved') badgeClass = 'approved';
      else if (lv.status === 'Rejected') badgeClass = 'rejected';

      const actions = lv.status === 'Pending' ? `
        <button class="btn btn-sm btn-success px-2 py-1" title="Approve" onclick="approveLeave('${lv._id}', '${lv.employee_name}', '${lv.leave_type}')">
          <i class="bi bi-check-lg"></i> Approve
        </button>
        <button class="btn btn-sm btn-outline-danger px-2 py-1" title="Reject" onclick="rejectLeave('${lv._id}', '${lv.employee_name}')">
          <i class="bi bi-x-lg"></i> Reject
        </button>
      ` : `
        <span class="text-muted small">${lv.reviewed_by ? 'By ' + lv.reviewed_by : '-'}</span>
      `;

      return `
        <tr>
          <td>
            <div class="fw-semibold text-dark">${lv.employee_name}</div>
            <div class="small font-monospace text-muted">${lv.employee_id} • ${lv.department || '-'}</div>
          </td>
          <td>
            <span class="badge bg-light text-dark border">${lv.leave_type}</span>
          </td>
          <td>
            <div class="fw-medium text-dark">${formatDate(lv.start_date)} to ${formatDate(lv.end_date)}</div>
            <div class="text-primary small fw-semibold">${lv.days_count} day(s) duration</div>
          </td>
          <td style="max-width: 250px;">
            <div class="text-dark small text-truncate" title="${escapeHtml(lv.reason)}">${lv.reason}</div>
            ${lv.review_comment ? `<div class="text-muted small fst-italic" style="font-size: 0.72rem;">Remark: ${escapeHtml(lv.review_comment)}</div>` : ''}
          </td>
          <td>
            <span class="text-muted small">${formatDate(lv.applied_at)}</span>
          </td>
          <td>
            <span class="badge-status ${badgeClass}">
              <i class="bi bi-circle-fill" style="font-size: 6px;"></i> ${lv.status}
            </span>
          </td>
          <td class="text-end">
            <div class="d-inline-flex gap-1 align-items-center">
              ${actions}
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }
}

function openApplyLeaveModal() {
  const form = document.getElementById('applyLeaveForm');
  if (form) form.reset();

  const today = new Date().toISOString().split('T')[0];
  document.getElementById('leave-start-date').value = today;
  document.getElementById('leave-end-date').value = today;
  document.getElementById('leave-days-count').textContent = '1 day(s)';
  document.getElementById('employee-leave-balances').innerHTML = '';

  const modal = new bootstrap.Modal(document.getElementById('applyLeaveModal'));
  modal.show();
}

async function handleApplyLeaveSubmit(e) {
  e.preventDefault();

  const payload = {
    employee_id: document.getElementById('leave-emp-id').value,
    leave_type: document.getElementById('leave-type').value,
    start_date: document.getElementById('leave-start-date').value,
    end_date: document.getElementById('leave-end-date').value,
    reason: document.getElementById('leave-reason').value.trim()
  };

  const res = await apiFetch('/leaves', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  if (res && res.success) {
    showToast('success', 'Leave request submitted successfully!');
    const modalEl = document.getElementById('applyLeaveModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
    loadLeaves();
  } else {
    Swal.fire({
      icon: 'error',
      title: 'Submission Failed',
      text: res ? res.message : 'Unable to apply for leave.',
      confirmButtonColor: '#2563eb'
    });
  }
}

async function approveLeave(id, empName, leaveType) {
  const { value: comment } = await Swal.fire({
    title: `Approve Leave for ${empName}?`,
    text: `This will deduct from employee's ${leaveType} balance and update their attendance roster accordingly.`,
    input: 'text',
    inputLabel: 'Approval Remark (Optional)',
    inputValue: 'Approved as requested.',
    showCancelButton: true,
    confirmButtonColor: '#10b981',
    cancelButtonColor: '#64748b',
    confirmButtonText: 'Yes, Approve'
  });

  if (comment !== undefined) {
    const res = await apiFetch(`/leaves/${id}/approve`, {
      method: 'PUT',
      body: JSON.stringify({ review_comment: comment })
    });

    if (res && res.success) {
      showToast('success', 'Leave approved and attendance synchronized!');
      loadLeaves();
    } else {
      Swal.fire({
        icon: 'error',
        title: 'Error',
        text: res ? res.message : 'Could not approve leave.',
        confirmButtonColor: '#2563eb'
      });
    }
  }
}

async function rejectLeave(id, empName) {
  const { value: comment } = await Swal.fire({
    title: `Reject Leave for ${empName}?`,
    input: 'text',
    inputLabel: 'Reason for Rejection',
    inputPlaceholder: 'e.g. Critical project milestone in progress...',
    inputValidator: (value) => {
      if (!value) {
        return 'Please provide a brief reason for rejecting this leave.';
      }
    },
    showCancelButton: true,
    confirmButtonColor: '#ef4444',
    cancelButtonColor: '#64748b',
    confirmButtonText: 'Reject Request'
  });

  if (comment) {
    const res = await apiFetch(`/leaves/${id}/reject`, {
      method: 'PUT',
      body: JSON.stringify({ review_comment: comment })
    });

    if (res && res.success) {
      showToast('info', 'Leave request rejected.');
      loadLeaves();
    } else {
      Swal.fire({
        icon: 'error',
        title: 'Error',
        text: res ? res.message : 'Could not reject leave.',
        confirmButtonColor: '#2563eb'
      });
    }
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}
