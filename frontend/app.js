const API = "http://127.0.0.1:5000";
let token = localStorage.getItem("token") || null;

function showSection(id) {
  document.querySelectorAll(".section").forEach(s => s.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
  if (id === "browse") loadBooks();
  if (id === "cart") loadCart();
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
      <div>
        <strong>${b.title}</strong> by ${b.author}<br/>
        $${b.price.toFixed(2)} - ${b.stock_quantity} in stock
      </div>

      <div>
        ${
          b.stock_quantity <= 0
            ? `<span style="color:red;font-weight:bold;">Out of Stock</span`
            : b.stock_quantity <= 2
              ? `<span style="color:orange;"Low Stock</span>`
              :`span style="color green;">In Stock</span>`
      }
    </div>

    <button
      onclick="addToCart(${b.id})"
      ${b.stock_quantity <= 0 ? "disabled" : ""}
    >
      $b.stock_quantity <= 0 ? "Unavailable" : "Add to Cart"}
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
    localStorage.setItem("token", token);
    document.getElementById("login-message").textContent = `Logged in as ${data.role}`;
  } else {
    document.getElementById("login-message").textContent = data.error;
  }
}

function authHeaders() {
  return { Authorization: `Bearer ${token}` };
}

// Load browse on start
showSection("browse");
