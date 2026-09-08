# Yoklama

Local meeting attendance for one AI Champion and one group. The server binds to `127.0.0.1` only. Marks live in `data/attendance.db` on that machine.

## Run

```bash
git clone https://github.com/cagrigider/yoklama.git
cd yoklama
python3 app.py
```

Open http://127.0.0.1:8765

Python 3 is enough. No extra packages.

An empty database opens a first-run wizard (group name, first date, repeat). A database that already has meetings gets a default profile on startup and skips the wizard.

`GET /api/meta` includes `configured` (boolean) and `groupName` (string), plus the existing meta fields. Wizard and Settings save with `PUT /api/profile` and JSON `{ "name", "firstDate", "endDate" or null, "repeatRule": "none"|"weekly"|"biweekly"|"monthly" }`. There is no second protocol and no `/api/setup` alias.

## First roster (optional)

Copy `seed/people.example.json` to `seed/people.json` and replace the example row with your group. Restart the app once. `people.json` is gitignored — do not commit real names, sicil, or emails.

You can also import a roster from the first-run wizard (optional file) or later from Settings. The client reads the file and `POST`s JSON to `/api/people/import` as `{ "filename", "text" }` or `{ "filename", "contentBase64" }` — not multipart.

### Roster columns

Required: **sicil** or **id**, and **name**.

Optional: **position**, **center** / **yetkinlik**. If **email** is present it is stored; it is not required.

Excel means a **simple first sheet** (shared or inline strings). Macros, extra header rows, or a password-protected workbook are rejected — save as CSV and try again. CSV is UTF-8 (a BOM is fine). JSON is an array like `seed/people.example.json`. Import upserts by sicil/`id` and does not delete people missing from the file. A rejected import does not undo a saved group profile or meetings.

Your existing local database is not replaced on `git pull`.

## What stays off git

The git-tracked tree omits `data/*.db` and a real `seed/people.json`. Tracked example seed stays synthetic (`seed/people.example.json`).

- `data/attendance.db` — attendance
- `seed/people.json` — roster
- Excel/CSV roster files
