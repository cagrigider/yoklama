import {
  BAD_CSV,
  configureProfile,
  getMeta,
  getPeople,
  resetSharedDb,
  SYNTHETIC,
  VALID_CSV,
} from "../helpers/api";
import { expect, test } from "../helpers/fixtures";
import { completeDontRepeatWizard, expectMeetingList, expectWizard, openNav, settingsHeading } from "../helpers/ui";

test.describe("roster import UI", () => {
  // TC-29
  test("TC-29 wizard and Settings import share upsert; reject keeps profile", async ({ page, request }) => {
    const adaFile = () => ({
      name: "roster.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(VALID_CSV, "utf8"),
    });
    const badFile = () => ({
      name: "bad.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(BAD_CSV, "utf8"),
    });

    // Run A — wizard optional file
    await page.goto("/");
    await expectWizard(page);
    await page.getByLabel(/Grup adı/).fill(SYNTHETIC.group5);
    await page.getByLabel(/İlk toplantı tarihi/).fill(SYNTHETIC.firstDate);
    await page.getByRole("button", { name: "Tekrarlama yok" }).click();
    await page.locator("#wizard-roster-file").setInputFiles(adaFile());
    await page.getByRole("button", { name: "Kaydet ve devam et" }).click();
    await expectMeetingList(page);
    await expect
      .poll(async () => {
        const people = await getPeople(request);
        return people.some((p: { id: string; name: string }) => p.id === "10001" && p.name === "Ada Lovelace");
      })
      .toBe(true);
    expect((await getMeta(request)).configured).toBe(true);

    // Run B — Settings import on a configured empty roster
    resetSharedDb();
    expect((await configureProfile(request)).status).toBeLessThan(300);
    expect(await getPeople(request)).toEqual([]);
    await page.goto("/#/settings");
    await expect(settingsHeading(page)).toBeVisible();
    const settingsFile = page.locator("#settings-roster-file");
    await expect(settingsFile).toBeAttached();
    await settingsFile.setInputFiles(adaFile());
    await page.getByRole("button", { name: "Aktar" }).click();
    await expect
      .poll(async () => {
        const people = await getPeople(request);
        return people.some((p: { id: string }) => p.id === "10001");
      })
      .toBe(true);

    // Run C — invalid file after profile save does not undo profile
    resetSharedDb();
    await page.goto("/");
    await completeDontRepeatWizard(page);
    expect((await getMeta(request)).configured).toBe(true);
    await openNav(page, "settings");
    await expect(page.locator("#settings-roster-file")).toBeAttached();
    await page.locator("#settings-roster-file").setInputFiles(badFile());
    await page.getByRole("button", { name: "Aktar" }).click();
    await expect(page.locator("#settings-import-error")).toBeVisible();
    await expect(page.locator("#settings-import-error")).toContainText("sicil");
    expect((await getMeta(request)).configured).toBe(true);
    expect((await getMeta(request)).groupName).toBe(SYNTHETIC.group5);
    expect(await getPeople(request)).toEqual([]);
  });
});
