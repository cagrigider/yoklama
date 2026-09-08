const TAG_LABELS = {
  question: "Soru sordu",
  win: "Kazanım paylaştı",
  homework: "Ödev yaptı",
  camera: "Kamera açık",
};

const STATUS_LABELS = {
  unmarked: "—",
  absent: "Gelmedi",
  present: "Katıldı",
  quiet: "Sessiz",
  spoke: "Konuştu",
  strong: "Katkı",
};

const JOINED = new Set(["present", "quiet", "spoke", "strong"]);

function isJoined(p) {
  return JOINED.has(p.status);
}

function rankPerson(p) {
  if (JOINED.has(p.status)) return 0;
  if (p.status === "absent") return 2;
  return 1;
}

const $app = document.getElementById("app");
let toastTimer;
let inputLockUntil = 0;

function isInputLocked() {
  return Date.now() < inputLockUntil;
}

function armInputLock() {
  inputLockUntil = Date.now() + 500;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || "İstek başarısız");
  }
  return res.json();
}

function toast(text) {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = text;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 1800);
}

function confirmDialog({ title, body, confirmLabel = "Sil", danger = true }) {
  return new Promise((resolve) => {
    const wrap = document.createElement("div");
    wrap.className = "modal-back";
    wrap.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true">
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(body)}</p>
        <div class="modal-actions">
          <button type="button" class="btn ghost" data-cancel>Vazgeç</button>
          <button type="button" class="btn ${danger ? "danger" : "primary"}" data-ok>${escapeHtml(confirmLabel)}</button>
        </div>
      </div>`;
    const finish = (value) => {
      wrap.remove();
      resolve(value);
    };
    wrap.addEventListener("click", (e) => {
      if (e.target === wrap) finish(false);
    });
    wrap.querySelector("[data-cancel]").addEventListener("click", () => finish(false));
    wrap.querySelector("[data-ok]").addEventListener("click", () => finish(true));
    document.body.appendChild(wrap);
    wrap.querySelector("[data-ok]").focus();
  });
}

function meetingEditorFields(m) {
  return `
    <input name="title" value="${escapeHtml(m.title)}" required />
    <input name="date" type="date" value="${escapeHtml(m.date)}" required />
    <textarea name="notes" rows="3" placeholder="Toplantı notu (gündem, link, hatırlatma…)">${escapeHtml(m.notes || "")}</textarea>
  `;
}

let viewSeq = 0;

function route() {
  const seq = ++viewSeq;
  const hash = location.hash.replace(/^#/, "") || "/";
  const parts = hash.split("/").filter(Boolean);
  document.querySelectorAll("[data-nav]").forEach((a) => {
    const key = a.dataset.nav;
    a.classList.toggle("active", (key === "home" && !parts.length) || parts[0] === key);
  });
  const run = !parts.length
    ? renderMeetings()
    : parts[0] === "people" && parts[1]
      ? renderPerson(parts[1])
      : parts[0] === "people"
        ? renderPeople()
        : parts[0] === "meeting" && parts[1] && parts[2] === "report"
          ? renderMeetingReport(parts[1])
          : parts[0] === "meeting" && parts[1]
            ? renderLive(parts[1], seq)
            : renderMeetings();
  return Promise.resolve(run).then(() => {
    if (seq !== viewSeq) return;
  });
}

function fmtDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat("tr-TR", {
    weekday: "short",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(y, m - 1, d));
}

async function renderMeetings() {
  const [meetings, meta] = await Promise.all([api("/api/meetings"), api("/api/meta")]);
  const today = meta.today;
  $app.innerHTML = `
    <div class="top">
      <div>
        <h2>Toplantılar</h2>
        <p class="sub">Toplantı ekle; yoklamayı canlı işaretle. Veri bu makinede kalır.</p>
      </div>
    </div>
    <section class="add-card">
      <strong>Toplantı ekle</strong>
      <form id="add-meeting">
        <input name="title" placeholder="Başlık" value="AI Awareness" required />
        <input name="date" type="date" required />
        <textarea name="notes" rows="2" placeholder="Not (isteğe bağlı)"></textarea>
        <button class="btn primary" type="submit">Ekle</button>
      </form>
    </section>
    <div class="grid" id="meeting-list"></div>
  `;
  const list = $app.querySelector("#meeting-list");
  list.innerHTML = meetings
    .map((m) => {
      const isToday = m.date === today;
      const noteLine = m.notes
        ? `<p class="note-preview">${escapeHtml(m.notes)}</p>`
        : "";
      return `
        <article class="meeting-card ${isToday ? "today" : ""}" data-id="${m.id}">
          <a class="meeting-card-main" href="#/meeting/${m.id}">
            <div>
              <p class="meeting-title">${escapeHtml(m.title)}</p>
              <p class="meta">${fmtDate(m.date)}${m.kind === "extra" ? " · ekstra" : ""}${isToday ? " · bugün" : ""}</p>
              ${noteLine}
            </div>
            <div class="counts">
              <span class="chip present">${m.present} geldi</span>
              <span class="chip">${m.unmarked} açık</span>
            </div>
          </a>
          <div class="meeting-card-actions">
            <button type="button" class="btn ghost" data-edit>Düzenle</button>
            <button type="button" class="btn danger" data-delete>Sil</button>
          </div>
          <form class="meeting-edit" hidden>
            ${meetingEditorFields(m)}
            <div class="modal-actions">
              <button type="button" class="btn ghost" data-cancel-edit>Vazgeç</button>
              <button class="btn primary" type="submit">Kaydet</button>
            </div>
          </form>
        </article>`;
    })
    .join("");
  list.querySelectorAll("[data-edit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".meeting-card");
      card.querySelector(".meeting-edit").hidden = false;
      card.querySelector(".meeting-card-actions").hidden = true;
    });
  });
  list.querySelectorAll("[data-cancel-edit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".meeting-card");
      card.querySelector(".meeting-edit").hidden = true;
      card.querySelector(".meeting-card-actions").hidden = false;
    });
  });
  list.querySelectorAll(".meeting-edit").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = form.closest(".meeting-card").dataset.id;
      const data = Object.fromEntries(new FormData(form));
      await api(`/api/meetings/${id}`, { method: "PUT", body: JSON.stringify(data) });
      toast("Toplantı güncellendi");
      renderMeetings();
    });
  });
  list.querySelectorAll("[data-delete]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const card = btn.closest(".meeting-card");
      const id = card.dataset.id;
      const title = card.querySelector(".meeting-title").textContent;
      const ok = await confirmDialog({
        title: "Toplantıyı sil",
        body: `“${title}” silinsin mi? Bu oturumun yoklaması da gider. Bu işlem geri alınamaz.`,
        confirmLabel: "Evet, sil",
      });
      if (!ok) return;
      await api(`/api/meetings/${id}`, { method: "DELETE" });
      toast("Toplantı silindi");
      renderMeetings();
    });
  });
  $app.querySelector("#add-meeting").addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    const created = await api("/api/meetings", { method: "POST", body: JSON.stringify(data) });
    toast("Toplantı eklendi");
    location.hash = `#/meeting/${created.id}`;
  });
}

