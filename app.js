const STORAGE_KEY = 'rsvp_registrations';
const API_URL = '/api';  // Use relative path - works with Flask
let stripe = null;
let stripeElements = null;

/* STATE  */
let registrations = [];
let deleteTargetId = null;

/* DOM REFS   */
const form        = document.getElementById('regForm');
const editIdInput = document.getElementById('editId');
const submitBtn   = document.getElementById('submitBtn');
const submitLabel = document.getElementById('submitLabel');
const cancelBtn   = document.getElementById('cancelBtn');
const searchInput = document.getElementById('searchInput');
const cardsGrid   = document.getElementById('cardsGrid');
const emptyState  = document.getElementById('emptyState');
const totalCount  = document.getElementById('totalCount');
const exportBtn   = document.getElementById('exportBtn');
const toast       = document.getElementById('toast');
const modalOverlay= document.getElementById('modalOverlay');
const modalName   = document.getElementById('modalName');
const modalCancel = document.getElementById('modalCancel');
const modalConfirm= document.getElementById('modalConfirm');

/* INIT  */
async function init() {
  // Try to load from API first, fall back to localStorage
  try {
    const response = await fetch(`${API_URL}/registrations`);
    if (response.ok) {
      registrations = await response.json();
      console.log('✓ Loaded registrations from server');
    } else {
      throw new Error('API not available');
    }
  } catch (error) {
    console.warn('API not available, using localStorage:', error);
    const stored = localStorage.getItem(STORAGE_KEY);
    registrations = stored ? JSON.parse(stored) : [];
  }

  renderCards();
  checkPaymentSuccess();
}

/* CHECK PAYMENT SUCCESS */
function checkPaymentSuccess() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('payment') === 'success') {
    showToast('✓ Payment successful! Your ticket has been sent to your email.');
    window.history.replaceState({}, document.title, window.location.pathname);
  } else if (urlParams.get('payment') === 'cancelled') {
    showToast('Payment cancelled. Please try again.');
  }
}

/* PERSIST */
function save() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(registrations));
}

/* PAYMENT MODAL */
const paymentModal = document.getElementById('paymentModal');
const paymentCancel = document.getElementById('paymentCancel');
const stripeBtn = document.getElementById('stripeBtn');
const complimentaryBtn = document.getElementById('complimentaryBtn');
let currentFormData = null;

function showPaymentModal(formData) {
  currentFormData = formData;
  const ticketPrices = {
    'General': '$50.00',
    'VIP': '$100.00',
    'Student': '$25.00',
  };
  const price = ticketPrices[formData.ticket] || '$50.00';
  document.getElementById('paymentModalSubtitle').textContent = `${formData.ticket} Ticket - ${price}`;
  paymentModal.classList.add('open');
}

function closePaymentModal() {
  paymentModal.classList.remove('open');
  currentFormData = null;
}

paymentCancel.addEventListener('click', closePaymentModal);
paymentModal.addEventListener('click', (e) => {
  if (e.target === paymentModal) closePaymentModal();
});

/* STRIPE PAYMENT   */
stripeBtn.addEventListener('click', async () => {
  try {
    closePaymentModal();
    showToast('Redirecting to payment...');

    const response = await fetch(`${API_URL}/registrations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...currentFormData,
        paymentMethod: 'stripe',
      }),
    });

    const data = await response.json();

    if (data.redirectUrl) {
      // Redirect to Stripe checkout
      window.location.href = data.redirectUrl;
    } else {
      showToast('Error initiating payment');
    }
  } catch (error) {
    console.error('Payment error:', error);
    showToast('Payment error: ' + error.message);
  }
});

/* COMPLIMENTARY / CASH PAYMENT*/
complimentaryBtn.addEventListener('click', async () => {
  try {
    closePaymentModal();
    showToast('Processing registration...');

    const response = await fetch(`${API_URL}/registrations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...currentFormData,
        paymentMethod: 'cash',
      }),
    });

    const data = await response.json();

    if (data.success) {
      showToast('✓ Registration successful! Check your email for your ticket.');
      resetForm();
      // Reload registrations from API
      const regsResponse = await fetch(`${API_URL}/registrations`);
      if (regsResponse.ok) {
        registrations = await regsResponse.json();
      }
      renderCards();
    } else {
      showToast('Error: ' + (data.error || 'Unknown error'));
    }
  } catch (error) {
    console.error('Registration error:', error);
    showToast('Error: ' + error.message);
  }
});


