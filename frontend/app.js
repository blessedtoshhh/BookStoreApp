const API = "";
let token = localStorage.getItem("token") || null;
let userRole = localStorage.getItem("role") || null;

function showSection(id) {
  document.querySelectorAll(".section").forEach(s => s.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
  if (id === "browse") loadBooks();
  if (id === "cart") loadCart();
  if (id === "inventory") loadInventory();
  if (id === "orders") loadAllOrders();
  if (id === "feedback") initFeedbackForm();
  if (id === "staff-feedback") loadStaffFeedback();
  if (id === "reviews") loadPublicReviews();
  if (id === "login-activity") loadLoginActivity();
}

function applyRoleUI() {
  const isEmployee = userRole === "employee" || userRole === "manager";
  document.getElementById("nav-login").classList.toggle("hidden", !!token);
  document.getElementById("nav-logout").classList.toggle("hidden", !token);
  document.getElementById("nav-reviews").classList.toggle("hidden", isEmployee);
  document.getElementById("nav-inventory").classList.toggle("hidden", !isEmployee);
  document.getElementById("nav-orders").classList.toggle("hidden", !isEmployee);
  document.getElementById("nav-staff-feedback").classList.toggle("hidden", !isEmployee);
  document.getElementById("nav-login-activity").classList.toggle("hidden", userRole !== "manager");
}

function logout() {
  token = null;
  userRole = null;
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  applyRoleUI();
  showSection("browse");
}

// --- Books ---

async function loadBooks(query = "", type = "all") {
  let url = `${API}/books/`;
  if (query) {
    url += `?q=${encodeURIComponent(query)}&type=${type}`;
  }
  
  const res = await fetch(url);
  const books = await res.json();
  const list = document.getElementById("book-list");
  list.innerHTML = books.map(b => `
    <div class="book-card">
      <div class="book-cover">
        <img
          src="${b.cover_url || 'https://via.placeholder.com/150x220?text=Book'}"
          alt="${b.title}"
        />
      </div>

        <div class="book-info">
        <strong>${b.title}</strong><br/>
        by ${b.author_name}<br/>
        $${b.price.toFixed(2)} &mdash; ${b.stock_quantity} in stock
      </div>

      <div>
        ${
          b.stock_quantity <= 0
            ? `<span style="color:red;font-weight:bold;">Special Order</span>`
            : b.stock_quantity <= 2
              ? `<span style="color:orange;">Low Stock</span>`
              : `<span style="color:green;">In Stock</span>`
        }
      </div>
      <button
        onclick="addToCart(${b.id})"
        ${b.stock_quantity <= 0 ? "disabled" : ""}
      >
        ${b.stock_quantity <= 0 ? "Unavailable" : "Add to Cart"}
      </button>
    </div>
  `).join("");
}

function searchBooks() {
  const q = document.getElementById("search-input").value;
  const type = document.getElementById("search-type").value;

  loadBooks(q, type);
}

// --- Cart ---

async function loadCart() {
  if (!token) { alert("Please log in first."); showSection("login"); return; }
  const res = await fetch(`${API}/store/cart`, { headers: authHeaders() });
  const cart = await res.json();
  const el = document.getElementById("cart-items");
  el.innerHTML = cart.items.map(i => `
    <div class="cart-item">
      <span>${i.title} x${i.quantity}</span>
      <span>$${i.subtotal.toFixed(2)}
        <button onclick="removeFromCart(${i.cart_item_id})" style="margin-left:8px;background:#e74c3c;color:white;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;">X</button>
      </span>
    </div>
  `).join("") || "<p>Your cart is empty.</p>";
  document.getElementById("cart-total").textContent = cart.total.toFixed(2);
  document.getElementById("cart-count").textContent = cart.items.length;
}

async function addToCart(bookId) {
  if (!token) { alert("Please log in first."); showSection("login"); return; }
  const res = await fetch(`${API}/store/cart`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ book_id: bookId, quantity: 1 }),
  });
  if (res.ok) {
    const cart = await res.json();
    document.getElementById("cart-count").textContent = cart.items.length;
    alert("Added to cart!");
  } else {
    const err = await res.json();
    alert(err.error || "Could not add to cart.");
  }
}

