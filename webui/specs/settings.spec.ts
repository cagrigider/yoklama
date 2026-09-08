import {
  configureProfile,
  getMeetings,
  getMeta,
  SYNTHETIC,
} from "../helpers/api";
import { expect, test } from "../helpers/fixtures";
import { assertNoEnglishSpecCopy, expectMeetingList, openNav, settingsHeading, wizardHeading } from "../helpers/ui";

async function openSettings(page: import("@playwright/test").Page) {
  await page.goto("/#/settings");
  await expect(settingsHeading(page)).toBeVisible();
}

test.describe("settings and chrome", () => {
  test.beforeEach(async ({ request }) => {
    const saved = await configureProfile(request);
    expect(saved.status).toBeLessThan(300);
  });

  // TC-18
  test("TC-18 Settings fill-gaps and inverted end date reject", async ({ page, request }) => {
    await page.goto("/");
    await expectMeetingList(page);
    await openNav(page, "settings");
    await expect(settingsHeading(page)).toBeVisible();
    await expect(page.locator("#settings-import")).toBeVisible();
    await expect(page.locator("#settings-roster-file")).toHaveValue("");

    await page.getByLabel(/Grup adı/).fill(SYNTHETIC.group7);
    await page.getByLabel(/İlk toplantı tarihi/).fill("2026-09-09");
    await page.getByRole("button", { name: "2 haftada bir" }).click();
    await page.getByLabel(/Bitiş tarihi/).fill("2026-10-07");
    await page.getByRole("button", { name: "Kaydet", exact: true }).click();
    await expect(page.getByText("Ayarlar kaydedildi")).toBeVisible();

    const meta = await getMeta(request);
    expect(meta.groupName).toBe(SYNTHETIC.group7);
    const dates = (await getMeetings(request)).map((m: { date: string }) => m.date);
    expect(dates).toEqual(expect.arrayContaining(["2026-09-09", "2026-09-23", "2026-10-07"]));
    expect(dates).not.toContain("2026-09-16");

    await openSettings(page);
    await page.getByRole("button", { name: "2 haftada bir" }).click();
    await page.getByLabel(/Bitiş tarihi/).fill("2026-09-01");
    await page.getByRole("button", { name: "Kaydet", exact: true }).click();
    await expect(page.locator("#settings-error")).toBeVisible();
    await expect(page.locator("#settings-error")).toContainText("Bitiş tarihi ilk tarihten önce olamaz");
    const after = (await getMeetings(request)).map((m: { date: string }) => m.date);
    expect(after).toEqual(dates);

    const inverted = await request.put("/api/profile", {
      data: {
        name: SYNTHETIC.group7,
        firstDate: "2026-09-09",
        endDate: "2026-09-01",
        repeatRule: "biweekly",
      },
    });
    expect([400, 422]).toContain(inverted.status());
    const still = (await getMeetings(request)).map((m: { date: string }) => m.date);
    expect(still).toEqual(dates);
  });

  // TC-19
  test("TC-19 header shows group name", async ({ page }) => {
    await page.goto("/#/");
    await expect(page.locator("#group-name")).toHaveText(SYNTHETIC.group5);
    await expect(page.locator("#meeting-list-title")).toHaveText(SYNTHETIC.group5);
  });

  // TC-20
  test("TC-20 configured chrome and extra meeting CUD", async ({ page, request }) => {
    await page.goto("/");
    await expectMeetingList(page);
    await expect(wizardHeading(page)).toHaveCount(0);
    await expect(page.locator('[data-nav="settings"]')).toHaveText("Ayarlar");
    await expect(page.locator('[data-nav="people"]')).toHaveText("Kişiler");

    await openNav(page, "settings");
    await expect(page.locator("#settings-import")).toBeVisible();
    await expect(page.locator("#settings-roster-file")).toHaveValue("");

    const created = await request.post("/api/meetings", {
      data: { title: "Ekstra CUD", date: "2026-09-12" },
    });
    expect(created.status()).toBe(201);
    const extra = await created.json();
    expect(extra.kind).toBe("extra");

    const updated = await request.put(`/api/meetings/${extra.id}`, {
      data: { title: "Ekstra CUD 2", date: "2026-09-12", notes: "" },
    });
    expect(updated.status()).toBe(200);

    const deleted = await request.delete(`/api/meetings/${extra.id}`);
    expect(deleted.status()).toBe(200);
    const left = await getMeetings(request);
    expect(left.some((m: { id: number }) => m.id === extra.id)).toBe(false);

    await page.goto("/#/");
    await page.locator("#add-meeting").locator('[name="title"]').fill("UI Ekstra");
    await page.locator("#add-meeting").locator('[name="date"]').fill("2026-09-13");
    await page.getByRole("button", { name: "Ekle" }).click();
    await expect(page).toHaveURL(/#\/meeting\/\d+/);
    const uiMeetings = await getMeetings(request);
    const uiExtra = uiMeetings.find((m: { title: string }) => m.title === "UI Ekstra");
    expect(uiExtra).toBeTruthy();
    expect(uiExtra.kind).toBe("extra");
  });

  // TC-23
  test("TC-23 Settings labels are Turkish", async ({ page }) => {
    await openSettings(page);
    await expect(page.locator("html")).toHaveAttribute("lang", "tr");
    await expect(page.getByLabel(/Grup adı/)).toBeVisible();
    await expect(page.getByLabel(/İlk toplantı tarihi/)).toBeVisible();
    await expect(page.getByText("Tekrar", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Kaydet", exact: true })).toBeVisible();
    await assertNoEnglishSpecCopy(page);
  });
});
