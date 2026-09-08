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

const WIZARD_COPY = {
  title: "Grubunu ayarla",
  sub: "Grup adı ve toplantı takvimini kaydet. Kişileri sonra ekleyebilirsin.",
  name: "Grup adı",
  firstDate: "İlk toplantı tarihi",
  repeat: "Tekrar",
  endDate: "Bitiş tarihi",
  save: "Kaydet ve devam et",
  required: "Grup adı ve ilk tarih gerekli.",
  dateError: "Bitiş tarihi ilk tarihten önce olamaz.",
  endRequired: "Tekrarlayan seride bitiş tarihi gerekli.",
  invalidDate: "Tarih geçersiz.",
  none: "Tekrarlama yok",
  weekly: "Her hafta",
  biweekly: "2 haftada bir",
  monthly: "Her ay",
};

const WIZARD_REPEATS = [
  { value: "none", label: WIZARD_COPY.none },
  { value: "weekly", label: WIZARD_COPY.weekly },
  { value: "biweekly", label: WIZARD_COPY.biweekly },
  { value: "monthly", label: WIZARD_COPY.monthly },
];

const PEOPLE_COPY = {
  title: "Kişiler",
  sub: "Yönetici “geldi mi, aktif miydi?” diye sorunca buradan bak.",
  add: "Kişi ekle",
  edit: "Düzenle",
  remove: "Sil",
  save: "Kaydet",
  cancel: "Vazgeç",
  sicil: "Sicil",
  name: "Ad",
  position: "Pozisyon",
  center: "Yetkinlik",
  email: "E-posta",
  emailHint: "isteğe bağlı",
  required: "Sicil ve ad gerekli.",
  formHint: "Sicil ve ad zorunlu. Pozisyon, yetkinlik ve e-posta isteğe bağlı.",
  duplicate: "Bu sicil zaten kayıtlı.",
  empty: "Henüz kişi yok. Kişi ekleyerek yoklama listesini oluşturabilirsin.",
  noMatch: "Eşleşen kimse yok.",
  deleteTitle: "Kişiyi sil",
  deleteConfirm: "Evet, sil",
  added: "Kişi eklendi",
  updated: "Kişi güncellendi",
  deleted: "Kişi silindi",
  history: "geçmiş",
  addTitle: "Kişi ekle",
  editTitle: "Kişiyi düzenle",
  search: "İsim ara",
  sessions: "oturum",
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
  const data = await res.json().catch(() => ({ error: res.statusText }));
  if (!res.ok) {
    const err = new Error(data.error || "İstek başarısız");
    err.status = res.status;
    err.code = data.error;
    throw err;
  }
  return data;
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
  return api("/api/meta")
    .then((meta) => {
      if (seq !== viewSeq) return;
      if (!meta.configured) {
        document.querySelectorAll("[data-nav]").forEach((a) => a.classList.remove("active"));
        return renderWizard();
      }
      const hash = location.hash.replace(/^#/, "") || "/";
      const parts = hash.split("/").filter(Boolean);
      document.querySelectorAll("[data-nav]").forEach((a) => {
        const key = a.dataset.nav;
        a.classList.toggle("active", (key === "home" && !parts.length) || parts[0] === key);
      });
      if (!parts.length) return renderMeetings();
      if (parts[0] === "people" && parts[1] === "new") return renderPersonForm();
      if (parts[0] === "people" && parts[1] && parts[2] === "edit") return renderPersonForm(parts[1]);
      if (parts[0] === "people" && parts[1]) return renderPerson(parts[1]);
      if (parts[0] === "people") return renderPeople();
      if (parts[0] === "meeting" && parts[1] && parts[2] === "report") return renderMeetingReport(parts[1]);
      if (parts[0] === "meeting" && parts[1]) return renderLive(parts[1], seq);
      return renderMeetings();
    })
    .then(() => {
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

function wizardErrorText(err) {
  if (err.code === "end_before_first") return WIZARD_COPY.dateError;
  if (err.code === "end_required") return WIZARD_COPY.endRequired;
  if (err.code === "invalid_date") return WIZARD_COPY.invalidDate;
  return err.message;
}

function wizardRepeatButtons(selected) {
  return WIZARD_REPEATS.map(
    (opt) =>
      `<button type="button" data-repeat="${opt.value}" data-on="${opt.value === selected}">${escapeHtml(opt.label)}</button>`
  ).join("");
}

function syncWizardRepeat(form, rule) {
  form.querySelector("[name=repeatRule]").value = rule;
  form.querySelector("#wizard-end-wrap").hidden = rule === "none";
  form.querySelectorAll("[data-repeat]").forEach((btn) => {
    btn.dataset.on = btn.dataset.repeat === rule ? "true" : "false";
  });
}

function bindWizardForm(form) {
  form.querySelectorAll("[data-repeat]").forEach((btn) => {
    btn.addEventListener("click", () => syncWizardRepeat(form, btn.dataset.repeat));
  });
  const errorEl = form.querySelector("#wizard-error");
  const showError = (text) => {
    errorEl.hidden = !text;
    errorEl.textContent = text || "";
  };
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    const name = (data.name || "").trim();
    const firstDate = (data.firstDate || "").trim();
    const repeatRule = data.repeatRule || "none";
    const endDate = (data.endDate || "").trim() || null;
    if (!name || !firstDate) {
      showError(WIZARD_COPY.required);
      return;
    }
    if (repeatRule !== "none" && endDate && endDate < firstDate) {
      showError(WIZARD_COPY.dateError);
      return;
    }
    const payload = { name, firstDate, endDate: repeatRule === "none" ? null : endDate, repeatRule };
    try {
      await api("/api/profile", { method: "PUT", body: JSON.stringify(payload) });
      if (location.hash === "#/" || location.hash === "" || location.hash === "#") {
        await route();
      } else {
        location.hash = "#/";
      }
    } catch (err) {
      showError(wizardErrorText(err));
    }
  });
}

async function renderWizard() {
  $app.innerHTML = `
    <div class="top">
      <div>
        <h2>${WIZARD_COPY.title}</h2>
        <p class="sub">${WIZARD_COPY.sub}</p>
      </div>
    </div>
    <form class="add-card person-form wizard-card" id="wizard-form" novalidate>
      ${personFormField({ name: "name", label: WIZARD_COPY.name, required: true })}
      ${personFormField({ name: "firstDate", label: WIZARD_COPY.firstDate, type: "date", required: true })}
      <div class="field">
        <span class="field-label">${WIZARD_COPY.repeat}</span>
        <div class="seg">${wizardRepeatButtons("none")}</div>
        <input type="hidden" name="repeatRule" value="none" />
      </div>
      <div id="wizard-end-wrap" hidden>
        ${personFormField({ name: "endDate", label: WIZARD_COPY.endDate, type: "date" })}
      </div>
      <p class="form-error" id="wizard-error" hidden></p>
      <div class="modal-actions">
        <button class="btn primary" type="submit">${WIZARD_COPY.save}</button>
      </div>
    </form>
  `;
  bindWizardForm($app.querySelector("#wizard-form"));
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
          ${personSubtitle(p) ? `<p class="meta">${escapeHtml(personSubtitle(p))}</p>` : ""}
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

function personSubtitle(p) {
  return [p.position, p.center].filter(Boolean).join(" · ");
}

function peopleDeleteWarning(name) {
  return `“${name}” silinsin mi? Bu kişinin tüm yoklama kayıtları da silinir. Bu işlem geri alınamaz.`;
}

function peopleRow(p) {
  const role = personSubtitle(p);
  const counts = `${p.present}/${p.total} ${PEOPLE_COPY.sessions}`;
  const meta = role ? `${escapeHtml(role)} · ${counts}` : counts;
  return `
    <article class="meeting-card" data-id="${escapeHtml(p.id)}" data-name="${escapeHtml(p.name)}">
      <a class="meeting-card-main" href="#/people/${encodeURIComponent(p.id)}">
        <div>
          <p class="meeting-title">${escapeHtml(p.name)}</p>
          <p class="meta">${meta}</p>
        </div>
        <span class="chip present">%${p.percent}</span>
      </a>
      <div class="meeting-card-actions">
        <a class="btn ghost" href="#/people/${encodeURIComponent(p.id)}/edit">${PEOPLE_COPY.edit}</a>
        <button type="button" class="btn danger" data-delete>${PEOPLE_COPY.remove}</button>
      </div>
    </article>`;
}

async function confirmDeletePerson(id, name) {
  const ok = await confirmDialog({
    title: PEOPLE_COPY.deleteTitle,
    body: peopleDeleteWarning(name),
    confirmLabel: PEOPLE_COPY.deleteConfirm,
  });
  if (!ok) return false;
  await api(`/api/people/${encodeURIComponent(id)}`, { method: "DELETE" });
  toast(PEOPLE_COPY.deleted);
  return true;
}

async function renderPeople() {
  const people = await api("/api/overview");
  $app.innerHTML = `
    <div class="top">
      <div>
        <h2>${PEOPLE_COPY.title}</h2>
        <p class="sub">${PEOPLE_COPY.sub}</p>
      </div>
      <a class="btn primary" href="#/people/new">${PEOPLE_COPY.add}</a>
    </div>
    <input class="search" id="search" placeholder="${PEOPLE_COPY.search}" />
    <div class="grid" id="list" style="margin-top:14px"></div>
  `;
  const draw = (q = "") => {
    const needle = q.trim().toLocaleLowerCase("tr");
    const rows = people.filter((p) => p.name.toLocaleLowerCase("tr").includes(needle));
    const list = $app.querySelector("#list");
    if (!people.length) {
      list.innerHTML = `<p class="empty">${PEOPLE_COPY.empty}</p>`;
      return;
    }
    if (!rows.length) {
      list.innerHTML = `<p class="empty">${PEOPLE_COPY.noMatch}</p>`;
      return;
    }
    list.innerHTML = rows.map(peopleRow).join("");
    list.querySelectorAll("[data-delete]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const card = btn.closest(".meeting-card");
        const removed = await confirmDeletePerson(card.dataset.id, card.dataset.name);
        if (removed) renderPeople();
      });
    });
  };
  draw();
  $app.querySelector("#search").addEventListener("input", (e) => draw(e.target.value));
}