async function removeFromCart(itemId) {
  await fetch(`${API}/store/cart/${itemId}`, { method: "DELETE", headers: authHeaders() });
  loadCart();
}

async function checkout() {
  if (!token) { alert("Please log in first."); return; }
  const res = await fetch(`${API}/store/checkout`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ payment_method: "credit_card" }),
  });
  const data = await res.json();
  if (res.ok) {
    alert(`Order #${data.order_id} placed! Total: $${data.total.toFixed(2)}`);
    loadCart();
  } else {
    alert(data.error || "Checkout failed.");
  }
}

// --- Auth ---

async function login() {
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (res.ok) {
    token = data.token;
    userRole = data.role;
    localStorage.setItem("token", token);
    localStorage.setItem("role", userRole);
    applyRoleUI();
    showSection("browse");
  } else {
    document.getElementById("login-message").textContent = data.error;
  }
}

function authHeaders() {
  return { Authorization: `Bearer ${token}` };
}

// --- Employee: Inventory ---

function showAddBookForm() {
  document.getElementById("add-book-form").classList.toggle("hidden");
}

async function loadInventory() {
  const res = await fetch(`${API}/books/`);
  const books = await res.json();
  document.getElementById("inventory-list").innerHTML = books.map(b => `
    <div class="book-card">
      <div>
        <strong>${b.title}</strong> by ${b.author}<br/>
        Category: ${b.category || "N/A"} &mdash; ISBN: ${b.isbn || "N/A"}<br/>
        $${b.price.toFixed(2)} &mdash; Stock: ${b.stock_quantity}
      </div>
      <div>
        <label>Update Stock:</label>
        <input type="number" id="stock-${b.id}" value="${b.stock_quantity}" style="width:60px;" />
        <button onclick="updateStock(${b.id})">Save</button>
      </div>
    </div>
  `).join("");
}

async function updateStock(bookId) {
  const qty = parseInt(document.getElementById(`stock-${bookId}`).value);
  await fetch(`${API}/books/${bookId}`, {
    method: "PUT",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ stock_quantity: qty }),
  });
  loadInventory();
}