function clearErrors() {
  document.querySelectorAll('.field-group').forEach(fg => fg.classList.remove('has-error'));
  document.querySelectorAll('.field-error').forEach(el => el.textContent = '');
}

function setError(fieldId, errId, msg) {
  document.getElementById(fieldId).classList.add('has-error');
  document.getElementById(errId).textContent = msg;
}

function validate(data) {
  clearErrors();
  let valid = true;

  if (!data.name.trim()) {
    setError('fg-name', 'err-name', 'Name is required.');
    valid = false;
  }

  const emailRx = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!data.email.trim()) {
    setError('fg-email', 'err-email', 'Email is required.');
    valid = false;
  } else if (!emailRx.test(data.email)) {
    setError('fg-email', 'err-email', 'Enter a valid email address.');
    valid = false;
  }

  if (!data.ticket) {
    setError('fg-ticket', 'err-ticket', 'Select a ticket type.');
    valid = false;
  }

  if (data.sessions.length === 0) {
    setError('fg-sessions', 'err-sessions', 'Select at least one session.');
    valid = false;
  }

  if (!data.payment) {
    setError('fg-payment', 'err-payment', 'Select a payment status.');
    valid = false;
  }

  return valid;
}

/* READ FORM */
function readForm() {
  const ticketRadio  = document.querySelector('input[name="ticket"]:checked');
  const paymentRadio = document.querySelector('input[name="payment"]:checked');
  const sessionBoxes = [...document.querySelectorAll('input[name="session"]:checked')];

  return {
    name:     document.getElementById('name').value.trim(),
    email:    document.getElementById('email').value.trim(),
    ticket:   ticketRadio  ? ticketRadio.value  : '',
    dietary:  document.getElementById('dietary').value,
    sessions: sessionBoxes.map(cb => cb.value),
    payment:  paymentRadio ? paymentRadio.value : '',
  };
}

/*RESET FORM  */
function resetForm() {
  form.reset();
  clearErrors();
  editIdInput.value = '';
  submitLabel.textContent = 'Register Attendee';
  cancelBtn.style.display = 'none';
  // uncheck all radios/checkboxes explicitly
  document.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(el => el.checked = false);
}

/* POPULATE FORM FOR EDIT*/
function populateForm(reg) {
  document.getElementById('name').value  = reg.name;
  document.getElementById('email').value = reg.email;
  document.getElementById('dietary').value = reg.dietary;

  document.querySelectorAll('input[name="ticket"]').forEach(r => {
    r.checked = r.value === reg.ticket;
  });

  document.querySelectorAll('input[name="payment"]').forEach(r => {
    r.checked = r.value === reg.payment;
  });

  document.querySelectorAll('input[name="session"]').forEach(cb => {
    cb.checked = reg.sessions.includes(cb.value);
  });

  editIdInput.value = reg.id;
  submitLabel.textContent = 'Save Changes';
  cancelBtn.style.display = 'block';
  form.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* SUBMIT   */
form.addEventListener('submit', (e) => {
  e.preventDefault();
  const data = readForm();

  if (!validate(data)) return;

  // Show payment modal
  showPaymentModal(data);
});

/* CANCEL EDIT */
cancelBtn.addEventListener('click', () => {
  resetForm();
});

/* RENDER CARDS */
function renderCards(filter = '') {
  const q = filter.toLowerCase().trim();

  const filtered = registrations.filter(r =>
    !q ||
    r.name.toLowerCase().includes(q) ||
    r.email.toLowerCase().includes(q) ||
    r.ticket.toLowerCase().includes(q) ||
    r.payment.toLowerCase().includes(q) ||
    r.dietary.toLowerCase().includes(q) ||
    r.sessions.some(s => s.toLowerCase().includes(q))
  );

  totalCount.textContent = `${registrations.length} registration${registrations.length !== 1 ? 's' : ''}`;

  if (filtered.length === 0) {
    emptyState.style.display = 'block';
    cardsGrid.innerHTML = '';
    if (registrations.length > 0 && q) {
      emptyState.querySelector('p').textContent = `No results for "${filter}".`;
    } else {
      emptyState.querySelector('p').innerHTML = 'No registrations yet.<br/>Fill out the form to add your first attendee.';
    }
    return;
  }

  emptyState.style.display = 'none';
  cardsGrid.innerHTML = filtered.map(r => buildCard(r)).join('');

  // Bind card buttons
  cardsGrid.querySelectorAll('.btn-edit').forEach(btn => {
    btn.addEventListener('click', () => handleEdit(btn.dataset.id));
  });
  cardsGrid.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', () => handleDeletePrompt(btn.dataset.id));
  });
}

