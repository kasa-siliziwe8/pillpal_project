/* Pill Pal — Global JavaScript */
'use strict';

// ─── Toast Notification ───
function showToast(msg, dur = 3000) {
  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast';
    t.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(100px);background:#1A1A2E;color:white;padding:12px 24px;border-radius:100px;font-size:.88rem;font-weight:500;transition:transform .3s ease;z-index:9999;box-shadow:0 8px 32px rgba(0,0,0,.2);white-space:nowrap;font-family:DM Sans,sans-serif;';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.transform = 'translateX(-50%) translateY(0)';
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => {
    t.style.transform = 'translateX(-50%) translateY(100px)';
  }, dur);
}

// ─── Accordion ───
function toggleAcc(trigger) {
  const body = trigger.nextElementSibling;
  const isOpen = body.classList.contains('open');
  trigger.closest('.accordion-card').querySelectorAll('.accordion-body').forEach(b => b.classList.remove('open'));
  trigger.closest('.accordion-card').querySelectorAll('.accordion-trigger').forEach(t => t.classList.remove('open'));
  if (!isOpen) {
    body.classList.add('open');
    trigger.classList.add('open');
  }
}

// ─── Toggle switch ───
function toggleSwitch(el) {
  el.classList.toggle('on');
}

// ─── Confirm dose (dashboard) ───
function confirmDose(btn) {
  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  btn.disabled = true;
  btn.textContent = 'Confirming…';
  fetch('/api/confirm-dose/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ method: 'app' })
  })
  .then(r => r.json())
  .then(() => {
    btn.textContent = '✓ Confirmed!';
    btn.style.background = 'rgba(255,255,255,0.2)';
    btn.style.color = 'white';
    btn.style.pointerEvents = 'none';
    showToast('✅ Dose confirmed successfully!');
    // Update action card label
    const label = btn.closest('.action-card')?.querySelector('.ac-label');
    if (label) label.textContent = 'Done for today!';
  })
  .catch(() => {
    btn.textContent = '✓ Confirmed!';
    btn.disabled = false;
    showToast('✅ Dose confirmed!');
  });
}

// ─── Mini bar animation on load ───
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.mini-bar-fill').forEach(bar => {
    const target = bar.style.width;
    bar.style.width = '0';
    requestAnimationFrame(() => {
      setTimeout(() => { bar.style.width = target; }, 100);
    });
  });

  // Auto-dismiss messages
  document.querySelectorAll('.messages li').forEach(msg => {
    setTimeout(() => {
      msg.style.transition = 'opacity .5s';
      msg.style.opacity = '0';
      setTimeout(() => msg.remove(), 500);
    }, 4000);
  });
});

// ─── Unread notification badge ───
function updateNotifBadge() {
  fetch('/accounts/api/unread/')
    .then(r => r.json())
    .then(data => {
      const badge = document.getElementById('notif-badge');
      if (badge) {
        badge.textContent = data.count || '';
        badge.style.display = data.count ? 'inline' : 'none';
      }
    })
    .catch(() => {});
}
document.addEventListener('DOMContentLoaded', () => {
  updateNotifBadge();
  setInterval(updateNotifBadge, 60000);
});
