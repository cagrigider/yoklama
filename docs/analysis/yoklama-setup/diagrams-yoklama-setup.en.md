# Modeling diagrams — Yoklama shareable setup

| Field | Value |
|-------|-------|
| Date | 2026-09-08 |
| Slug | yoklama-setup |
| Locale | en |
| Source | BRD-yoklama-setup.en.md |
| Filename style | locale-suffixed (default; no `_memory/MEMORY.md`) |

Mermaid blocks are language-neutral. Operator confirmed all four drafts 2026-09-08. Primary sequence: empty-clone first-run.

## 1. Activity (process flow)

```mermaid
flowchart TD
  start([Open app]) --> hasProfile{Group profile exists?}
  hasProfile -->|yes| list[Meeting list]
  hasProfile -->|no| wizard[First-run wizard: name, first date, repeat]
  wizard --> repeat{Repeat?}
  repeat -->|don't repeat| saveOne[Save profile + meeting on first date]
  repeat -->|week / 2 weeks / month| needEnd[Require end date]
  needEnd --> valid{End date >= first date?}
  valid -->|no| rejectDates[Reject save]
  rejectDates --> wizard
  valid -->|yes| saveSeries[Save profile + fill-gap meetings]
  saveOne --> importQ{Import roster now?}
  saveSeries --> importQ
  importQ -->|skip| list
  importQ -->|Excel CSV or JSON| rows{Every row has id or sicil and name?}
  rows -->|no| rejectFile[Reject whole file]
  rejectFile --> importQ
  rows -->|yes| upsert[Upsert people by id]
  upsert --> list
  list --> settings[Settings]
  settings --> nameOrSeries[Change name or series bounds]
  settings --> importQ
  settings --> peopleUi[Add edit or delete people]
  nameOrSeries --> fillGaps[Insert missing dates only]
  fillGaps --> list
  peopleUi --> list
```

## 2. Sequence (empty clone first-run)

```mermaid
sequenceDiagram
  actor Champion
  participant App
  participant DB
  Champion->>App: Open http://127.0.0.1:8765
  App->>DB: Group profile?
  DB-->>App: none
  App-->>Champion: First-run wizard
  Champion->>App: name, first date, repeat, optional end date, optional file
  alt invalid dates
    App-->>Champion: Error, no writes
  else valid
    App->>DB: Insert profile
    App->>DB: Insert missing meetings
    alt file present and any row invalid
      App-->>Champion: Reject file, people unchanged
    else file present and valid
      App->>DB: Upsert people
    else no file
      Note over App,DB: Roster may stay empty
    end
    App-->>Champion: Meeting list
  end
```

## 3. State (primary entity: GroupProfile)

```mermaid
stateDiagram-v2
  [*] --> Unconfigured
  Unconfigured --> Configured: wizard saved
  Configured --> Configured: Settings save fill-gaps
  Configured --> Configured: import or people CRUD
```

No transition back to Unconfigured. Person delete removes that person and their attendance; it does not unconfigure the install.

## 4. ER (entities)

```mermaid
erDiagram
  GROUP_PROFILE ||--o{ MEETING : "install has"
  PERSON ||--o{ ATTENDANCE : has
  MEETING ||--o{ ATTENDANCE : has
  GROUP_PROFILE {
    string name
    date firstDate
    date endDate
    string repeatRule
  }
  PERSON {
    string id PK
    string name
    string position
    string center
    string email
  }
  MEETING {
    int id PK
    string title
    date date
    string kind
    string notes
  }
  ATTENDANCE {
    int meetingId FK
    string personId FK
    string status
    string tags
    string note
  }
```

Cardinality: one GroupProfile per install. Delete person cascades that person's attendance. Generating a series never deletes Meeting or Attendance rows.

> Render note: open this file in a mermaid-compatible viewer (GitHub, VS Code mermaid extension, etc.) to see the diagrams drawn.
