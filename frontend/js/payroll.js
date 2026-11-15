/**
 * EMS - Payroll & Salary Module
 */

document.addEventListener('DOMContentLoaded', async () => {
  // Populate month and year dropdowns
  setupMonthYearFilters();
  await loadEmployeesDropdown();
  await loadPayrollRecords();

  // Filter change listeners
  const monthFilter = document.getElementById('filter-payroll-month');
  const yearFilter = document.getElementById('filter-payroll-year');
  const statusFilter = document.getElementById('filter-payroll-status');

  [monthFilter, yearFilter, statusFilter].forEach(el => {
    if (el) {
      el.addEventListener('change', () => loadPayrollRecords());
    }
  });

  // Generate Payroll Form Submit
  const form = document.getElementById('generatePayrollForm');
  if (form) {
    form.addEventListener('submit', handleGeneratePayrollSubmit);
  }
});

function setupMonthYearFilters() {
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const currentMonth = months[new Date().getMonth()];
  const currentYear = new Date().getFullYear();

  const filterMonth = document.getElementById('filter-payroll-month');
  const genMonth = document.getElementById('gen-payroll-month');
  const filterYear = document.getElementById('filter-payroll-year');
  const genYear = document.getElementById('gen-payroll-year');

  if (filterMonth && genMonth) {
    const opts = months.map(m => `<option value="${m}" ${m === currentMonth ? 'selected' : ''}>${m}</option>`).join('');
    filterMonth.innerHTML = `<option value="All">All Months</option>` + opts;
    genMonth.innerHTML = opts;
  }

  if (filterYear && genYear) {
    const years = [currentYear, currentYear - 1, currentYear - 2];
    const opts = years.map(y => `<option value="${y}" ${y === currentYear ? 'selected' : ''}>${y}</option>`).join('');
    filterYear.innerHTML = `<option value="All">All Years</option>` + opts;
    genYear.innerHTML = opts;
  }
}

async function loadEmployeesDropdown() {
  const res = await apiFetch('/employees?status=Active&limit=100');
  if (res && res.success) {
    const select = document.getElementById('gen-employee-id');
    if (select) {
      select.innerHTML = `<option value="ALL" selected>⚡ All Active Employees (Batch Run)</option>` +
        res.data.employees.map(e => `<option value="${e.employee_id}">${e.name} (${e.employee_id}) - ${e.department}</option>`).join('');
    }
  }
}

