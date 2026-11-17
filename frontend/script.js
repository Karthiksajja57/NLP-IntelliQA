// Served by FastAPI at /app -> same origin. If opened another way, talk to localhost:8000.
const API = location.protocol.startsWith("http") && location.port === "8000" ? "" : "http://127.0.0.1:8000";
const $ = id => document.getElementById(id);
let token = localStorage.getItem("iq_token");
let user = null, docReady = false, lastNlp = null;

const QUICK = ["What is the main topic of this document?", "What are the important concepts?",
  "What are the advantages?", "What are the applications?", "What are the limitations?"];

function toast(msg, type = "ok") {
  const t = document.createElement("div");
  t.className = "toast " + type; t.textContent = msg; $("toasts").appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

async function api(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  if (token) headers.Authorization = "Bearer " + token;
  let res;
  try { res = await fetch(API + path, Object.assign({}, options, { headers })); }
  catch { throw new Error("Cannot reach the backend. Start it with: python -m uvicorn main:app --reload"); }
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && token && path !== "/login") { showAuth(); throw new Error("Session expired. Please log in again."); }
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Invalid request.");
  return data;
}
const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---------- auth ----------
function showAuth() {
  token = null; user = null; localStorage.removeItem("iq_token");
  $("app-view").hidden = true; $("auth-view").hidden = false;
}
async function showApp(u) {
  user = u; $("auth-view").hidden = true; $("app-view").hidden = false;
  $("p-name").textContent = u.full_name; $("p-email").textContent = u.email;
  $("admin-nav").hidden = u.role !== "admin";
  docReady = false; lastNlp = null; $("answer").hidden = true; $("result").hidden = true;
  $("nlp-inline-card").hidden = true; $("nlp-page").innerHTML = '<p class="muted">Ask a question to see the NLP stages here.</p>';
  go("dashboard"); refresh();
}
function switchForm(toRegister) { $("login-form").hidden = toRegister; $("register-form").hidden = !toRegister; }
$("to-register").onclick = e => { e.preventDefault(); switchForm(true); };
$("to-login").onclick = e => { e.preventDefault(); switchForm(false); };

$("login-form").onsubmit = async e => {
  e.preventDefault(); $("l-error").textContent = "";
  const email = $("l-email").value.trim(), password = $("l-pass").value;
  if (!email || !password) return $("l-error").textContent = "Email and password are required.";
  try {
    const d = await post("/login", { email, password });
    token = d.token; localStorage.setItem("iq_token", token); showApp(d.user);
  } catch (err) { $("l-error").textContent = err.message; }
};
$("register-form").onsubmit = async e => {
  e.preventDefault(); const err = $("r-error"); err.textContent = "";
  const b = { full_name: $("r-name").value.trim(), email: $("r-email").value.trim(),
    password: $("r-pass").value, confirm_password: $("r-pass2").value };
  if (!b.full_name || !b.email || !b.password || !b.confirm_password) return err.textContent = "All fields are required.";
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(b.email)) return err.textContent = "Please enter a valid email address.";
  if (b.password.length < 6) return err.textContent = "Password must be at least 6 characters.";
  if (b.password !== b.confirm_password) return err.textContent = "Passwords do not match.";
  try {
    const d = await post("/register", b);
    token = d.token; localStorage.setItem("iq_token", token); showApp(d.user); toast("Account created. Welcome, " + d.user.full_name + "!");
  } catch (ex) { err.textContent = ex.message; }
};
$("logout").onclick = async () => { try { await api("/logout", { method: "POST" }); } catch {} showAuth(); switchForm(false); };

// ---------- navigation ----------
function go(view) {
  document.querySelectorAll(".view").forEach(v => v.hidden = v.id !== "view-" + view);
  document.querySelectorAll("#nav button[data-view]").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  if (view === "history") loadHistory();
  if (view === "dashboard") refresh();
  if (view === "admin" && user?.role === "admin") loadAdmin();
}
$("nav").addEventListener("click", e => { const v = e.target.dataset.view; if (v) go(v); });
document.addEventListener("click", e => { if (e.target.dataset.go) go(e.target.dataset.go); });

async function refresh() {
  try {
    const i = await api("/document-info");
    docReady = i.uploaded;
    $("c-docs").textContent = i.documents_processed; $("c-q").textContent = i.questions;
    $("c-sim").textContent = i.average_similarity + "%"; $("c-doc").textContent = i.filename || "None";
  } catch (e) { toast(e.message, "err"); }
}

// ---------- upload ----------
async function upload(file) {
  if (!file) return toast("No file selected.", "err");
  if (!/\.(pdf|txt)$/i.test(file.name)) return toast("Unsupported file. Please choose a PDF or TXT file.", "err");
  if (file.size > 10 * 1024 * 1024) return toast("File too large. Maximum size is 10 MB.", "err");
  const form = new FormData(); form.append("file", file);
  $("progress").hidden = false; $("result").hidden = true;
  try {
    const d = await api("/upload", { method: "POST", body: form });
    $("r-file").textContent = "Document: " + d.filename; $("r-pages").textContent = d.pages; $("r-chunks").textContent = d.chunks;
    $("result").hidden = false; docReady = true; toast("Document processed successfully."); refresh();
  } catch (e) { toast(e.message, "err"); }
  $("progress").hidden = true; $("file").value = "";
}
const drop = $("drop");
$("choose").onclick = () => $("file").click();
$("file").onchange = e => upload(e.target.files[0]);
drop.ondragover = e => { e.preventDefault(); drop.classList.add("over"); };
drop.ondragleave = () => drop.classList.remove("over");
drop.ondrop = e => { e.preventDefault(); drop.classList.remove("over"); upload(e.dataTransfer.files[0]); };