async function renderLive(id, seq = viewSeq) {
  const stillHere = () =>
    seq === viewSeq && /#\/meeting\/\d+$/.test(location.hash);
  const data = { meeting: null, roster: [] };
  let filter = "all";
  let query = "";

  const reload = async () => {
    const fresh = await api(`/api/meetings/${id}/roster`);
    data.meeting = fresh.meeting;
    data.roster = fresh.roster;
  };

  const visibleRoster = () =>
    data.roster.filter((p) => {
      const hay = `${p.name} ${p.center} ${p.position}`.toLocaleLowerCase("tr");
      if (query && !hay.includes(query)) return false;
      if (filter === "present") return JOINED.has(p.status);
      if (filter === "unmarked") return p.status === "unmarked";
      if (filter === "absent") return p.status === "absent";
      return true;
    });

  const paintRoster = () => {
    if (!stillHere()) return;
    const rosterEl = $app.querySelector("#roster");
    if (!rosterEl) return;
    const present = data.roster.filter((p) => JOINED.has(p.status)).length;
    const sub = $app.querySelector("#live-sub");
    if (sub) sub.textContent = `${fmtDate(data.meeting.date)} · ${present}/${data.meeting.people} katıldı`;
    $app.querySelectorAll("[data-filter]").forEach((btn) => {
      btn.dataset.on = btn.dataset.filter === filter ? "true" : "false";
    });
    const rows = visibleRoster();
    const groups = [
      { key: "joined", title: "Katılanlar", items: rows.filter((p) => rankPerson(p) === 0) },
      { key: "wait", title: "Henüz işaretlenmedi", items: rows.filter((p) => rankPerson(p) === 1) },
      { key: "absent", title: "Gelmedi", items: rows.filter((p) => rankPerson(p) === 2) },
    ].filter((g) => g.items.length);
    rosterEl.innerHTML = groups.length
      ? groups
          .map(
            (g) =>
              `<h3 class="group-label">${g.title} · ${g.items.length}</h3>` +
              g.items.map(personCard).join("")
          )
          .join("")
      : `<p class="empty">Eşleşen kimse yok.</p>`;
    rosterEl.querySelectorAll(".person-row").forEach((row) => bindPersonRow(row, data, id, reloadAndPaint));
  };

  const reloadAndPaint = async () => {
    await reload();
    paintRoster();
  };

  await reload();
  if (!stillHere()) return;
  const present = data.roster.filter((p) => JOINED.has(p.status)).length;
  $app.innerHTML = `
    <div class="live-head">
      <div class="top" style="margin:0">
        <div>
          <h2>${escapeHtml(data.meeting.title)}</h2>
          <p class="sub" id="live-sub">${fmtDate(data.meeting.date)} · ${present}/${data.meeting.people} katıldı</p>
        </div>
        <div class="live-actions">
          <a class="btn ghost" href="#/">Geri</a>
          <a class="btn" href="#/meeting/${id}/report">Toplantı raporu</a>
          <button class="btn ghost" id="edit-meeting" type="button">Düzenle</button>
          <button class="btn" id="close-meeting" type="button">Kalanları gelmedi işaretle</button>
          <button class="btn danger" id="delete-meeting" type="button">Sil</button>
        </div>
      </div>
      <form class="meeting-edit live-edit" id="live-edit" hidden>
        ${meetingEditorFields(data.meeting)}
        <div class="modal-actions">
          <button type="button" class="btn ghost" id="cancel-live-edit">Vazgeç</button>
          <button class="btn primary" type="submit">Kaydet</button>
        </div>
      </form>
      ${
        data.meeting.notes
          ? `<p class="meeting-note">${escapeHtml(data.meeting.notes)}</p>`
          : `<p class="meeting-note muted">Toplantı notu yok. Düzenle ile ekleyebilirsin.</p>`
      }
      <input class="search" id="search" placeholder="İsim veya yetkinlik ara" />
      <div class="filters">
        ${["all", "unmarked", "present", "absent"]
          .map((f) => {
            const labels = { all: "Hepsi", unmarked: "Açık", present: "Katıldı", absent: "Gelmedi" };
            return `<button class="pill" data-filter="${f}" type="button">${labels[f]}</button>`;
          })
          .join("")}
      </div>
    </div>
    <div id="roster"></div>
  `;
  $app.querySelector("#search").addEventListener("input", (e) => {
    query = e.target.value.trim().toLocaleLowerCase("tr");
    paintRoster();
  });
  $app.querySelectorAll("[data-filter]").forEach((btn) =>
    btn.addEventListener("click", () => {
      filter = btn.dataset.filter;
      paintRoster();
    })
  );
  $app.querySelector("#edit-meeting").addEventListener("click", () => {
    $app.querySelector("#live-edit").hidden = false;
  });
  $app.querySelector("#cancel-live-edit").addEventListener("click", () => {
    $app.querySelector("#live-edit").hidden = true;
  });
  $app.querySelector("#live-edit").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = Object.fromEntries(new FormData(e.target));
    const updated = await api(`/api/meetings/${id}`, { method: "PUT", body: JSON.stringify(payload) });
    data.meeting = { ...data.meeting, ...updated };
    toast("Toplantı güncellendi");
    renderLive(id, seq);
  });
  $app.querySelector("#delete-meeting").addEventListener("click", async () => {
    const ok = await confirmDialog({
      title: "Toplantıyı sil",
      body: `“${data.meeting.title}” silinsin mi? Bu oturumun yoklaması da gider. Bu işlem geri alınamaz.`,
      confirmLabel: "Evet, sil",
    });
    if (!ok) return;
    await api(`/api/meetings/${id}`, { method: "DELETE" });
    toast("Toplantı silindi");
    location.hash = "#/";
  });
  $app.querySelector("#close-meeting").addEventListener("click", async () => {
    if (!confirm("İşaretlenmeyen herkesi “gelmedi” yapayım mı?")) return;
    const closed = await api(`/api/meetings/${id}/close`, { method: "POST", body: "{}" });
    data.meeting = closed.meeting;
    data.roster = closed.roster;
    toast("Toplantı kapatıldı");
    paintRoster();
  });
  paintRoster();
}

