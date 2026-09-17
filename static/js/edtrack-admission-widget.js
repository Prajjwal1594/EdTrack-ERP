/**
 * EdTrack ERP — Embeddable Admission Widget
 * Allows any external school/college website to collect admission enquiries
 * that sync automatically to the EdTrack ERP Admin & Admissions portal.
 *
 * Usage:
 * <script src="https://ed-track-erp.vercel.app/static/js/edtrack-admission-widget.js"
 *         data-school="YOUR_SCHOOL_CODE"
 *         data-button-text="Apply for Admission"
 *         data-color="#1b3d2f"></script>
 */
(function () {
  'use strict';

  // 1. Locate the script tag and configuration
  var scriptTag = document.currentScript || document.querySelector('script[src*="edtrack-admission-widget.js"]');
  var scriptUrl = scriptTag ? scriptTag.src : 'https://ed-track-erp.vercel.app/';
  var parsedUrl = new URL(scriptUrl, window.location.href);
  var defaultServer = parsedUrl.origin;

  var config = {
    schoolCode: (scriptTag && (scriptTag.getAttribute('data-school') || scriptTag.getAttribute('data-school-code'))) || '',
    serverUrl: (scriptTag && scriptTag.getAttribute('data-server')) || defaultServer,
    buttonText: (scriptTag && scriptTag.getAttribute('data-button-text')) || 'Apply for Admission',
    buttonColor: (scriptTag && scriptTag.getAttribute('data-color')) || '#1b3d2f',
    position: (scriptTag && scriptTag.getAttribute('data-position')) || 'bottom-right',
    hideButton: scriptTag && scriptTag.getAttribute('data-hide-button') === 'true'
  };

  // 2. Inject CSS styles
  var style = document.createElement('style');
  style.id = 'edtrack-widget-styles';
  style.textContent = `
    .edtrack-float-btn {
      position: fixed;
      ${config.position === 'bottom-left' ? 'left: 24px;' : 'right: 24px;'}
      bottom: 24px;
      z-index: 999990;
      background: ${config.buttonColor};
      color: #ffffff;
      padding: 14px 22px;
      border-radius: 50px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.3px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.2);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      border: 2px solid rgba(255, 255, 255, 0.25);
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .edtrack-float-btn:hover {
      transform: translateY(-3px) scale(1.02);
      box-shadow: 0 20px 30px -10px rgba(0, 0, 0, 0.4);
    }
    .edtrack-float-btn svg {
      width: 18px;
      height: 18px;
      fill: currentColor;
    }

    /* Modal Backdrop */
    .edtrack-modal-backdrop {
      display: none;
      position: fixed;
      top: 0; left: 0; width: 100vw; height: 100vh;
      background: rgba(15, 23, 42, 0.65);
      backdrop-filter: blur(6px);
      -webkit-backdrop-filter: blur(6px);
      z-index: 999999;
      align-items: center;
      justify-content: center;
      padding: 16px;
      opacity: 0;
      transition: opacity 0.25s ease;
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .edtrack-modal-backdrop.edtrack-open {
      display: flex;
      opacity: 1;
    }

    /* Modal Card */
    .edtrack-modal-card {
      background: #ffffff;
      color: #1e293b;
      width: 100%;
      max-width: 480px;
      max-height: 90vh;
      overflow-y: auto;
      border-radius: 20px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
      box-sizing: border-box;
      position: relative;
      transform: translateY(20px) scale(0.96);
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .edtrack-modal-backdrop.edtrack-open .edtrack-modal-card {
      transform: translateY(0) scale(1);
    }

    /* Header */
    .edtrack-modal-header {
      background: linear-gradient(135deg, ${config.buttonColor} 0%, #0f172a 100%);
      color: #ffffff;
      padding: 24px 28px;
      border-top-left-radius: 20px;
      border-top-right-radius: 20px;
      position: relative;
    }
    .edtrack-modal-title {
      font-size: 20px;
      font-weight: 700;
      margin: 0 0 4px 0;
    }
    .edtrack-modal-sub {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.85);
      margin: 0;
      line-height: 1.4;
    }
    .edtrack-modal-close {
      position: absolute;
      top: 18px; right: 18px;
      background: rgba(255, 255, 255, 0.15);
      color: #ffffff;
      border: none;
      width: 32px; height: 32px;
      border-radius: 50%;
      font-size: 18px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
    }
    .edtrack-modal-close:hover {
      background: rgba(255, 255, 255, 0.3);
    }

    /* Body */
    .edtrack-modal-body {
      padding: 24px 28px 28px;
    }
    .edtrack-form-group {
      margin-bottom: 16px;
    }
    .edtrack-form-row {
      display: flex;
      gap: 12px;
    }
    .edtrack-form-row .edtrack-form-group {
      flex: 1;
    }
    .edtrack-label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }
    .edtrack-input {
      width: 100%;
      padding: 10px 14px;
      border: 1.5px solid #cbd5e1;
      border-radius: 10px;
      font-size: 14px;
      box-sizing: border-box;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .edtrack-input:focus {
      border-color: ${config.buttonColor};
      box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
    }
    textarea.edtrack-input {
      resize: vertical;
      min-height: 70px;
    }

    .edtrack-submit-btn {
      width: 100%;
      padding: 13px;
      background: ${config.buttonColor};
      color: #ffffff;
      font-size: 15px;
      font-weight: 700;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      margin-top: 8px;
      transition: opacity 0.2s, transform 0.1s;
    }
    .edtrack-submit-btn:hover {
      opacity: 0.95;
    }
    .edtrack-submit-btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    /* Error & Success States */
    .edtrack-alert {
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 14px;
      display: none;
    }
    .edtrack-alert-danger {
      background: #fef2f2;
      color: #dc2626;
      border: 1px solid #fecaca;
    }
    .edtrack-alert-success {
      background: #ecfdf5;
      color: #059669;
      border: 1px solid #a7f3d0;
    }

    .edtrack-success-view {
      text-align: center;
      padding: 30px 10px 10px;
      display: none;
    }
    .edtrack-success-icon {
      width: 64px; height: 64px;
      border-radius: 50%;
      background: #ecfdf5;
      color: #059669;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      margin-bottom: 16px;
    }
    .edtrack-success-title {
      font-size: 20px;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 8px;
    }
    .edtrack-success-desc {
      font-size: 14px;
      color: #64748b;
      margin-bottom: 20px;
      line-height: 1.5;
    }
    .edtrack-footer-brand {
      text-align: center;
      margin-top: 16px;
      font-size: 11px;
      color: #94a3b8;
    }
  `;
  document.head.appendChild(style);

  // 3. Create Modal DOM
  var modalBackdrop = document.createElement('div');
  modalBackdrop.className = 'edtrack-modal-backdrop';
  modalBackdrop.id = 'edtrackAdmissionModal';
  modalBackdrop.innerHTML = `
    <div class="edtrack-modal-card">
      <div class="edtrack-modal-header">
        <button type="button" class="edtrack-modal-close" aria-label="Close">&times;</button>
        <h3 class="edtrack-modal-title" id="edtrackSchoolHeader">Admission Enquiry</h3>
        <p class="edtrack-modal-sub">Submit your details and our admissions team will contact you shortly.</p>
      </div>
      <div class="edtrack-modal-body">
        <div class="edtrack-alert edtrack-alert-danger" id="edtrackErrorBox"></div>

        <form id="edtrackEnquiryForm">
          <div class="edtrack-form-group">
            <label class="edtrack-label">Student Name *</label>
            <input type="text" class="edtrack-input" name="student_name" placeholder="Full name of student" required>
          </div>

          <div class="edtrack-form-group">
            <label class="edtrack-label">Parent / Guardian Name</label>
            <input type="text" class="edtrack-input" name="parent_name" placeholder="Father, mother, or guardian name">
          </div>

          <div class="edtrack-form-row">
            <div class="edtrack-form-group">
              <label class="edtrack-label">Phone / WhatsApp *</label>
              <input type="tel" class="edtrack-input" name="phone" placeholder="e.g. +91 9876543210" required>
            </div>
            <div class="edtrack-form-group">
              <label class="edtrack-label">Email</label>
              <input type="email" class="edtrack-input" name="email" placeholder="name@domain.com">
            </div>
          </div>

          <div class="edtrack-form-group">
            <label class="edtrack-label">Applying For (Grade / Class / Course)</label>
            <input type="text" class="edtrack-input" name="target_class" placeholder="e.g. Grade 5, Class 11, B.Tech, etc.">
          </div>

          <div class="edtrack-form-group">
            <label class="edtrack-label">Message or Questions (Optional)</label>
            <textarea class="edtrack-input" name="notes" placeholder="Any specific requirements, academic background, or questions..."></textarea>
          </div>

          <button type="submit" class="edtrack-submit-btn" id="edtrackSubmitBtn">Submit Enquiry</button>
        </form>

        <div class="edtrack-success-view" id="edtrackSuccessView">
          <div class="edtrack-success-icon">&#10003;</div>
          <div class="edtrack-success-title">Enquiry Received!</div>
          <div class="edtrack-success-desc" id="edtrackSuccessMessage">
            Thank you for applying. We have registered your enquiry and our counselor will reach out to you within 24 hours.
          </div>
          <button type="button" class="edtrack-submit-btn" id="edtrackDoneBtn">Done</button>
        </div>

        <div class="edtrack-footer-brand">Powered by EdTrack ERP Admissions</div>
      </div>
    </div>
  `;
  document.body.appendChild(modalBackdrop);

  // 4. Create Floating Button (if not disabled)
  if (!config.hideButton) {
    var floatBtn = document.createElement('button');
    floatBtn.type = 'button';
    floatBtn.className = 'edtrack-float-btn';
    floatBtn.innerHTML = `
      <svg viewBox="0 0 24 24"><path d="M12 2L1 21h22L12 2zm0 3.8l7.5 13.2H4.5L12 5.8zM11 10v4h2v-4h-2zm0 6v2h2v-2h-2z"/></svg>
      <span>${config.buttonText}</span>
    `;
    floatBtn.addEventListener('click', openModal);
    document.body.appendChild(floatBtn);
  }

  // Bind to any element with data-edtrack-open or class edtrack-admission-trigger
  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-edtrack-open], .edtrack-admission-trigger');
    if (trigger) {
      e.preventDefault();
      var overrideSchool = trigger.getAttribute('data-school') || trigger.getAttribute('data-school-code');
      if (overrideSchool) config.schoolCode = overrideSchool;
      openModal();
    }
  });

  // Modal event listeners
  var closeBtn = modalBackdrop.querySelector('.edtrack-modal-close');
  var doneBtn = document.getElementById('edtrackDoneBtn');
  var form = document.getElementById('edtrackEnquiryForm');
  var errorBox = document.getElementById('edtrackErrorBox');
  var successView = document.getElementById('edtrackSuccessView');
  var submitBtn = document.getElementById('edtrackSubmitBtn');

  closeBtn.addEventListener('click', closeModal);
  doneBtn.addEventListener('click', closeModal);
  modalBackdrop.addEventListener('click', function (e) {
    if (e.target === modalBackdrop) closeModal();
  });

  function openModal() {
    errorBox.style.display = 'none';
    form.style.display = 'block';
    successView.style.display = 'none';
    submitBtn.disabled = false;
    submitBtn.textContent = 'Submit Enquiry';
    modalBackdrop.classList.add('edtrack-open');

    // Fetch school title dynamically if school code is present
    if (config.schoolCode) {
      fetch(`${config.serverUrl}/api/admissions/school-info?school=${encodeURIComponent(config.schoolCode)}`)
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data && data.success && data.school) {
            document.getElementById('edtrackSchoolHeader').textContent = data.school.name + ' — Admissions';
          }
        })
        .catch(function () { /* keep fallback */ });
    }
  }

  function closeModal() {
    modalBackdrop.classList.remove('edtrack-open');
  }

  // Form submission handler
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    errorBox.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    var formData = new FormData(form);
    var payload = {
      school_code: config.schoolCode,
      student_name: formData.get('student_name'),
      parent_name: formData.get('parent_name'),
      phone: formData.get('phone'),
      email: formData.get('email'),
      target_class: formData.get('target_class'),
      notes: formData.get('notes'),
      source: 'Website Widget'
    };

    fetch(`${config.serverUrl}/api/admissions/inquire`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data.success) {
          throw new Error(result.data.error || 'Failed to submit enquiry. Please try again.');
        }

        form.reset();
        form.style.display = 'none';
        successView.style.display = 'block';
        if (result.data.enquiry_id) {
          document.getElementById('edtrackSuccessMessage').textContent =
            `Your enquiry has been registered with reference #ENQ-${String(result.data.enquiry_id).padStart(4, '0')}. Our admissions counselor will contact you shortly.`;
        }
      })
      .catch(function (err) {
        errorBox.textContent = err.message || 'An unexpected error occurred. Please try again.';
        errorBox.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Enquiry';
      });
  });

  // Expose global helper
  window.EdTrackAdmission = {
    open: openModal,
    close: closeModal,
    setSchool: function (code) { config.schoolCode = code; }
  };
})();
