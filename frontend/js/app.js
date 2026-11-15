/**
 * Employee Management System (EMS) - Core Application Script
 */

function getApiBase() {
  if (window.EMS_API_URL) return window.EMS_API_URL;
  
  // If opened directly from file system (file:///...)
  if (window.location.protocol === 'file:') {
    return 'http://localhost:5000/api';
  }
  
  // If served on a dev port other than 5000 (e.g. Live Server 5500, 3000, 8080)
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    if (window.location.port && window.location.port !== '5000') {
      return `http://${window.location.hostname}:5000/api`;
    }
  }
  
  return '/api';
}

const API_BASE = getApiBase();

// Authentication check
function checkAuth(requireAuth = true) {
  const token = localStorage.getItem('ems_token');
  const isLoginPage = window.location.pathname.endsWith('index.html') || window.location.pathname === '/' || window.location.pathname.endsWith('/frontend/');

  if (requireAuth && !token) {
    if (!isLoginPage) {
      window.location.href = 'index.html';
    }
  } else if (!requireAuth && token) {
    if (isLoginPage) {
      window.location.href = 'dashboard.html';
    }
  }
}

// Global API Fetcher
async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('ems_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers
  };

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, config);

    if (res.status === 401) {
      localStorage.removeItem('ems_token');
      localStorage.removeItem('ems_admin');
      if (!window.location.pathname.endsWith('index.html') && window.location.pathname !== '/') {
        window.location.href = 'index.html';
      }
      return null;
    }

    const data = await res.json();
    return data;
  } catch (error) {
    console.error(`API Error on ${endpoint}:`, error);
    showToast('error', 'Network error or server unreachable');
    return { success: false, message: 'Network error or server unreachable' };
  }
}

// SweetAlert2 Toasts
function showToast(icon = 'success', title = '') {
  const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true,
    didOpen: (toast) => {
      toast.addEventListener('mouseenter', Swal.stopTimer);
      toast.addEventListener('mouseleave', Swal.resumeTimer);
    }
  });

  Toast.fire({ icon, title });
}

// Confirm Dialog
async function confirmDialog(title, text, confirmButtonText = 'Yes, Proceed') {
  return await Swal.fire({
    title,
    text,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#2563eb',
    cancelButtonColor: '#64748b',
    confirmButtonText,
    cancelButtonText: 'Cancel',
    reverseButtons: true
  });
}

// Logout function
async function logout() {
  const result = await confirmDialog('Logout Confirmation', 'Are you sure you want to sign out from the EMS admin dashboard?');
  if (result.isConfirmed) {
    try {
      await apiFetch('/auth/logout', { method: 'POST' });
    } catch (e) {
      console.log('Logout error', e);
    }
    localStorage.removeItem('ems_token');
    localStorage.removeItem('ems_admin');
    window.location.href = 'index.html';
  }
}

// Formatters
function formatCurrency(amount, currency = '$') {
  const num = parseFloat(amount || 0);
  return `${currency}${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch (e) {
    return dateStr;
  }
}

// Initialize common UI (Sidebar, Topbar profile, active navigation)
document.addEventListener('DOMContentLoaded', () => {
  const isLoginPage = window.location.pathname.endsWith('index.html') || window.location.pathname === '/' || window.location.pathname.endsWith('/frontend/');
  
  if (!isLoginPage) {
    checkAuth(true);

    // Sidebar Mobile Toggle
    const sidebar = document.querySelector('.app-sidebar');
    const toggleBtns = document.querySelectorAll('.sidebar-toggle-btn');
    const backdrop = document.querySelector('.sidebar-backdrop');

    toggleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        if (sidebar) sidebar.classList.toggle('show-mobile');
        if (backdrop) backdrop.classList.toggle('show');
      });
    });

    if (backdrop) {
      backdrop.addEventListener('click', () => {
        if (sidebar) sidebar.classList.remove('show-mobile');
        backdrop.classList.remove('show');
      });
    }

    // Highlighting Active Nav Link
    const currentPath = window.location.pathname.split('/').pop() || 'dashboard.html';
    const navLinks = document.querySelectorAll('.nav-link-custom');
    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (href && (href === currentPath || (currentPath === '' && href === 'dashboard.html'))) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // Populate admin profile info in topbar/sidebar
    const cachedAdmin = localStorage.getItem('ems_admin');
    if (cachedAdmin) {
      try {
        const admin = JSON.parse(cachedAdmin);
        const nameElems = document.querySelectorAll('.admin-name-display');
        const roleElems = document.querySelectorAll('.admin-role-display');
        const avatarElems = document.querySelectorAll('.admin-avatar-display');

        nameElems.forEach(el => el.textContent = admin.name || 'Admin');
        roleElems.forEach(el => el.textContent = admin.role || 'Super Admin');
        avatarElems.forEach(el => {
          if (admin.avatar) el.src = admin.avatar;
        });
      } catch (e) {}
    }

    // Refresh pending counts in sidebar badges
    refreshSidebarBadges();
  } else {
    checkAuth(false);
  }
});

async function refreshSidebarBadges() {
  try {
    const res = await apiFetch('/dashboard/stats');
    if (res && res.success) {
      const pendingLeaveBadge = document.getElementById('badge-pending-leaves');
      if (pendingLeaveBadge && res.data.pending_leaves > 0) {
        pendingLeaveBadge.textContent = res.data.pending_leaves;
        pendingLeaveBadge.style.display = 'inline-block';
      }
    }
  } catch (e) {}
}
