# Test Cases — Yoklama shareable setup

| Field | Value |
|-------|-------|
| Date | 2026-09-08 |
| Slug | yoklama-setup |
| Source | FRD-yoklama-setup.en.md, uiux/screens.md (no services.md) |
| Language | EN |
| Format | Gherkin (English keywords) |

No `services.md` (ba-services skipped). BE cases describe local HTTP/SQLite behaviour from the FRD. Operator approved BE and FE drafts 2026-09-08. NFR-001 is ⚠ (not designed as an automated acceptance case).

## 1. Backend (BE) Scenarios

```gherkin
Feature: Local group profile, series, and roster

  @TC-BE-001 @FR-001
  Scenario: Empty database has no group profile
    Given a fresh local database with no people and no meetings
    Then the system has no group profile

  @TC-BE-002 @FR-002
  Scenario: Existing profile is not treated as first-run
    Given a local database with a saved group profile
    When the app starts
    Then the system does not require first-run setup

  @TC-BE-003 @FR-003
  Scenario: Don't-repeat creates only the first date
    Given no group profile
    When the champion saves first-run with first date 2026-09-09 and repeat "don't repeat"
    Then a group profile is stored
    And exactly one meeting exists on 2026-09-09

  @TC-BE-004 @FR-004
  Scenario: Biweekly series fills weekdays through end date
    Given no group profile
    When the champion saves first-run with first date 2026-09-09, end date 2026-10-07, repeat every 2 weeks
    Then meetings exist on 2026-09-09, 2026-09-23, and 2026-10-07
    And no meeting exists on 2026-09-16

  @TC-BE-005 @FR-005
  Scenario: End date before first date is rejected
    Given no group profile
    When the champion saves first-run with first date 2026-09-09, end date 2026-09-01, repeat every week
    Then the save is rejected
    And no group profile is stored
    And no meetings are created

  @TC-BE-006 @FR-006
  Scenario: Series generation skips dates that already have a meeting
    Given a meeting on 2026-09-23 with attendance marks
    And a group profile with first date 2026-09-09, end date 2026-10-07, repeat every 2 weeks
    When series generation runs
    Then the meeting on 2026-09-23 and its marks still exist
    And missing dates in range are inserted

  @TC-BE-007 @FR-008
  Scenario: Profile saves with an empty roster
    Given no group profile and no people
    When the champion completes first-run without a roster file
    Then a group profile is stored
    And the people list is empty

  @TC-BE-008 @FR-009
  Scenario: Import upserts by sicil and does not delete extra people
    Given person 10001 named "Old Name" and person 10002 named "Keep Me"
    When the champion imports a valid file that contains only 10001 named "New Name"
    Then person 10001 has name "New Name"
    And person 10002 still exists

  @TC-BE-009 @FR-010
  Scenario: Import with one invalid row changes nothing
    Given person 10001 exists
    When the champion imports a file where one row has no name
    Then the import is rejected
    And person 10001 is unchanged
    And no new people are added

  @TC-BE-010 @FR-011
  Scenario: Add person with sicil and name
    When the champion adds a person with id "10099" and name "Ada"
    Then that person is on the roster

  @TC-BE-011 @FR-012
  Scenario: Edit cannot change sicil
    Given person 10001 exists
    When the champion submits an edit that would change id to "10002"
    Then the id remains "10001"

  @TC-BE-012 @FR-013
  Scenario: Delete person removes their attendance
    Given person 10001 has attendance on a meeting
    When the champion deletes person 10001
    Then person 10001 is gone
    And that meeting has no attendance row for 10001

  @TC-BE-013 @FR-014
  Scenario: Add person without name is rejected
    When the champion adds a person with id "10099" and empty name
    Then no person is created

  @TC-BE-014 @FR-015 @NFR-002
  Scenario: Server listens only on localhost
    When the app is running
    Then it accepts connections on 127.0.0.1
    And it does not listen on 0.0.0.0

  @TC-BE-015 @NFR-004
  Scenario: Existing database survives app files being updated
    Given data/attendance.db already contains people and marks
    When the application files are replaced as in a git pull
    Then the same database file still contains those people and marks

  @TC-BE-016 @FR-016
  Scenario: Tracked tree omits real roster and database
    Given the git repository as shared
    Then seed/people.json is not tracked
    And data/*.db is not tracked
    And README lists required columns sicil or id and name
```

## 2. Frontend (FE) Scenarios

