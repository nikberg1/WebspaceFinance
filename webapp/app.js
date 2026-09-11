const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor("#071428");
  tg.setBackgroundColor("#071428");
}

const MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];

const state = {
  month: currentMonth(),
  formType: "income",
  accounts: [],
  editAccountId: null,
};

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function money(n) {
  return `${Number(n || 0).toLocaleString("ru-RU")} ₽`;
}

function initData() {
  return tg?.initData || "dev";
}

async function api(path, options = {}) {
  const auth = initData();
  const sep = path.includes("?") ? "&" : "?";
  const url = `${path}${sep}_auth=${encodeURIComponent(auth)}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `tma ${auth}`,
      "X-Telegram-Init-Data": auth,
      ...(options.headers || {}),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? "Проверьте поля формы" : (data.detail || "Ошибка запроса");
    throw new Error(detail);
  }
  return data;
}

function shiftMonth(delta) {
  const [y, m] = state.month.split("-").map(Number);
  const date = new Date(y, m - 1 + delta, 1);
  state.month = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  renderMonth();
  load();
}

function renderMonth() {
  const [y, m] = state.month.split("-").map(Number);
  document.getElementById("monthLabel").textContent = `${MONTHS[m - 1]} ${y}`;
}

function setText(id, value, extraClass) {
  const el = document.getElementById(id);
  el.textContent = value;
  if (extraClass !== undefined) el.classList.toggle("neg", extraClass);
}

function statusLabel(status) {
  if (status === "paid") return "оплачено";
  if (status === "plan") return "план";
  return "просрочено";
}

function fillAccountSelect() {
  const select = document.getElementById("account");
  select.innerHTML = state.accounts
    .map((a) => `<option value="${a.id}">${a.name}</option>`)
    .join("");
}

function renderAccounts(accounts) {
  state.accounts = accounts;
  fillAccountSelect();
  const box = document.getElementById("accounts");
  box.innerHTML = accounts
    .map(
      (a) => `
      <button class="account" type="button" data-acc="${a.id}">
        <div>
          <small>${a.name}</small>
          <strong class="${a.balance < 0 ? "neg" : ""}">${money(a.balance)}</strong>
        </div>
        <span class="item-meta">изменить</span>
      </button>
    `
    )
    .join("");
}

function renderList(items) {
  const list = document.getElementById("list");
  const empty = document.getElementById("empty");
  list.innerHTML = "";
  empty.classList.toggle("hidden", items.length > 0);
  items.forEach((item) => {
    const el = document.createElement("article");
    el.className = "item";
    const sign = item.type === "income" ? "+" : "−";
    el.innerHTML = `
      <div class="item-top">
        <div>
          <div>${item.category}</div>
          <div class="item-meta">${item.account_name || "счёт"} · ${item.op_date} · <span class="badge ${item.status}">${statusLabel(item.status)}</span></div>
        </div>
        <div class="item-amount ${item.type}">${sign} ${money(item.amount_rub)}</div>
      </div>
      ${item.comment ? `<div class="item-comment">${item.comment}</div>` : ""}
      <div class="item-actions">
        ${item.status !== "paid" ? `<button class="btn small ghost" data-pay="${item.id}">Отметить оплаченным</button>` : ""}
        <button class="btn small ghost" data-del="${item.id}">Удалить</button>
      </div>
    `;
    list.appendChild(el);
  });
}

async function load() {
  const error = document.getElementById("error");
  error.classList.add("hidden");
  try {
    const [summary, operations] = await Promise.all([
      api(`/api/summary?month=${state.month}`),
      api(`/api/operations?month=${state.month}`),
    ]);
    setText("totalBalance", money(summary.total_balance), summary.total_balance < 0);
    setText("paidIncome", money(summary.paid_income));
    setText("paidExpense", money(summary.paid_expense));
    setText("expectedIn", money(summary.expected_in));
    document.getElementById("expectedIn").classList.toggle("blue", Number(summary.expected_in) > 0);
    setText("expectedOut", money(summary.expected_out));
    renderAccounts(summary.accounts || []);
    renderList(operations);
  } catch (err) {
    error.textContent = err.message;
    error.classList.remove("hidden");
  }
}

function openSheet(type) {
  state.formType = type;
  document.getElementById("sheetTitle").textContent = type === "income" ? "Новый приход" : "Новый расход";
  document.getElementById("amount").value = "";
  document.getElementById("comment").value = "";
  document.getElementById("status").value = "paid";
  document.getElementById("opDate").value = new Date().toISOString().slice(0, 10);
  fillAccountSelect();
  document.getElementById("sheet").classList.remove("hidden");
}

function closeSheet() {
  document.getElementById("sheet").classList.add("hidden");
}

function openBalance(accountId) {
  const acc = state.accounts.find((a) => String(a.id) === String(accountId));
  if (!acc) return;
  state.editAccountId = acc.id;
  document.getElementById("balanceTitle").textContent = `Остаток · ${acc.name}`;
  document.getElementById("balanceAmount").value = String(acc.balance);
  document.getElementById("balanceSheet").classList.remove("hidden");
}

function closeBalance() {
  document.getElementById("balanceSheet").classList.add("hidden");
}

async function setupCategories() {
  const select = document.getElementById("category");
  try {
    const meta = await api("/api/meta");
    select.innerHTML = meta.categories.map((c) => `<option value="${c}">${c}</option>`).join("");
    if (meta.accounts) {
      state.accounts = meta.accounts;
      fillAccountSelect();
    }
  } catch {
    ["предоплата", "акт", "подряд", "реклама", "сервисы", "налоги", "зарплата", "прочее"].forEach((c) => {
      select.innerHTML += `<option value="${c}">${c}</option>`;
    });
  }
}

document.getElementById("prevMonth").onclick = () => shiftMonth(-1);
document.getElementById("nextMonth").onclick = () => shiftMonth(1);
document.getElementById("addIncome").onclick = () => openSheet("income");
document.getElementById("addExpense").onclick = () => openSheet("expense");
document.getElementById("cancelForm").onclick = closeSheet;
document.getElementById("cancelBalance").onclick = closeBalance;
document.getElementById("sheet").addEventListener("click", (e) => {
  if (e.target.id === "sheet") closeSheet();
});
document.getElementById("balanceSheet").addEventListener("click", (e) => {
  if (e.target.id === "balanceSheet") closeBalance();
});
document.getElementById("accounts").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-acc]");
  if (btn) openBalance(btn.dataset.acc);
});

document.getElementById("form").onsubmit = async (e) => {
  e.preventDefault();
  const amount = Number(String(document.getElementById("amount").value).replace(/\D/g, ""));
  if (!amount) return;
  try {
    await api("/api/operations", {
      method: "POST",
      body: JSON.stringify({
        type: state.formType,
        status: document.getElementById("status").value,
        category: document.getElementById("category").value,
        amount_rub: amount,
        comment: document.getElementById("comment").value,
        op_date: document.getElementById("opDate").value,
        account_id: Number(document.getElementById("account").value),
      }),
    });
    tg?.HapticFeedback?.notificationOccurred("success");
    closeSheet();
    load();
  } catch (err) {
    document.getElementById("error").textContent = err.message;
    document.getElementById("error").classList.remove("hidden");
  }
};

document.getElementById("balanceForm").onsubmit = async (e) => {
  e.preventDefault();
  const raw = String(document.getElementById("balanceAmount").value).replace(/\s/g, "").replace(",", ".");
  const amount = Number(raw);
  if (Number.isNaN(amount)) return;
  try {
    await api(`/api/accounts/${state.editAccountId}`, {
      method: "PATCH",
      body: JSON.stringify({ balance: Math.round(amount) }),
    });
    closeBalance();
    load();
  } catch (err) {
    document.getElementById("error").textContent = err.message;
    document.getElementById("error").classList.remove("hidden");
  }
};

document.getElementById("list").addEventListener("click", async (e) => {
  const pay = e.target.dataset.pay;
  const del = e.target.dataset.del;
  try {
    if (pay) {
      await api(`/api/operations/${pay}`, { method: "PATCH", body: JSON.stringify({ status: "paid" }) });
    }
    if (del) {
      if (!confirm("Удалить операцию?")) return;
      await api(`/api/operations/${del}`, { method: "DELETE" });
    }
    if (pay || del) load();
  } catch (err) {
    document.getElementById("error").textContent = err.message;
    document.getElementById("error").classList.remove("hidden");
  }
});

renderMonth();
setupCategories();
load();