function personCard(p) {
  const joined = JOINED.has(p.status);
  const rowClass = p.status === "absent" ? "absent" : joined ? "joined" : "";
  return `
    <article class="person-row ${rowClass}" data-id="${p.id}">
      <div class="person-main">
        <button type="button" class="join-toggle" data-join="1" aria-pressed="${joined}">Katıldı</button>
        <div class="who">
          <h3 class="person-name">${escapeHtml(p.name)}</h3>
          <p class="meta">${escapeHtml(p.center || p.position || "")}</p>
        </div>
        <button type="button" class="btn miss-btn" data-status="absent" aria-pressed="${p.status === "absent"}">Gelmedi</button>
        <a class="link-quiet" href="#/people/${p.id}">geçmiş</a>
      </div>
      <div class="field">
        <span class="field-label">Aktivite (isteğe bağlı)</span>
        <div class="seg">
          ${["quiet", "spoke", "strong"]
            .map(
              (s) =>
                `<button type="button" data-status="${s}" data-on="${p.status === s}">${STATUS_LABELS[s]}</button>`
            )
            .join("")}
        </div>
      </div>
      <div class="field">
        <span class="field-label">Notlar</span>
        <div class="tags">
          ${Object.entries(TAG_LABELS)
            .map(
              ([k, label]) =>
                `<button type="button" class="tag" data-tag="${k}" data-on="${p.tags.includes(k)}"><span class="box"></span>${label}</button>`
            )
            .join("")}
        </div>
      </div>
      <input class="note" placeholder="Kısa not (isteğe bağlı)" value="${escapeHtml(p.note || "")}" />
    </article>
  `;
}

