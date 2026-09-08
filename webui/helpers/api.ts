import fs from "node:fs";
import path from "node:path";
import type { APIRequestContext } from "@playwright/test";
import { PROJECT_ROOT, readRuntime, resetEmptyDb } from "./isolated-app.mjs";

export const SYNTHETIC = {
  group5: "Grup 5",
  group7: "Grup 7",
  firstDate: "2026-09-09",
  jane: {
    id: "10001",
    name: "Jane Doe",
    position: "QA Engineer",
    center: "QA",
    email: "jane.doe@example.com",
  },
  ada: {
    id: "10001",
    name: "Ada Lovelace",
    email: "ada.lovelace@example.com",
  },
  adaSeed: {
    id: "10099",
    name: "Ada Lovelace",
    position: "",
    center: "",
    email: "ada.lovelace@example.com",
  },
} as const;

export const VALID_CSV = "sicil,name\n10001,Ada Lovelace\n";
export const BAD_CSV = "sicil,name\n10001,\n";

export function assertNotOperatorDb(dbPath: string) {
  const operator = path.resolve(PROJECT_ROOT, "data", "attendance.db");
  if (path.resolve(dbPath) === operator) {
    throw new Error("Refusing to open operator data/attendance.db");
  }
}

export function resetSharedDb() {
  const runtime = readRuntime();
  assertNotOperatorDb(path.join(runtime.root, "data", "attendance.db"));
  resetEmptyDb(runtime.root);
}

export async function json<T>(res: { json: () => Promise<T>; ok: () => boolean; status: () => number }) {
  return res.json();
}

export async function getMeta(request: APIRequestContext) {
  const res = await request.get("/api/meta");
  return res.json();
}

export async function getPeople(request: APIRequestContext) {
  const res = await request.get("/api/people");
  return res.json();
}

export async function getMeetings(request: APIRequestContext) {
  const res = await request.get("/api/meetings");
  return res.json();
}

export async function configureProfile(
  request: APIRequestContext,
  body: {
    name?: string;
    firstDate?: string;
    endDate?: string | null;
    repeatRule?: "none" | "weekly" | "biweekly" | "monthly";
  } = {},
) {
  const payload = {
    name: body.name ?? SYNTHETIC.group5,
    firstDate: body.firstDate ?? SYNTHETIC.firstDate,
    repeatRule: body.repeatRule ?? "none",
    ...(body.endDate !== undefined ? { endDate: body.endDate } : {}),
  };
  const res = await request.put("/api/profile", { data: payload });
  return { status: res.status(), body: await res.json() };
}

export async function addPerson(
  request: APIRequestContext,
  person: { id: string; name: string; position?: string; center?: string; email?: string },
) {
  const res = await request.post("/api/people", { data: person });
  return { status: res.status(), body: await res.json() };
}

export async function meetingByDate(request: APIRequestContext, date: string) {
  const meetings = await getMeetings(request);
  return meetings.find((m: { date: string }) => m.date === date);
}

export function appPySource(root = readRuntime().root) {
  return fs.readFileSync(path.join(root, "app.py"), "utf8");
}

export function englishSpecStrings() {
  return [
    "Save and continue",
    "don't repeat",
    "first date",
    "group name",
    "end date",
    "Group name",
    "First date",
    "Repeat rule",
    "End date",
    "Save series",
    "Add person",
    "Delete person",
  ];
}
