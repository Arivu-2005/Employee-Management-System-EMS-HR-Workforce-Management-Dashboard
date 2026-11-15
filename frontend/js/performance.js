/**
 * EMS - Performance Module
 */

document.addEventListener('DOMContentLoaded', async () => {
  await loadEmployeesDropdown();
  await loadPerformanceAnalytics();
  await loadReviews();

  // Filters
  const deptFilter = document.getElementById('filter-perf-department');
  const ratingFilter = document.getElementById('filter-perf-rating');

  [deptFilter, ratingFilter].forEach(el => {
    if (el) {
      el.addEventListener('change', () => loadReviews());
    }
  });

  // Review Form Submit
  const form = document.getElementById('reviewForm');
  if (form) {
    form.addEventListener('submit', handleReviewFormSubmit);
  }
});

async function loadEmployeesDropdown() {
  const res = await apiFetch('/employees?limit=100');
  if (res && res.success) {
    const select = document.getElementById('rev-employee-id');
    if (select) {
      select.innerHTML = `<option value="" disabled selected>Select Employee</option>` +
        res.data.employees.map(e => `<option value="${e.employee_id}">${e.name} (${e.employee_id}) - ${e.department}</option>`).join('');
    }

    const deptSelect = document.getElementById('filter-perf-department');
    if (deptSelect) {
      const deptsRes = await apiFetch('/departments');
      if (deptsRes && deptsRes.success) {
        deptSelect.innerHTML = `<option value="All">All Departments</option>` +
          deptsRes.data.map(d => `<option value="${d.name}">${d.name}</option>`).join('');
      }
    }
  }
}

async function loadPerformanceAnalytics() {
  const res = await apiFetch('/performance/analytics');
  if (res && res.success) {
    const a = res.data;
    document.getElementById('perf-kpi-rating').textContent = `${a.org_avg_rating} / 5.0`;
    document.getElementById('perf-kpi-productivity').textContent = `${a.org_avg_productivity}%`;
    document.getElementById('perf-kpi-total').textContent = a.total_reviews;

    // Top performers preview
    const topContainer = document.getElementById('top-performers-container');
    if (topContainer && a.top_performers) {
      topContainer.innerHTML = a.top_performers.map(p => `
        <div class="d-flex align-items-center justify-content-between p-2 bg-light rounded mb-2">
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-primary text-white">${p.rating} ★</span>
            <div>
              <div class="fw-semibold text-dark small">${p.employee_name}</div>
              <div class="text-muted" style="font-size: 0.72rem;">${p.department}</div>
            </div>
          </div>
          <span class="text-success fw-bold small">${p.productivity_score}%</span>
        </div>
      `).join('');
    }
  }
}

async function loadReviews() {
  const tbody = document.getElementById('performance-table-body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading performance reviews...</td></tr>`;

  const dept = document.getElementById('filter-perf-department')?.value || 'All';
  const rating = document.getElementById('filter-perf-rating')?.value || 'All';

  const queryParams = new URLSearchParams({
    department: dept,
    rating
  });

  const res = await apiFetch(`/performance?${queryParams.toString()}`);
  if (res && res.success) {
    const reviews = res.data;

    if (reviews.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted">No evaluations found. Click "Add Evaluation" to record a performance review.</td></tr>`;
      return;
    }

    tbody.innerHTML = reviews.map(rev => {
      let stars = '';
      for (let i = 1; i <= 5; i++) {
        stars += `<i class="bi bi-star${i <= rev.rating ? '-fill text-warning' : ' text-muted'}"></i> `;
      }

      return `
        <tr>
          <td>
            <div class="fw-semibold text-dark">${rev.employee_name}</div>
            <div class="small font-monospace text-muted">${rev.employee_id} • ${rev.department || '-'}</div>
          </td>
          <td>
            <span class="badge bg-light text-dark border">${rev.review_period}</span>
          </td>
          <td>
            <div class="d-inline-flex align-items-center">${stars}</div>
          </td>
          <td>
            <div class="d-flex align-items-center gap-2">
              <div class="progress flex-grow-1" style="height: 6px; width: 60px;">
                <div class="progress-bar bg-success" style="width: ${rev.productivity_score}%"></div>
              </div>
              <span class="fw-semibold text-dark small">${rev.productivity_score}%</span>
            </div>
          </td>
          <td>
            <span class="small text-muted">${formatDate(rev.review_date)}</span>
            <div class="text-muted" style="font-size: 0.72rem;">By ${rev.reviewer_name || 'Admin'}</div>
          </td>
          <td style="max-width: 250px;">
            <div class="text-muted small text-truncate" title="${escapeHtml(rev.remarks || '')}">${rev.remarks || '-'}</div>
          </td>
          <td class="text-end">
            <button class="btn-action-icon text-danger" title="Delete Review" onclick="deleteReview('${rev._id}')">
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }
}

function openAddReviewModal() {
  const form = document.getElementById('reviewForm');
  if (form) form.reset();

  document.getElementById('rev-date').value = new Date().toISOString().split('T')[0];
  document.getElementById('rev-period').value = 'Q4 2026';
  document.getElementById('rev-rating').value = '5';
  document.getElementById('rev-productivity').value = '95';
  document.getElementById('rev-task-completion').value = '98';

  const modal = new bootstrap.Modal(document.getElementById('reviewModal'));
  modal.show();
}

async function handleReviewFormSubmit(e) {
  e.preventDefault();

  const payload = {
    employee_id: document.getElementById('rev-employee-id').value,
    review_period: document.getElementById('rev-period').value.trim(),
    rating: parseInt(document.getElementById('rev-rating').value),
    productivity_score: parseFloat(document.getElementById('rev-productivity').value),
    task_completion_rate: parseFloat(document.getElementById('rev-task-completion').value),
    review_date: document.getElementById('rev-date').value,
    remarks: document.getElementById('rev-remarks').value.trim()
  };

  const res = await apiFetch('/performance', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  if (res && res.success) {
    showToast('success', 'Performance evaluation saved!');
    const modalEl = document.getElementById('reviewModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();

    loadPerformanceAnalytics();
    loadReviews();
  } else {
    Swal.fire({
      icon: 'error',
      title: 'Action Failed',
      text: res ? res.message : 'Could not save review.',
      confirmButtonColor: '#2563eb'
    });
  }
}

async function deleteReview(id) {
  const confirm = await confirmDialog('Delete Review?', 'Are you sure you want to delete this performance review?');
  if (confirm.isConfirmed) {
    const res = await apiFetch(`/performance/${id}`, { method: 'DELETE' });
    if (res && res.success) {
      showToast('success', 'Review deleted.');
      loadPerformanceAnalytics();
      loadReviews();
    }
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}