async function loadPayrollRecords() {
  const tbody = document.getElementById('payroll-table-body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading payroll records...</td></tr>`;

  const month = document.getElementById('filter-payroll-month')?.value || 'All';
  const year = document.getElementById('filter-payroll-year')?.value || 'All';
  const status = document.getElementById('filter-payroll-status')?.value || 'All';

  const queryParams = new URLSearchParams({
    month,
    year,
    status
  });

  const res = await apiFetch(`/payroll?${queryParams.toString()}`);
  if (res && res.success) {
    const records = res.data;

    let totalGross = 0;
    let totalDeductions = 0;
    let totalNet = 0;

    records.forEach(r => {
      totalGross += (r.gross_salary || 0);
      totalDeductions += (r.total_deductions || 0);
      totalNet += (r.net_salary || 0);
    });

    document.getElementById('payroll-kpi-gross').textContent = formatCurrency(totalGross);
    document.getElementById('payroll-kpi-deductions').textContent = formatCurrency(totalDeductions);
    document.getElementById('payroll-kpi-net').textContent = formatCurrency(totalNet);
    document.getElementById('payroll-kpi-slips').textContent = `${records.length} Issued`;

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-5 text-muted">No payroll records found for the selected period. Click "Generate Payroll" to run calculation.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map(p => {
      let badgeClass = 'paid';
      if (p.payment_status === 'Unpaid') badgeClass = 'unpaid';
      else if (p.payment_status === 'Processing') badgeClass = 'processing';

      return `
        <tr>
          <td>
            <span class="badge bg-light text-dark border font-monospace" style="font-size: 0.72rem;">${p.payroll_id}</span>
          </td>
          <td>
            <div class="fw-semibold text-dark">${p.employee_name}</div>
            <div class="small font-monospace text-muted">${p.employee_id} • ${p.department || '-'}</div>
          </td>
          <td>
            <span class="fw-medium text-dark">${p.month} ${p.year}</span>
          </td>
          <td>
            <span class="text-dark">${formatCurrency(p.basic_salary)}</span>
          </td>
          <td>
            <span class="text-dark">${formatCurrency(p.gross_salary)}</span>
            ${p.overtime_pay > 0 ? `<div class="text-muted small" style="font-size: 0.7rem;">+${formatCurrency(p.overtime_pay)} OT</div>` : ''}
          </td>
          <td>
            <span class="text-danger">-${formatCurrency(p.total_deductions)}</span>
          </td>
          <td>
            <span class="fw-bold text-success">${formatCurrency(p.net_salary)}</span>
          </td>
          <td class="text-end">
            <div class="d-inline-flex gap-1">
              <button class="btn btn-sm btn-outline-custom" title="View & Print Salary Slip" onclick="viewSalarySlip('${p._id || p.payroll_id}')">
                <i class="bi bi-receipt"></i> Payslip
              </button>
              <button class="btn-action-icon text-danger" title="Delete Record" onclick="deletePayroll('${p._id || p.payroll_id}')">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }
}

function openGeneratePayrollModal() {
  const modal = new bootstrap.Modal(document.getElementById('generatePayrollModal'));
  modal.show();
}

async function handleGeneratePayrollSubmit(e) {
  e.preventDefault();

  const month = document.getElementById('gen-payroll-month').value;
  const year = parseInt(document.getElementById('gen-payroll-year').value);
  const empId = document.getElementById('gen-employee-id').value;
  const otHours = parseFloat(document.getElementById('gen-ot-hours').value || 0);
  const bonus = parseFloat(document.getElementById('gen-bonus').value || 0);

  const payload = {
    month,
    year,
    employee_id: empId,
    overtime_hours: otHours,
    bonus: bonus
  };

  const submitBtn = document.getElementById('btnSubmitPayroll');
  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Calculating & Generating...`;

  try {
    const res = await apiFetch('/payroll/generate', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res && res.success) {
      Swal.fire({
        icon: 'success',
        title: 'Payroll Generated',
        text: res.message,
        confirmButtonColor: '#2563eb'
      });

      const modalEl = document.getElementById('generatePayrollModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();

      loadPayrollRecords();
    } else {
      Swal.fire({
        icon: 'warning',
        title: 'Generation Notice',
        text: res ? res.message : 'Could not generate payroll.',
        confirmButtonColor: '#2563eb'
      });
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<i class="bi bi-gear-fill"></i> Execute Payroll Generation`;
  }
}

async function viewSalarySlip(id) {
  const res = await apiFetch(`/payroll/${id}/slip`);
  if (res && res.success) {
    const { payroll, employee, company } = res.data;
    const container = document.getElementById('salary-slip-content');

    container.innerHTML = `
      <div class="salary-slip-container shadow-sm">
        <div class="slip-header">
          <div class="slip-company-name">${company.company_name || 'Apex Enterprise Solutions'}</div>
          <div class="text-muted small">${company.company_address || '100 Tech Boulevard, Suite 500, San Francisco, CA'}</div>
          <div class="text-muted small">Email: ${company.company_email || 'hr@apexenterprise.io'} | Phone: ${company.company_phone || '+1 (800) 555-0199'}</div>
          <div class="slip-title">CONFIDENTIAL SALARY PAYSLIP</div>
          <div class="small fw-semibold text-dark">Pay Period: ${payroll.month} ${payroll.year}</div>
        </div>

        <div class="row g-3 small mb-4 pb-3 border-bottom">
          <div class="col-6">
            <div><span class="text-muted">Employee Name:</span> <strong class="text-dark">${payroll.employee_name}</strong></div>
            <div><span class="text-muted">Employee ID:</span> <strong class="text-dark">${payroll.employee_id}</strong></div>
            <div><span class="text-muted">Department:</span> <strong class="text-dark">${payroll.department}</strong></div>
            <div><span class="text-muted">Designation:</span> <strong class="text-dark">${payroll.designation}</strong></div>
          </div>
          <div class="col-6 text-end">
            <div><span class="text-muted">Payslip ID:</span> <strong class="font-monospace text-dark">${payroll.payroll_id}</strong></div>
            <div><span class="text-muted">Payment Date:</span> <strong class="text-dark">${formatDate(payroll.payment_date)}</strong></div>
            <div><span class="text-muted">Disbursement:</span> <strong class="text-dark">${payroll.payment_method || 'Bank Transfer'}</strong></div>
            <div><span class="text-muted">Status:</span> <span class="badge bg-success text-white">${payroll.payment_status}</span></div>
          </div>
        </div>

        <div class="row g-4 mb-4">
          <!-- Earnings -->
          <div class="col-6">
            <h6 class="fw-bold text-dark border-bottom pb-2 mb-2">Earnings</h6>
            <table class="table table-sm table-borderless small">
              <tbody>
                <tr>
                  <td>Basic Salary</td>
                  <td class="text-end fw-semibold">${formatCurrency(payroll.basic_salary)}</td>
                </tr>
                <tr>
                  <td>House Rent Allowance (HRA)</td>
                  <td class="text-end fw-semibold">${formatCurrency(payroll.hra)}</td>
                </tr>
                <tr>
                  <td>Special Allowances</td>
                  <td class="text-end fw-semibold">${formatCurrency(payroll.allowances)}</td>
                </tr>
                <tr>
                  <td>Overtime (${payroll.overtime_hours || 0} hrs)</td>
                  <td class="text-end fw-semibold">${formatCurrency(payroll.overtime_pay || 0)}</td>
                </tr>
                <tr>
                  <td>Performance Bonus</td>
                  <td class="text-end fw-semibold">${formatCurrency(payroll.bonus || 0)}</td>
                </tr>
                <tr class="border-top">
                  <td class="fw-bold">Total Gross Earnings</td>
                  <td class="text-end fw-bold text-primary">${formatCurrency(payroll.gross_salary)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Deductions -->
          <div class="col-6">
            <h6 class="fw-bold text-dark border-bottom pb-2 mb-2">Deductions</h6>
            <table class="table table-sm table-borderless small">
              <tbody>
                <tr>
                  <td>Income Tax / TDS</td>
                  <td class="text-end fw-semibold text-danger">-${formatCurrency(payroll.tax_deductions)}</td>
                </tr>
                <tr>
                  <td>Provident Fund / Insurance</td>
                  <td class="text-end fw-semibold text-danger">-${formatCurrency(payroll.other_deductions)}</td>
                </tr>
                <tr class="border-top">
                  <td class="fw-bold">Total Deductions</td>
                  <td class="text-end fw-bold text-danger">-${formatCurrency(payroll.total_deductions)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Net Payable -->
        <div class="p-3 bg-light rounded d-flex justify-content-between align-items-center mb-4 border">
          <div>
            <div class="text-muted small">NET SALARY PAYABLE</div>
            <div class="fw-semibold text-dark small">Disbursed via Direct Bank Deposit</div>
          </div>
          <div class="text-end">
            <div class="fs-4 fw-bold text-success">${formatCurrency(payroll.net_salary)}</div>
          </div>
        </div>

        <div class="d-flex justify-content-between text-muted small pt-3 border-top" style="font-size: 0.72rem;">
          <div>System Generated Document • Apex EMS Cloud</div>
          <div>Authorized Signature: ______________________</div>
        </div>
      </div>
    `;

    const modal = new bootstrap.Modal(document.getElementById('salarySlipModal'));
    modal.show();
  }
}

function printSalarySlip() {
  window.print();
}

async function deletePayroll(id) {
  const confirm = await confirmDialog('Delete Payroll Record?', 'Are you sure you want to delete this payroll entry?');
  if (confirm.isConfirmed) {
    const res = await apiFetch(`/payroll/${id}`, { method: 'DELETE' });
    if (res && res.success) {
      showToast('success', 'Payroll record deleted.');
      loadPayrollRecords();
    }
  }
}