function bindPersonRow(row, data, meetingId, reloadAndPaint) {
  const personId = row.dataset.id;
  const current = () => data.roster.find((p) => p.id === personId);

  const save = async (patch) => {
    if (isInputLocked()) return;
    armInputLock();
    try {
      await api(`/api/meetings/${meetingId}/attendance/${personId}`, {
        method: "PUT",
        body: JSON.stringify(patch),
      });
      await reloadAndPaint();
    } catch (err) {
      toast(err.message);
    }
  };

  row.querySelector("[data-join]").addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    const person = current();
    save({ status: JOINED.has(person.status) ? "unmarked" : "present" });
  });
  row.querySelector(".miss-btn").addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    const person = current();
    save({ status: person.status === "absent" ? "unmarked" : "absent" });
  });
  row.querySelectorAll(".seg [data-status]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const person = current();
      const next = person.status === btn.dataset.status ? "present" : btn.dataset.status;
      save({ status: next });
    });
  });
  row.querySelectorAll("[data-tag]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (isInputLocked()) return;
      const person = current();
      const tag = btn.dataset.tag;
      const tags = person.tags.includes(tag)
        ? person.tags.filter((t) => t !== tag)
        : [...person.tags, tag];
      const status = JOINED.has(person.status) ? person.status : "present";
      save({ tags, status });
    });
  });
  row.querySelector(".note").addEventListener("change", (e) => {
    save({ note: e.target.value.trim() });
  });
}