async function addBook() {
  const body = {
    title: document.getElementById("book-title").value,
    author_name: document.getElementById("book-author").value,
    isbn: document.getElementById("book-isbn").value,
    price: parseFloat(document.getElementById("book-price").value),
    stock_quantity: parseInt(document.getElementById("book-stock").value),
    category: document.getElementById("book-category").value,
    description: document.getElementById("book-description").value,
  };
  const res = await fetch(`${API}/books/`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const msg = document.getElementById("add-book-message");
  if (res.ok) {
    msg.textContent = "Book added successfully.";
    loadInventory();
  } else {
    const err = await res.json();
    msg.textContent = err.error || "Failed to add book.";
  }
}

// --- Employee: Orders ---

async function loadAllOrders() {
  const res = await fetch(`${API}/store/orders`, { headers: authHeaders() });
  const orders = await res.json();
  document.getElementById("orders-list").innerHTML = orders.length ? orders.map(o => `
    <div class="book-card">
      <strong>Order #${o.order_id}</strong> &mdash; Status: ${o.status} &mdash; Total: $${o.total.toFixed(2)}<br/>
      <small>${o.created_at}</small>
      <ul>
        ${o.items.map(i => `<li>${i.title} x${i.quantity} @ $${i.price_at_purchase.toFixed(2)}</li>`).join("")}
      </ul>
    </div>
  `).join("") : "<p>No orders found.</p>";
}

// --- Feedback ---

let selectedRating = 0;

function initFeedbackForm() {
  selectedRating = 0;
  document.getElementById("feedback-message").value = "";
  document.getElementById("feedback-message-status").textContent = "";
  document.getElementById("feedback-category").value = "general";

  const nameField = document.getElementById("feedback-name");
  const emailField = document.getElementById("feedback-email");
  const guestFields = document.getElementById("feedback-guest-fields");

  if (token) {
    guestFields.style.display = "none";
  } else {
    guestFields.style.display = "block";
    nameField.value = "";
    emailField.value = "";
  }

  updateStars(0);

  document.querySelectorAll(".star").forEach(star => {
    star.onmouseover = () => updateStars(parseInt(star.dataset.value));
    star.onmouseout = () => updateStars(selectedRating);
    star.onclick = () => {
      selectedRating = parseInt(star.dataset.value);
      updateStars(selectedRating);
      const labels = ["", "Poor", "Fair", "Good", "Very Good", "Excellent"];
      document.getElementById("rating-label").textContent = labels[selectedRating];
    };
  });
}

function updateStars(value) {
  document.querySelectorAll(".star").forEach(star => {
    star.classList.toggle("active", parseInt(star.dataset.value) <= value);
  });
}

async function submitFeedback() {
  const message = document.getElementById("feedback-message").value.trim();
  const status = document.getElementById("feedback-message-status");

  if (!selectedRating) {
    status.style.color = "#e74c3c";
    status.textContent = "Please select a rating.";
    return;
  }
  if (!message) {
    status.style.color = "#e74c3c";
    status.textContent = "Please enter a message.";
    return;
  }

  const body = {
    rating: selectedRating,
    category: document.getElementById("feedback-category").value,
    message,
  };

  if (!token) {
    body.name = document.getElementById("feedback-name").value.trim();
    body.email = document.getElementById("feedback-email").value.trim();
  }

  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API}/feedback/`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const data = await res.json();

  if (res.ok) {
    status.style.color = "#27ae60";
    status.textContent = data.message || "Thank you for your feedback!";
    selectedRating = 0;
    updateStars(0);
    document.getElementById("rating-label").textContent = "Select a rating";
    document.getElementById("feedback-message").value = "";
    document.getElementById("feedback-category").value = "general";
    if (!token) {
      document.getElementById("feedback-name").value = "";
      document.getElementById("feedback-email").value = "";
    }
  } else {
    status.style.color = "#e74c3c";
    status.textContent = data.error || "Could not submit feedback.";
  }
}

let currentFeedbackFilter = "all";

async function loadStaffFeedback(statusFilter) {
  if (!token) return;
  if (statusFilter !== undefined) currentFeedbackFilter = statusFilter;

  const url = currentFeedbackFilter === "all"
    ? `${API}/feedback/`
    : `${API}/feedback/?status=${currentFeedbackFilter}`;

  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) return;
  const data = await res.json();
  const { entries, counts } = data;

  const listEl = document.getElementById("staff-feedback-list");
  const summaryEl = document.getElementById("feedback-summary");

  const allEntries = counts.all;
  const avg = allEntries > 0
    ? (entries.reduce((sum, e) => sum + e.rating, 0) / (entries.length || 1)).toFixed(1)
    : null;

  const globalAvgRes = await fetch(`${API}/feedback/`, { headers: authHeaders() });
  const globalData = await globalAvgRes.json();
  const globalAvg = globalData.counts.all > 0
    ? (globalData.entries.reduce((sum, e) => sum + e.rating, 0) / globalData.entries.length).toFixed(1)
    : null;

  summaryEl.innerHTML = `
    <div class="feedback-summary-bar">
      ${globalAvg !== null ? `
        <span class="summary-avg">${globalAvg} <span class="stars-inline">${"&#9733;".repeat(Math.round(globalAvg))}${"&#9734;".repeat(5 - Math.round(globalAvg))}</span></span>
        <span style="color:#555;margin-left:0.8rem;">Average rating &mdash; ${globalData.counts.all} total review${globalData.counts.all !== 1 ? "s" : ""}</span>
      ` : `<span style="color:#888;">No feedback yet.</span>`}
    </div>
    <div class="feedback-filter-tabs">
      <button class="filter-tab ${currentFeedbackFilter === "all" ? "active" : ""}" onclick="loadStaffFeedback('all')">
        All <span class="filter-count">${counts.all}</span>
      </button>
      <button class="filter-tab filter-tab-new ${currentFeedbackFilter === "new" ? "active" : ""}" onclick="loadStaffFeedback('new')">
        New <span class="filter-count">${counts.new}</span>
      </button>
      <button class="filter-tab filter-tab-reviewed ${currentFeedbackFilter === "reviewed" ? "active" : ""}" onclick="loadStaffFeedback('reviewed')">
        Reviewed <span class="filter-count">${counts.reviewed}</span>
      </button>
      <button class="filter-tab filter-tab-actioned ${currentFeedbackFilter === "actioned" ? "active" : ""}" onclick="loadStaffFeedback('actioned')">
        Actioned <span class="filter-count">${counts.actioned}</span>
      </button>
    </div>
  `;

  if (!entries.length) {
    listEl.innerHTML = `<p style="color:#888;margin-top:1rem;">No feedback in this category.</p>`;
    return;
  }

  const categoryLabels = { general: "General", selection: "Book Selection", service: "Customer Service", website: "Website Experience", other: "Other" };

  listEl.innerHTML = entries.map(f => `
    <div class="feedback-card" id="fcard-${f.id}">
      <div class="feedback-card-header">
        <div>
          <strong>${escapeHtml(f.name)}</strong>
          ${f.email ? `<span style="color:#888;font-size:0.85rem;margin-left:0.5rem;">${escapeHtml(f.email)}</span>` : ""}
        </div>
        <div style="text-align:right;display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;justify-content:flex-end;">
          <span class="feedback-stars">${"&#9733;".repeat(f.rating)}${"&#9734;".repeat(5 - f.rating)}</span>
          <span class="feedback-badge">${categoryLabels[f.category] || f.category}</span>
          <span class="status-badge status-${f.status}">${f.status.charAt(0).toUpperCase() + f.status.slice(1)}</span>
        </div>
      </div>
      <p class="feedback-card-message">${escapeHtml(f.message)}</p>
      <div class="feedback-note-row">
        <textarea class="internal-note-input" id="note-${f.id}" placeholder="Add internal note... (shown publicly as 'Our Response' when marked Actioned)">${escapeHtml(f.internal_note)}</textarea>
      </div>
      <div class="feedback-actions">
        <small style="color:#aaa;">Received: ${f.created_at}</small>
        <div class="action-buttons">
          <button class="action-btn btn-reviewed ${f.status === "reviewed" ? "btn-active" : ""}" onclick="updateFeedbackStatus(${f.id}, 'reviewed')">Mark Reviewed</button>
          <button class="action-btn btn-actioned ${f.status === "actioned" ? "btn-active" : ""}" onclick="updateFeedbackStatus(${f.id}, 'actioned')">Mark Actioned</button>
          ${f.status !== "new" ? `<button class="action-btn btn-reset" onclick="updateFeedbackStatus(${f.id}, 'new')">Reset</button>` : ""}
          <button class="action-btn btn-save-note" onclick="saveFeedbackNote(${f.id})">Save Note</button>
        </div>
      </div>
    </div>
  `).join("");
}

async function updateFeedbackStatus(id, status) {
  const res = await fetch(`${API}/feedback/${id}`, {
    method: "PATCH",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (res.ok) loadStaffFeedback();
}

async function saveFeedbackNote(id) {
  const note = document.getElementById(`note-${id}`).value;
  const res = await fetch(`${API}/feedback/${id}`, {
    method: "PATCH",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ internal_note: note }),
  });
  if (res.ok) {
    const card = document.getElementById(`fcard-${id}`);
    const indicator = document.createElement("span");
    indicator.textContent = " Saved!";
    indicator.style.cssText = "color:#27ae60;font-size:0.85rem;";
    const btn = card.querySelector(".btn-save-note");
    btn.after(indicator);
    setTimeout(() => indicator.remove(), 2000);
  }
}

// --- Manager: Login Activity ---

async function loadLoginActivity() {
  if (!token || userRole !== "manager") return;
  const res = await fetch(`${API}/auth/login-activity`, { headers: authHeaders() });
  if (!res.ok) return;
  const rows = await res.json();

  const statsEl = document.getElementById("login-activity-stats");
  const listEl = document.getElementById("login-activity-list");

  const total = rows.length;
  const failed = rows.filter(r => !r.success).length;

  statsEl.innerHTML = `<p style="color:#555;">${total} attempts &mdash; <span style="color:#27ae60;">${total - failed} successful</span>, <span style="color:#e74c3c;">${failed} failed</span></p>`;

  if (!total) {
    listEl.innerHTML = `<p style="color:#888;">No login activity recorded yet.</p>`;
    return;
  }

  listEl.innerHTML = `
    <table class="activity-table">
      <thead>
        <tr>
          <th>Timestamp</th>
          <th>Email</th>
          <th>Name</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        ${rows.map(r => `
          <tr>
            <td>${escapeHtml(r.timestamp)}</td>
            <td>${escapeHtml(r.email)}</td>
            <td>${r.user_name ? escapeHtml(r.user_name) : "—"}</td>
            <td><span class="activity-badge ${r.success ? "badge-success" : "badge-fail"}">${r.success ? "Success" : "Failed"}</span></td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

// --- Public Reviews ---

async function loadPublicReviews() {
  const res = await fetch(`${API}/feedback/public`);
  if (!res.ok) return;
  const data = await res.json();
  const { entries, avg, total } = data;

  const summaryEl = document.getElementById("reviews-summary");
  const listEl = document.getElementById("reviews-list");

  const isCustomer = token && userRole === "customer";
  const cta = document.getElementById("feedback-cta");
  if (cta) cta.classList.toggle("hidden", !isCustomer);

  if (!total) {
    summaryEl.innerHTML = `<p style="color:#888;margin-bottom:1rem;">No feedback has been published yet. Be the first to share your experience!</p>`;
    listEl.innerHTML = "";
    return;
  }

  const starsFull = Math.round(avg);
  summaryEl.innerHTML = `
    <div class="reviews-hero">
      <div class="reviews-hero-score">
        <span class="reviews-avg-number">${avg}</span>
        <span class="reviews-hero-stars">${"&#9733;".repeat(starsFull)}${"&#9734;".repeat(5 - starsFull)}</span>
        <span class="reviews-hero-label">${total} published review${total !== 1 ? "s" : ""}</span>
      </div>
      <p class="reviews-hero-note">All reviews below have been read and acknowledged by our team. Responses marked with a reply icon reflect actions we've taken.</p>
    </div>
  `;

  const categoryLabels = { general: "General", selection: "Book Selection", service: "Customer Service", website: "Website Experience", other: "Other" };

  listEl.innerHTML = entries.map(f => `
    <div class="review-card">
      <div class="review-card-top">
        <div class="review-meta">
          <span class="review-author">${escapeHtml(f.name)}</span>
          <span class="review-date">${f.created_at}</span>
        </div>
        <div class="review-right">
          <span class="review-stars">${"&#9733;".repeat(f.rating)}${"&#9734;".repeat(5 - f.rating)}</span>
          <span class="review-cat-badge">${categoryLabels[f.category] || f.category}</span>
        </div>
      </div>
      <p class="review-message">${escapeHtml(f.message)}</p>
      ${f.response ? `
        <div class="store-response">
          <span class="store-response-label">&#128172; Our Response</span>
          <p class="store-response-text">${escapeHtml(f.response)}</p>
        </div>
      ` : ""}
    </div>
  `).join("");
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Init
applyRoleUI();
showSection("browse");