```gherkin
Feature: First-run, Settings, and people UI

  @TC-FE-001 @FR-001 @SCR-01
  Scenario: Empty install opens the wizard
    Given a fresh local database
    When the champion opens the app
    Then the first-run wizard is shown
    And the meeting list is not the first screen

  @TC-FE-002 @FR-002 @SCR-02
  Scenario: Configured install skips the wizard
    Given a saved group profile
    When the champion opens the app
    Then the meeting list is shown
    And the first-run wizard is not shown

  @TC-FE-003 @FR-003 @SCR-01
  Scenario: Don't repeat hides end date
    Given the first-run wizard is open
    When the champion chooses don't repeat
    Then the end date field is hidden

  @TC-FE-004 @FR-005 @SCR-01
  Scenario: End date before first date shows an error
    Given the first-run wizard is open with a repeating rule
    When the champion sets end date before first date and saves
    Then an error is shown
    And the meeting list is not opened

  @TC-FE-005 @FR-019 @SCR-02
  Scenario: Header shows the group name
    Given group name "Grup 5" is saved
    When the champion is on the meeting list
    Then the header shows "Grup 5"

  @TC-FE-006 @FR-006 @FR-007 @SCR-04
  Scenario: Settings save does not remove existing meetings
    Given two extra meetings already exist
    When the champion saves Settings with a shorter end date
    Then those extra meetings are still listed

  @TC-FE-007 @FR-010 @SCR-01 @SCR-04
  Scenario: Rejected import explains the failure
    Given the champion selected a file with a row missing name
    When they import
    Then an error is shown
    And the people list is unchanged

  @TC-FE-008 @FR-008 @SCR-05
  Scenario: Wizard without a file leaves people empty
    Given the champion finishes first-run without a roster file
    When they open People
    Then the list is empty

  @TC-FE-009 @FR-014 @SCR-06
  Scenario: Add person requires id and name
    Given the add person form is open
    When the champion saves with name empty
    Then the person is not created
    And a validation message is shown

  @TC-FE-010 @FR-012 @SCR-06
  Scenario: Sicil is locked when editing
    Given the edit form for person 10001 is open
    Then the sicil field is disabled

  @TC-FE-011 @FR-013 @SCR-07
  Scenario: Delete confirm warns and then removes the person
    Given a person with past marks
    When the champion confirms delete
    Then the warning said their attendance would be removed
    And the person is gone from the people list

  @TC-FE-012 @FR-017 @SCR-03
  Scenario: Live tick still marks joined
    Given a configured meeting roster
    When the champion taps joined for a person
    Then that person is shown as joined

  @TC-FE-013 @NFR-003 @SCR-01 @SCR-04
  Scenario: Wizard and Settings are in Turkish
    When the champion opens the wizard or Settings
    Then labels are in Turkish

  @TC-FE-014 @FR-018 @SCR-03
  Scenario: Center is shown when present
    Given a person with center "QA"
    When the champion views the live roster
    Then "QA" is shown on that row
```

## 3. Coverage Matrix

| FR / NFR | Covering Scenarios |
|----------|--------------------|
| FR-001 | @TC-BE-001, @TC-FE-001 |
| FR-002 | @TC-BE-002, @TC-FE-002 |
| FR-003 | @TC-BE-003, @TC-FE-003 |
| FR-004 | @TC-BE-004 |
| FR-005 | @TC-BE-005, @TC-FE-004 |
| FR-006 | @TC-BE-006, @TC-FE-006 |
| FR-007 | @TC-FE-006 |
| FR-008 | @TC-BE-007, @TC-FE-008 |
| FR-009 | @TC-BE-008 |
| FR-010 | @TC-BE-009, @TC-FE-007 |
| FR-011 | @TC-BE-010 |
| FR-012 | @TC-BE-011, @TC-FE-010 |
| FR-013 | @TC-BE-012, @TC-FE-011 |
| FR-014 | @TC-BE-013, @TC-FE-009 |
| FR-015 | @TC-BE-014 |
| FR-016 | @TC-BE-016 |
| FR-017 | @TC-FE-012 |
| FR-018 | @TC-FE-014 |
| FR-019 | @TC-FE-005 |
| NFR-001 | ⚠ not covered (1s save — performance, not an acceptance scenario here) |
| NFR-002 | @TC-BE-014, @TC-BE-016 |
| NFR-003 | @TC-FE-013 |
| NFR-004 | @TC-BE-015 |
