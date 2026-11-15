/**
 * EMS - Dashboard Logic & Analytics
 */

let deptChart = null;
let attendanceChart = null;
let payrollChart = null;

document.addEventListener('DOMContentLoaded', async () => {
  await loadDashboardStats();
  await loadDashboardAnalytics();
  await loadRecentActivities();
});

async function loadDashboardStats() {
  const res = await apiFetch('/dashboard/stats');
  if (res && res.success) {
    const stats = res.data;

    document.getElementById('stat-total-employees').textContent = stats.total_employees;
    document.getElementById('stat-active-employees').textContent = `${stats.active_employees} Active`;
    document.getElementById('stat-total-departments').textContent = stats.total_departments;
    document.getElementById('stat-today-attendance').textContent = `${stats.today_attendance.present} / ${stats.total_employees}`;
    document.getElementById('stat-attendance-rate').textContent = `${stats.today_attendance.rate}% Present`;
    document.getElementById('stat-on-leave').textContent = stats.on_leave_employees;
    document.getElementById('stat-pending-leaves').textContent = stats.pending_leaves;
    document.getElementById('stat-monthly-payroll').textContent = formatCurrency(stats.monthly_payroll.total_net);
    document.getElementById('stat-payroll-month').textContent = `${stats.monthly_payroll.month} ${stats.monthly_payroll.year}`;
  }
}

async function loadDashboardAnalytics() {
  const res = await apiFetch('/dashboard/analytics');
  if (res && res.success) {
    const data = res.data;

    // 1. Department Distribution (Doughnut)
    const ctxDept = document.getElementById('chartDepartmentDistribution');
    if (ctxDept) {
      if (deptChart) deptChart.destroy();
      deptChart = new Chart(ctxDept, {
        type: 'doughnut',
        data: {
          labels: data.department_distribution.labels,
          datasets: [{
            data: data.department_distribution.data,
            backgroundColor: [
              '#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'
            ],
            borderWidth: 2,
            borderColor: '#ffffff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { boxWidth: 12, padding: 15, font: { family: 'Inter', size: 12 } } }
          },
          cutout: '70%'
        }
      });
    }

    // 2. Attendance Trend (Line Chart)
    const ctxAtt = document.getElementById('chartAttendanceTrend');
    if (ctxAtt) {
      if (attendanceChart) attendanceChart.destroy();
      attendanceChart = new Chart(ctxAtt, {
        type: 'line',
        data: {
          labels: data.attendance_trend.labels,
          datasets: [
            {
              label: 'Present',
              data: data.attendance_trend.present,
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              tension: 0.35,
              fill: true,
              pointRadius: 4
            },
            {
              label: 'Absent',
              data: data.attendance_trend.absent,
              borderColor: '#ef4444',
              backgroundColor: 'transparent',
              tension: 0.35,
              borderDash: [5, 5],
              pointRadius: 3
            },
            {
              label: 'On Leave',
              data: data.attendance_trend.leave,
              borderColor: '#06b6d4',
              backgroundColor: 'transparent',
              tension: 0.35,
              pointRadius: 3
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { stepSize: 1 } },
            x: { grid: { display: false } }
          },
          plugins: {
            legend: { position: 'top', align: 'end', labels: { boxWidth: 12 } }
          }
        }
      });
    }

    // 3. Payroll Trend (Bar Chart)
    const ctxPay = document.getElementById('chartPayrollTrend');
    if (ctxPay) {
      if (payrollChart) payrollChart.destroy();
      payrollChart = new Chart(ctxPay, {
        type: 'bar',
        data: {
          labels: data.payroll_trend.labels,
          datasets: [{
            label: 'Net Payroll ($)',
            data: data.payroll_trend.data,
            backgroundColor: '#2563eb',
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: '#f1f5f9' },
              ticks: {
                callback: function(val) { return '$' + (val / 1000) + 'k'; }
              }
            },
            x: { grid: { display: false } }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }
  }
}

async function loadRecentActivities() {
  const container = document.getElementById('recent-activities-list');
  if (!container) return;

  const res = await apiFetch('/dashboard/activities');
  if (res && res.success && res.data.length > 0) {
    container.innerHTML = res.data.map(act => `
      <div class="d-flex align-items-start gap-3 py-2 border-bottom">
        <div class="stat-icon info flex-shrink-0" style="width: 36px; height: 36px; font-size: 1rem;">
          <i class="bi bi-clock-history"></i>
        </div>
        <div class="flex-grow-1">
          <div class="d-flex justify-content-between align-items-center">
            <h6 class="mb-0 fw-semibold text-dark small">${act.action}</h6>
            <span class="text-muted" style="font-size: 0.72rem;">${formatDate(act.created_at)}</span>
          </div>
          <p class="text-muted small mb-0 mt-1">${act.details}</p>
        </div>
      </div>
    `).join('');
  } else {
    container.innerHTML = `<div class="text-center text-muted py-4 small">No recent activity logs found.</div>`;
  }
}