function personFormField({ name, label, value = "", required = false, disabled = false, type = "text", hint = "" }) {
  const req = required ? "required" : "";
  const dis = disabled ? "disabled" : "";
  const hintLine = hint ? `<span class="field-hint">${escapeHtml(hint)}</span>` : "";
  return `
    <label class="field">
      <span class="field-label">${escapeHtml(label)}${required ? " *" : ""}</span>
      <input id="person-${escapeHtml(name)}" name="${escapeHtml(name)}" type="${escapeHtml(type)}" value="${escapeHtml(value)}" ${req} ${dis} autocomplete="off" />
      ${hintLine}
    </label>`;
}

async function renderPersonForm(editId) {
  const editing = Boolean(editId);
  let person = { id: "", name: "", position: "", center: "", email: "" };
  if (editing) {
    const report = await api(`/api/people/${encodeURIComponent(editId)}/report`);
    person = report.person;
  }
  $app.innerHTML = `
    <div class="top">
      <div>
        <h2>${editing ? PEOPLE_COPY.editTitle : PEOPLE_COPY.addTitle}</h2>
        <p class="sub">${editing ? escapeHtml(person.name) : PEOPLE_COPY.formHint}</p>
      </div>
      <a class="btn ghost" href="#/people">${PEOPLE_COPY.cancel}</a>
    </div>
    <form class="add-card person-form" id="person-form" novalidate>
      ${personFormField({
        name: "id",
        label: PEOPLE_COPY.sicil,
        value: person.id,
        required: true,
        disabled: editing,
      })}
      ${personFormField({ name: "name", label: PEOPLE_COPY.name, value: person.name, required: true })}
      ${personFormField({ name: "position", label: PEOPLE_COPY.position, value: person.position })}
      ${personFormField({ name: "center", label: PEOPLE_COPY.center, value: person.center })}
      ${personFormField({
        name: "email",
        label: PEOPLE_COPY.email,
        value: person.email,
        type: "text",
        hint: PEOPLE_COPY.emailHint,
      })}
      <p class="form-error" id="person-form-error" hidden></p>
      <div class="modal-actions">
        <a class="btn ghost" href="#/people">${PEOPLE_COPY.cancel}</a>
        <button class="btn primary" type="submit">${PEOPLE_COPY.save}</button>
      </div>
    </form>
  `;
  const form = $app.querySelector("#person-form");
  const errorEl = $app.querySelector("#person-form-error");
  const showError = (text) => {
    errorEl.hidden = !text;
    errorEl.textContent = text || "";
  };
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    const id = editing ? person.id : (data.id || "").trim();
    const name = (data.name || "").trim();
    if (!id || !name) {
      showError(PEOPLE_COPY.required);
      return;
    }
    const payload = {
      name,
      position: (data.position || "").trim(),
      center: (data.center || "").trim(),
      email: (data.email || "").trim(),
    };
    try {
      if (editing) {
        await api(`/api/people/${encodeURIComponent(id)}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        toast(PEOPLE_COPY.updated);
      } else {
        await api("/api/people", {
          method: "POST",
          body: JSON.stringify({ id, ...payload }),
        });
        toast(PEOPLE_COPY.added);
      }
      location.hash = "#/people";
    } catch (err) {
      if (err.status === 409 || err.code === "duplicate_id") {
        showError(PEOPLE_COPY.duplicate);
        return;
      }
      showError(err.message === "missing_id_or_name" ? PEOPLE_COPY.required : err.message);
    }
  });
}

async function renderPerson(id) {
  const report = await api(`/api/people/${id}/report`);
  const role = personSubtitle(report.person);
  $app.innerHTML = `
    <div class="top">
      <div>
        <h2>${escapeHtml(report.person.name)}</h2>
        ${role ? `<p class="sub">${escapeHtml(role)}</p>` : ""}
      </div>
      <div class="live-actions">
        <a class="btn ghost" href="#/people">${PEOPLE_COPY.title}</a>
        <a class="btn ghost" href="#/people/${encodeURIComponent(report.person.id)}/edit">${PEOPLE_COPY.edit}</a>
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