async function renderMeetingReport(id) {
  const report = await api(`/api/meetings/${id}/report`);
  $app.innerHTML = `
    <div class="top">
      <div>
        <h2>Toplantı raporu</h2>
        <p class="sub">${escapeHtml(report.meeting.title)} · ${fmtDate(report.meeting.date)}</p>
      </div>
      <div class="live-actions">
        <a class="btn ghost" href="#/meeting/${id}">Canlı yoklama</a>
        <button class="btn primary" id="copy" type="button">Özeti kopyala</button>
      </div>
    </div>
    <pre class="summary" id="summary">${escapeHtml(report.summary)}</pre>
  `;
  $app.querySelector("#copy").addEventListener("click", async () => {
    await navigator.clipboard.writeText(report.summary);
    toast("Kopyalandı");
  });
}

async function renderPeople() {
  const people = await api("/api/overview");
  $app.innerHTML = `
    <div class="top">
      <div>
        <h2>Kişiler</h2>
        <p class="sub">Yönetici “geldi mi, aktif miydi?” diye sorunca buradan bak.</p>
      </div>
    </div>
    <input class="search" id="search" placeholder="İsim ara" />
    <div class="grid" id="list" style="margin-top:14px"></div>
  `;
  const draw = (q = "") => {
    const needle = q.trim().toLocaleLowerCase("tr");
    const rows = people.filter((p) => p.name.toLocaleLowerCase("tr").includes(needle));
    $app.querySelector("#list").innerHTML = rows
      .map(
        (p) => `
        <a class="meeting-card" href="#/people/${p.id}">
          <div>
            <p class="meeting-title">${escapeHtml(p.name)}</p>
            <p class="meta">${escapeHtml(p.center || "")} · ${p.present}/${p.total} oturum</p>
          </div>
          <span class="chip present">%${p.percent}</span>
        </a>`
      )
      .join("");
  };
  draw();
  $app.querySelector("#search").addEventListener("input", (e) => draw(e.target.value));
}

async function renderPerson(id) {
  const report = await api(`/api/people/${id}/report`);
  $app.innerHTML = `
    <div class="top">
      <div>
        <h2>${escapeHtml(report.person.name)}</h2>
        <p class="sub">${escapeHtml(report.person.position)} · ${escapeHtml(report.person.center)}</p>
      </div>
      <div class="live-actions">
        <a class="btn ghost" href="#/people">Kişiler</a>
        <button class="btn primary" id="copy" type="button">Yönetici özetini kopyala</button>
      </div>
    </div>
    <p class="report-card">${escapeHtml(report.summary)}</p>
    <div class="grid" style="margin-top:14px">
      ${report.history
        .map(
          (h) => `
        <a class="meeting-card" href="#/meeting/${h.meetingId}">
          <div>
            <p class="meeting-title">${fmtDate(h.date)}</p>
            <p class="meta">${escapeHtml(h.title)}${h.note ? " · " + escapeHtml(h.note) : ""}</p>
          </div>
          <span class="chip">${STATUS_LABELS[h.status] || h.status}</span>
        </a>`
        )
        .join("")}
    </div>
  `;
  $app.querySelector("#copy").addEventListener("click", async () => {
    await navigator.clipboard.writeText(report.summary);
    toast("Kopyalandı");
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

window.addEventListener("hashchange", () => route().catch((err) => toast(err.message)));
route().catch((err) => {
  $app.innerHTML = `<p class="empty">${escapeHtml(err.message)}</p>`;
});