// ---------- ask ----------
async function ask() {
  const question = $("q").value.trim();
  if (!question) return toast("Please type a question.", "err");
  if (!docReady) { toast("Please upload a document first.", "err"); return go("upload"); }
  $("askBtn").disabled = true; $("loading").hidden = false; $("answer").hidden = true;
  try {
    const d = await post("/ask", { question });
    $("answer").classList.toggle("miss", !d.success);
    $("a-text").textContent = d.answer; $("a-sim").textContent = d.similarity + "%";
    $("a-page-wrap").hidden = !d.success; $("source").hidden = !d.success;
    if (d.success) { $("a-page").textContent = d.page; $("src-text").textContent = d.source_text; }
    $("answer").hidden = false;
    lastNlp = d; renderNlp($("nlp-inline"), d); renderNlp($("nlp-page"), d); $("nlp-inline-card").hidden = false;
    refresh();
  } catch (e) { toast(e.message, "err"); }
  $("loading").hidden = true; $("askBtn").disabled = false;
}
$("askBtn").onclick = ask;
$("q").addEventListener("keydown", e => { if (e.key === "Enter") ask(); });
QUICK.forEach(t => {
  const b = document.createElement("button"); b.className = "chip"; b.textContent = t;
  b.onclick = () => { $("q").value = t; $("q").focus(); }; $("chips").appendChild(b);
});

// ---------- NLP processing panel (built with textContent, so nothing is injected as HTML) ----------
function tokens(list, cls, removed) {
  const box = document.createElement("div");
  if (!list.length) box.textContent = "—";
  list.forEach(t => { const s = document.createElement("span"); s.className = "tok " + (cls || ""); s.textContent = t; box.appendChild(s); });
  return box;
}
function renderNlp(box, d) {
  const n = d.nlp, kw = new Set(n.keywords); box.innerHTML = "";
  const removedTokens = n.tokens.filter(t => !kw.has(t));
  const text = s => { const p = document.createElement("div"); p.className = "val"; p.textContent = s; return p; };
  const tfidf = n.tfidf_terms.length ? n.tfidf_terms.map(t => t.term + " (" + t.weight + ")").join("  |  ") : "—";
  const groups = [
    ["1 · NLP PREPROCESSING", [
      ["Original question", text(n.original_question)],
      ["Lowercase", text(n.lowercase)],
      ["Punctuation removed", text(n.cleaned_question)],
      ["Tokenization", tokens(n.tokens)],
      ["Stop-words removed → keywords", (() => { const w = document.createElement("div");
        removedTokens.forEach(t => w.appendChild(Object.assign(document.createElement("span"), { className: "tok rm", textContent: t })));
        n.keywords.forEach(t => w.appendChild(Object.assign(document.createElement("span"), { className: "tok kw", textContent: t }))); return w; })()]]],
    ["2 · INFORMATION RETRIEVAL", [
      ["TF-IDF question vector (term weight)", text(tfidf)],
      ["Cosine similarity", text(d.similarity + "%")],
      ["Most relevant sentence", text(n.relevant_sentence || "No sentence passed the similarity threshold.")]]],
    ["3 · ANSWER EXTRACTION", [
      ["Pattern used", text(n.extraction_pattern || "—")],
      ["Final answer", text(d.success ? d.answer : "—")]]],
  ];
  let i = 1;
  groups.forEach(([title, steps]) => {
    const g = document.createElement("div"); g.className = "grp"; g.textContent = title; box.appendChild(g);
    steps.forEach(([label, node]) => {
      const row = document.createElement("div"); row.className = "step";
      const dot = document.createElement("div"); dot.className = "dot"; dot.textContent = i++;
      const body = document.createElement("div"); const h = document.createElement("h5"); h.textContent = label;
      body.append(h, node); row.append(dot, body); box.appendChild(row);
    });
  });
}

// ---------- history ----------
async function loadHistory() {
  try {
    const d = await api("/history"), body = $("hist"); body.innerHTML = "";
    $("hist-empty").hidden = d.history.length > 0;
    d.history.forEach(r => {
      const tr = document.createElement("tr");
      [r.question, r.answer, r.similarity + "%", r.created_at + " UTC"].forEach(v => {
        const td = document.createElement("td"); td.textContent = v; tr.appendChild(td);
      });
      body.appendChild(tr);
    });
  } catch (e) { toast(e.message, "err"); }
}

// ---------- start: restore session if a valid token exists ----------
(async () => {
  if (!token) return;
  try { const d = await api("/me"); showApp(d.user); }
  catch (e) { if (!$("app-view").hidden) return; showAuth(); }
})();


// ---------- admin ----------
async function loadAdmin() {
  if (!user || user.role !== "admin") return;
  try {
    const s = await api("/admin/stats");
    $("admin-users").textContent = s.users;
    $("admin-docs").textContent = s.documents;
    $("admin-questions").textContent = s.questions;
    $("admin-admins").textContent = s.admins;
    const d = await api("/admin/users");
    const body = $("admin-user-list"); body.innerHTML = "";
    d.users.forEach(u => {
      const tr = document.createElement("tr");
      [u.full_name, u.email, u.role, u.created_at.replace("T", " ").replace("+00:00", " UTC")].forEach(v => {
        const td = document.createElement("td"); td.textContent = v; tr.appendChild(td);
      });
      body.appendChild(tr);
    });
  } catch (e) { toast(e.message, "err"); }
}
$("admin-refresh").onclick = loadAdmin;
