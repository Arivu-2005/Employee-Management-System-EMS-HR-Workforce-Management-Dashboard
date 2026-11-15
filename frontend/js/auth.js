/**
 * EMS - Authentication Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  checkAuth(false);

  const loginForm = document.getElementById('loginForm');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const rememberCheckbox = document.getElementById('rememberMe');
  const togglePasswordBtn = document.getElementById('togglePassword');
  const demoFillBtn = document.getElementById('demoFillBtn');
  const submitBtn = document.getElementById('submitBtn');

  // Toggle Password Visibility
  if (togglePasswordBtn && passwordInput) {
    togglePasswordBtn.addEventListener('click', () => {
      const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
      passwordInput.setAttribute('type', type);
      const icon = togglePasswordBtn.querySelector('i');
      if (icon) {
        icon.classList.toggle('bi-eye');
        icon.classList.toggle('bi-eye-slash');
      }
    });
  }

  // Pre-fill remembered email if available
  const savedEmail = localStorage.getItem('ems_remembered_email');
  if (savedEmail && emailInput) {
    emailInput.value = savedEmail;
    if (rememberCheckbox) rememberCheckbox.checked = true;
  }

  // Quick Demo Credentials Fill
  if (demoFillBtn && emailInput && passwordInput) {
    demoFillBtn.addEventListener('click', () => {
      emailInput.value = 'admin@ems.com';
      passwordInput.value = 'admin123';
      showToast('info', 'Demo credentials loaded!');
    });
  }

  // Form Submit
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = emailInput.value.trim();
      const password = passwordInput.value;
      const rememberMe = rememberCheckbox ? rememberCheckbox.checked : false;

      // Basic client validation
      if (!email || !password) {
        Swal.fire({
          icon: 'warning',
          title: 'Required Fields',
          text: 'Please enter both your administrator email and password.',
          confirmButtonColor: '#2563eb'
        });
        return;
      }

      // Show loading
      const originalText = submitBtn.innerHTML;
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span> Authenticating...`;

      try {
        const res = await apiFetch('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email, password, remember_me: rememberMe })
        });

        if (res && res.success) {
          localStorage.setItem('ems_token', res.data.token);
          localStorage.setItem('ems_admin', JSON.stringify(res.data));

          if (rememberMe) {
            localStorage.setItem('ems_remembered_email', email);
          } else {
            localStorage.removeItem('ems_remembered_email');
          }

          Swal.fire({
            icon: 'success',
            title: 'Welcome Back!',
            text: `Signed in as ${res.data.name}`,
            timer: 1500,
            showConfirmButton: false
          }).then(() => {
            window.location.href = 'dashboard.html';
          });
        } else {
          Swal.fire({
            icon: 'error',
            title: 'Authentication Failed',
            text: res ? res.message : 'Invalid credentials. Please verify your email and password.',
            confirmButtonColor: '#2563eb'
          });
        }
      } catch (err) {
        console.error(err);
        Swal.fire({
          icon: 'error',
          title: 'System Error',
          text: 'Unable to connect to the authentication server.',
          confirmButtonColor: '#2563eb'
        });
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
      }
    });
  }
});
