import { pickListenPortSync, startIsolated } from "../helpers/isolated-app.mjs";
import { configureProfile, getMeetings, getMeta, getPeople, SYNTHETIC } from "../helpers/api";
import { expect, test } from "../helpers/fixtures";
import {
  assertNoEnglishSpecCopy,
  expectMeetingList,
  expectWizard,
  openNav,
  wizardHeading,
} from "../helpers/ui";

test.describe("wizard gate", () => {
  // TC-9
  test("TC-9 empty clone shows wizard and nav cannot leave it", async ({ page, request }) => {
    const meta = await getMeta(request);
    expect(meta.configured).toBe(false);
    expect(await getMeetings(request)).toEqual([]);
    expect(await getPeople(request)).toEqual([]);

    await page.goto("/");
    await expectWizard(page);

    await openNav(page, "home");
    await expectWizard(page);
    await page.goto("/#/");
    await expectWizard(page);

    await openNav(page, "people");
    await expectWizard(page);
    await page.goto("/#/people");
    await expectWizard(page);

    await page.goto("/#/settings");
    await expectWizard(page);
    await page.goto("/#/meeting/1");
    await expectWizard(page);

    expect((await getMeta(request)).configured).toBe(false);
  });

  // TC-10
  test("TC-10 configured install skips wizard", async ({ page, request }) => {
    const saved = await configureProfile(request);
    expect(saved.status).toBeLessThan(300);
    expect((await getMeta(request)).configured).toBe(true);

    await page.goto("/");
    await expectMeetingList(page);
    await expect(wizardHeading(page)).toHaveCount(0);
  });

  // TC-12 — dedicated temp tree with synthetic seed/people.json (never Grup 8)
  test("TC-12 seed/people.json does not skip wizard", async ({ browser }) => {
    const extra = await startIsolated({
      port: pickListenPortSync(18766),
      seedPeople: [SYNTHETIC.adaSeed],
    });
    try {
      const context = await browser.newContext({
        baseURL: extra.baseURL,
        locale: "tr-TR",
      });
      const page = await context.newPage();
      const people = await (await page.request.get("/api/people")).json();
      expect(people.some((p: { id: string; name: string }) => p.id === "10099" && p.name === "Ada Lovelace")).toBe(
        true,
      );
      const meta = await (await page.request.get("/api/meta")).json();
      expect(meta.configured).toBe(false);
      const meetings = await (await page.request.get("/api/meetings")).json();
      expect(meetings).toEqual([]);

      await page.goto("/");
      await expectWizard(page);
      await context.close();
    } finally {
      await extra.stop();
    }
  });

  // TC-14
  test("TC-14 wizard is Turkish, hides end date, rejects inverted dates", async ({ page, request }) => {
    await page.goto("/");
    await expectWizard(page);
    await expect(page.locator("html")).toHaveAttribute("lang", "tr");
    await assertNoEnglishSpecCopy(page);
    await expect(page.getByRole("button", { name: "Kaydet ve devam et" })).toBeVisible();

    await page.getByRole("button", { name: "Tekrarlama yok" }).click();
    await expect(page.locator("#wizard-end-wrap")).toBeHidden();

    await page.getByLabel(/Grup adı/).fill(SYNTHETIC.group5);
    await page.getByLabel(/İlk toplantı tarihi/).fill("2026-09-09");
    await page.getByRole("button", { name: "Her hafta" }).click();
    await expect(page.locator("#wizard-end-wrap")).toBeVisible();
    await page.getByLabel(/Bitiş tarihi/).fill("2026-09-01");
    await page.getByRole("button", { name: "Kaydet ve devam et" }).click();

    await expect(page.locator("#wizard-error")).toBeVisible();
    await expect(page.locator("#wizard-error")).toContainText("Bitiş tarihi ilk tarihten önce olamaz");
    await expectWizard(page);
    expect((await getMeta(request)).configured).toBe(false);
  });
});
