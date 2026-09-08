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

## First roster (optional)

Copy `seed/people.example.json` to `seed/people.json` and replace the example row with your group. Restart the app once. `people.json` is gitignored — do not commit real names, sicil, or emails.

Your existing local database is not replaced on `git pull`.

## What stays off git

- `data/attendance.db` — attendance
- `seed/people.json` — roster
- Excel/CSV roster files
