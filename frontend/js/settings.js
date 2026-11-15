/**
 * EMS - Admin Settings Module
 */

document.addEventListener('DOMContentLoaded', async () => {
  await loadAdminProfile();
  await loadCompanySettings();

  // Profile Form
  const profileForm = document.getElementById('adminProfileForm');
  if (profileForm) {
    profileForm.addEventListener('submit', handleProfileUpdate);
  }

  // Password Form
  const passwordForm = document.getElementById('changePasswordForm');
  if (passwordForm) {
    passwordForm.addEventListener('submit', handlePasswordChange);
  }

  // Company Settings Form
  const companyForm = document.getElementById('companySettingsForm');
  if (companyForm) {
    companyForm.addEventListener('submit', handleCompanySettingsUpdate);
  }
});

async function loadAdminProfile() {
  const res = await apiFetch('/auth/profile');
  if (res && res.success) {
    const admin = res.data;
    document.getElementById('admin-profile-name').value = admin.name || '';
    document.getElementById('admin-profile-email').value = admin.email || '';
    document.getElementById('admin-profile-phone').value = admin.phone || '';
    document.getElementById('admin-profile-avatar').value = admin.avatar || '';

    const avatarPreview = document.getElementById('admin-avatar-preview');
    if (avatarPreview && admin.avatar) {
      avatarPreview.src = admin.avatar;
    }
  }
}

async function loadCompanySettings() {
  const res = await apiFetch('/settings');
  if (res && res.success) {
    const c = res.data;
    document.getElementById('comp-name').value = c.company_name || '';
    document.getElementById('comp-email').value = c.company_email || '';
    document.getElementById('comp-phone').value = c.company_phone || '';
    document.getElementById('comp-address').value = c.company_address || '';
    document.getElementById('comp-website').value = c.company_website || '';
    document.getElementById('comp-currency').value = c.currency || 'USD';
    document.getElementById('comp-casual-leaves').value = c.casual_leaves_allowed ?? 12;
    document.getElementById('comp-sick-leaves').value = c.sick_leaves_allowed ?? 10;
    document.getElementById('comp-earned-leaves').value = c.earned_leaves_allowed ?? 15;
  }
}

async function handleProfileUpdate(e) {
  e.preventDefault();

  const payload = {
    name: document.getElementById('admin-profile-name').value.trim(),
    phone: document.getElementById('admin-profile-phone').value.trim(),
    avatar: document.getElementById('admin-profile-avatar').value.trim()
  };

  const res = await apiFetch('/auth/profile', {
    method: 'PUT',
    body: JSON.stringify(payload)
  });

  if (res && res.success) {
    showToast('success', 'Admin profile updated successfully!');
    localStorage.setItem('ems_admin', JSON.stringify(res.data));

    // Update avatar preview and UI elements
    const avatarPreview = document.getElementById('admin-avatar-preview');
    if (avatarPreview && res.data.avatar) {
      avatarPreview.src = res.data.avatar;
    }
    document.querySelectorAll('.admin-name-display').forEach(el => el.textContent = res.data.name);
    document.querySelectorAll('.admin-avatar-display').forEach(el => {
      if (res.data.avatar) el.src = res.data.avatar;
    });
  } else {
    Swal.fire({
      icon: 'error',
      title: 'Update Failed',
      text: res ? res.message : 'Could not update profile.',
      confirmButtonColor: '#2563eb'
    });
  }
}

async function handlePasswordChange(e) {
  e.preventDefault();

  const curPassword = document.getElementById('admin-cur-password').value;
  const newPassword = document.getElementById('admin-new-password').value;
  const confirmPassword = document.getElementById('admin-confirm-password').value;

  if (newPassword !== confirmPassword) {
    Swal.fire({
      icon: 'warning',
      title: 'Mismatch',
      text: 'New password and confirmation do not match.',
      confirmButtonColor: '#2563eb'
    });
    return;
  }

  const res = await apiFetch('/auth/change-password', {
    method: 'PUT',
    body: JSON.stringify({
      current_password: curPassword,
      new_password: newPassword
    })
  });

  if (res && res.success) {
    Swal.fire({
      icon: 'success',
      title: 'Password Updated',
      text: 'Your security password has been changed successfully.',
      confirmButtonColor: '#2563eb'
    });
    document.getElementById('changePasswordForm').reset();
  } else {
    Swal.fire({
      icon: 'error',
      title: 'Change Failed',
      text: res ? res.message : 'Current password incorrect.',
      confirmButtonColor: '#2563eb'
    });
  }
}

async function handleCompanySettingsUpdate(e) {
  e.preventDefault();

  const payload = {
    company_name: document.getElementById('comp-name').value.trim(),
    company_email: document.getElementById('comp-email').value.trim(),
    company_phone: document.getElementById('comp-phone').value.trim(),
    company_address: document.getElementById('comp-address').value.trim(),
    company_website: document.getElementById('comp-website').value.trim(),
    currency: document.getElementById('comp-currency').value,
    casual_leaves_allowed: parseInt(document.getElementById('comp-casual-leaves').value || 12),
    sick_leaves_allowed: parseInt(document.getElementById('comp-sick-leaves').value || 10),
    earned_leaves_allowed: parseInt(document.getElementById('comp-earned-leaves').value || 15)
  };

  const res = await apiFetch('/settings', {
    method: 'PUT',
    body: JSON.stringify(payload)
  });

  if (res && res.success) {
    showToast('success', 'Organization settings saved successfully!');
  } else {
    Swal.fire({
      icon: 'error',
      title: 'Save Failed',
      text: res ? res.message : 'Could not save company settings.',
      confirmButtonColor: '#2563eb'
    });
  }
}

async function triggerResetDemoData() {
  const confirm = await Swal.fire({
    title: 'Reset Demo Dataset?',
    text: 'This action will restore all standard demonstration records (employees, departments, attendance, payroll, leaves, and activity logs). Any changes you made will be re-initialized.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#ef4444',
    cancelButtonColor: '#64748b',
    confirmButtonText: 'Yes, Reset Demo Data',
    cancelButtonText: 'Cancel'
  });

  if (confirm.isConfirmed) {
    Swal.fire({
      title: 'Resetting Data...',
      text: 'Seeding high-fidelity demonstration records...',
      allowOutsideClick: false,
      didOpen: () => {
        Swal.showLoading();
      }
    });

    const res = await apiFetch('/settings/reset-demo-data', { method: 'POST' });
    if (res && res.success) {
      Swal.fire({
        icon: 'success',
        title: 'Demo Data Restored',
        text: 'System successfully re-seeded with demonstration datasets!',
        confirmButtonColor: '#2563eb'
      }).then(() => {
        window.location.href = 'dashboard.html';
      });
    } else {
      Swal.fire({
        icon: 'error',
        title: 'Reset Failed',
        text: res ? res.message : 'Could not reset demo data.',
        confirmButtonColor: '#2563eb'
      });
    }
  }
}
