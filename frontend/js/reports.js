/**
 * EMS - Reports & Analytics Module
 */

let activeReportTab = 'employees';

document.addEventListener('DOMContentLoaded', async () => {
  await loadDepartmentsDropdown();
  loadCurrentReport();

  // Tab change handlers
  const tabLinks = document.querySelectorAll('#reportTabs button[data-bs-toggle="tab"]');
  tabLinks.forEach(tab => {
    tab.addEventListener('shown.bs.tab', (e) => {
      activeReportTab = e.target.getAttribute('data-report-type');
      loadCurrentReport();
    });
  });

  // Filter change handlers
  const filters = document.querySelectorAll('.report-filter-input');
  filters.forEach(f => {
    f.addEventListener('change', () => loadCurrentReport());
  });
});

async function loadDepartmentsDropdown() {
  const res = await apiFetch('/departments');
  if (res && res.success) {
    const selects = document.querySelectorAll('.report-dept-dropdown');
    selects.forEach(s => {
      s.innerHTML = `<option value="All">All Departments</option>` +
        res.data.map(d => `<option value="${d.name}">${d.name}</option>`).join('');
    });
  }
}

function loadCurrentReport() {
  if (activeReportTab === 'employees') {
    loadEmployeesReport();
  } else if (activeReportTab === 'attendance') {
    loadAttendanceReport();
  } else if (activeReportTab === 'leaves') {
    loadLeavesReport();
  } else if (activeReportTab === 'payroll') {
    loadPayrollReport();
  }
}

async function loadEmployeesReport() {
  const tbody = document.getElementById('report-employees-tbody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Generating report...</td></tr>`;

  const dept = document.getElementById('rep-emp-dept')?.value || 'All';
  const status = document.getElementById('rep-emp-status')?.value || 'All';

  const res = await apiFetch(`/reports/employees?department=${dept}&status=${status}`);
  if (res && res.success) {
    const { records, summary } = res.data;

    document.getElementById('rep-emp-total').textContent = summary.total_count;
    document.getElementById('rep-emp-active').textContent = summary.active_count;
    document.getElementById('rep-emp-gross').textContent = formatCurrency(summary.total_gross_salary);
    document.getElementById('rep-emp-net').textContent = formatCurrency(summary.total_net_salary);

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No records match criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map(e => `
      <tr>
        <td><strong class="font-monospace text-dark">${e.employee_id}</strong></td>
        <td>
          <div class="fw-semibold text-dark">${e.name}</div>
          <div class="small text-muted">${e.email}</div>
        </td>
        <td>${e.department} - ${e.designation}</td>
        <td><span class="badge bg-light text-muted border">${e.employment_type}</span></td>
        <td><span class="badge-status ${e.status === 'Active' ? 'active' : 'inactive'}">${e.status}</span></td>
        <td class="text-end fw-bold text-dark">${formatCurrency(e.salary?.net || 0)}</td>
      </tr>
    `).join('');
  }
}

async function loadAttendanceReport() {
  const tbody = document.getElementById('report-attendance-tbody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Generating report...</td></tr>`;

  const dept = document.getElementById('rep-att-dept')?.value || 'All';
  const status = document.getElementById('rep-att-status')?.value || 'All';

  const res = await apiFetch(`/reports/attendance?department=${dept}&status=${status}`);
  if (res && res.success) {
    const { records, summary } = res.data;

    document.getElementById('rep-att-total').textContent = summary.total_records;
    document.getElementById('rep-att-present').textContent = summary.present_count;
    document.getElementById('rep-att-absent').textContent = summary.absent_count;
    document.getElementById('rep-att-hours').textContent = `${summary.total_hours} hrs`;

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No attendance records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map(a => `
      <tr>
        <td>${formatDate(a.date)}</td>
        <td><strong class="text-dark">${a.employee_name}</strong> (${a.employee_id})</td>
        <td>${a.department}</td>
        <td><span class="badge-status ${a.status === 'Present' ? 'active' : (a.status === 'Absent' ? 'inactive' : 'late')}">${a.status}</span></td>
        <td>${a.check_in || '-'} to ${a.check_out || '-'}</td>
        <td class="text-end fw-semibold text-dark">${a.working_hours || 0} hrs</td>
      </tr>
    `).join('');
  }
}

async function loadLeavesReport() {
  const tbody = document.getElementById('report-leaves-tbody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Generating report...</td></tr>`;

  const status = document.getElementById('rep-leave-status')?.value || 'All';
  const type = document.getElementById('rep-leave-type')?.value || 'All';

  const res = await apiFetch(`/reports/leaves?status=${status}&type=${type}`);
  if (res && res.success) {
    const { records, summary } = res.data;

    document.getElementById('rep-leave-total').textContent = summary.total_requests;
    document.getElementById('rep-leave-approved').textContent = summary.approved;
    document.getElementById('rep-leave-pending').textContent = summary.pending;
    document.getElementById('rep-leave-days').textContent = `${summary.total_days} days`;

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No leave records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map(l => `
      <tr>
        <td><strong class="text-dark">${l.employee_name}</strong> (${l.employee_id})</td>
        <td><span class="badge bg-light text-dark border">${l.leave_type}</span></td>
        <td>${formatDate(l.start_date)} to ${formatDate(l.end_date)}</td>
        <td><span class="badge bg-primary text-white">${l.days_count} days</span></td>
        <td><span class="badge-status ${l.status === 'Approved' ? 'approved' : (l.status === 'Pending' ? 'pending' : 'rejected')}">${l.status}</span></td>
        <td class="text-end text-muted small">${l.reviewed_by || '-'}</td>
      </tr>
    `).join('');
  }
}

async function loadPayrollReport() {
  const tbody = document.getElementById('report-payroll-tbody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Generating report...</td></tr>`;

  const res = await apiFetch('/reports/payroll');
  if (res && res.success) {
    const { records, summary } = res.data;

    document.getElementById('rep-pay-slips').textContent = summary.total_slips;
    document.getElementById('rep-pay-gross').textContent = formatCurrency(summary.total_gross);
    document.getElementById('rep-pay-tax').textContent = formatCurrency(summary.total_tax);
    document.getElementById('rep-pay-net').textContent = formatCurrency(summary.total_net);

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No payroll entries found.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map(p => `
      <tr>
        <td><strong class="font-monospace text-dark">${p.payroll_id}</strong></td>
        <td><strong class="text-dark">${p.employee_name}</strong> (${p.department})</td>
        <td>${p.month} ${p.year}</td>
        <td>${formatCurrency(p.gross_salary)}</td>
        <td class="text-danger">-${formatCurrency(p.total_deductions)}</td>
        <td class="text-end fw-bold text-success">${formatCurrency(p.net_salary)}</td>
      </tr>
    `).join('');
  }
}

function exportActiveReportCSV() {
  const token = localStorage.getItem('ems_token');
  const url = `${API_BASE}/reports/export-csv?type=${activeReportTab}`;

  // Fetch as blob with auth header to trigger browser download
  fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  .then(res => res.blob())
  .then(blob => {
    const a = document.createElement('a');
    a.href = window.URL.createObjectURL(blob);
    a.download = `${activeReportTab}_report_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast('success', `${activeReportTab.toUpperCase()} CSV Export Downloaded!`);
  })
  .catch(err => {
    console.error(err);
    showToast('error', 'CSV Export failed');
  });
}

function printReport() {
  window.print();
}