/*BUILD CARD HTML */
function buildCard(r) {
  const ts = new Date(r.timestamp);
  const dateStr = ts.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
  const timeStr = ts.toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit' });

  const sessionPills = r.sessions.map(s =>
    `<span class="session-pill">${s}</span>`
  ).join('');

  const ticketBadge  = `<span class="badge badge-ticket-${r.ticket}">${r.ticket}</span>`;
  const paymentBadge = `<span class="badge badge-pay-${r.payment}">${r.payment}</span>`;

  const dietaryLabel = r.dietary && r.dietary !== 'None'
    ? `🍽 ${r.dietary}`
    : '🍽 No requirements';

  return `
    <div class="reg-card" data-ticket="${r.ticket}" data-id="${r.id}">
      <div class="card-top">
        <div>
          <div class="card-name">${escHtml(r.name)}</div>
          <div class="card-email">${escHtml(r.email)}</div>
        </div>
        <div class="card-badges">
          ${ticketBadge}
          ${paymentBadge}
        </div>
      </div>

      <div class="card-sessions">
        ${sessionPills || '<span class="session-pill">No sessions</span>'}
      </div>

      <div class="card-meta">
        <span class="card-dietary">${dietaryLabel}</span>
        <span class="card-ts">${dateStr} · ${timeStr}</span>
      </div>

      <div class="card-actions">
        <button class="btn-edit" data-id="${r.id}">Edit</button>
        <button class="btn-delete" data-id="${r.id}">Remove</button>
      </div>
    </div>
  `;
}

/* EDIT  */
function handleEdit(id) {
  const reg = registrations.find(r => r.id === id);
  if (!reg) return;
  populateForm(reg);
}

/* DELETE   */
function handleDeletePrompt(id) {
  const reg = registrations.find(r => r.id === id);
  if (!reg) return;
  deleteTargetId = id;
  modalName.textContent = reg.name;
  modalOverlay.classList.add('open');
}

modalCancel.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', (e) => {
  if (e.target === modalOverlay) closeModal();
});

modalConfirm.addEventListener('click', async () => {
  try {
    const response = await fetch(`${API_URL}/registrations/${deleteTargetId}`, {
      method: 'DELETE',
    });

    if (response.ok) {
      registrations = registrations.filter(r => r.id !== deleteTargetId);
      save();
      renderCards(searchInput.value);
      closeModal();
      showToast('Registration removed.');
    } else {
      showToast('Error deleting registration');
    }
  } catch (error) {
    console.error('Delete error:', error);
    registrations = registrations.filter(r => r.id !== deleteTargetId);
    save();
    renderCards(searchInput.value);
    closeModal();
    showToast('Registration removed (local).');
  }
});

function closeModal() {
  modalOverlay.classList.remove('open');
  deleteTargetId = null;
}

/* SEARCH   */
searchInput.addEventListener('input', () => {
  renderCards(searchInput.value);
});

/*CSV EXPORT */
exportBtn.addEventListener('click', () => {
  if (registrations.length === 0) {
    showToast('No registrations to export.');
    return;
  }

  const headers = ['Name', 'Email', 'Ticket Type', 'Dietary Requirements', 'Sessions', 'Payment Status', 'Timestamp'];

  const rows = registrations.map(r => [
    csvCell(r.name),
    csvCell(r.email),
    csvCell(r.ticket),
    csvCell(r.dietary),
    csvCell(r.sessions.join(' | ')),
    csvCell(r.payment),
    csvCell(new Date(r.timestamp).toLocaleString('en-AU')),
  ]);

  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `registrations_${datestamp()}.csv`;
  a.click();
  URL.revokeObjectURL(url);

  showToast(`Exported ${registrations.length} registration${registrations.length !== 1 ? 's' : ''}.`);
});

/* HELPERS*/
function csvCell(val) {
  const str = String(val ?? '');
  return str.includes(',') || str.includes('"') || str.includes('\n')
    ? `"${str.replace(/"/g, '""')}"`
    : str;
}

function datestamp() {
  const d = new Date();
  return `${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}`;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

let toastTimer;
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
}

/* BOOT */
init();