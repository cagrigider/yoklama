import { addPerson, configureProfile, getPeople, meetingByDate, SYNTHETIC } from "../helpers/api";
import { expect, test } from "../helpers/fixtures";
import { assertNoEnglishSpecCopy, peopleHeading } from "../helpers/ui";

test.describe("people UI", () => {
  test.beforeEach(async ({ request }) => {
    expect((await configureProfile(request)).status).toBeLessThan(300);
  });

  // TC-33
  test("TC-33 edit fields; sicil locked", async ({ page, request }) => {
    expect((await addPerson(request, { id: "10001", name: "Jane Doe" })).status).toBeLessThan(300);

    const edited = await request.put("/api/people/10001", {
      data: {
        name: "Jane Q. Doe",
        position: "QA Engineer",
        center: "QA",
        email: "jane.doe@example.com",
      },
    });
    expect(edited.status()).toBeLessThan(300);
    let person = (await edited.json()) as { id: string; name: string };
    expect(person.id).toBe("10001");
    expect(person.name).toBe("Jane Q. Doe");

    const sneak = await request.put("/api/people/10001", {
      data: { id: "10002", name: "Jane Q. Doe", position: "QA Engineer", center: "QA" },
    });
    expect(sneak.status()).toBeLessThan(300);
    person = await sneak.json();
    expect(person.id).toBe("10001");

    await page.goto("/#/people/10001/edit");
    const sicil = page.locator("#person-id");
    await expect(sicil).toBeDisabled();
    await expect(sicil).toHaveValue("10001");
  });

  // TC-34
  test("TC-34 delete confirm / cancel", async ({ page, request }) => {
    expect((await addPerson(request, { id: "10001", name: "Jane Doe" })).status).toBeLessThan(300);
    const meeting = await meetingByDate(request, SYNTHETIC.firstDate);
    const mark = await request.put(`/api/meetings/${meeting.id}/attendance/10001`, {
      data: { status: "present" },
    });
    expect(mark.status()).toBeLessThan(300);

    await page.goto("/#/people");
    await page.locator(".meeting-card", { hasText: "Jane Doe" }).getByRole("button", { name: "Sil" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("yoklama");
    await dialog.getByRole("button", { name: "Vazgeç" }).click();
    expect((await getPeople(request)).some((p: { id: string }) => p.id === "10001")).toBe(true);
    const roster = await (await request.get(`/api/meetings/${meeting.id}/roster`)).json();
    expect(roster.roster.find((p: { id: string }) => p.id === "10001").status).toBe("present");

    await page.locator(".meeting-card", { hasText: "Jane Doe" }).getByRole("button", { name: "Sil" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("dialog").getByRole("button", { name: "Evet, sil" }).click();
    await expect(page.getByText("Kişi silindi")).toBeVisible();
    expect(await getPeople(request)).toEqual([]);
    const after = await (await request.get(`/api/meetings/${meeting.id}/roster`)).json();
    expect(after.roster.find((p: { id: string }) => p.id === "10001")).toBeFalsy();
  });

  // TC-35
  test("TC-35 empty people list is valid", async ({ page, request }) => {
    expect(await getPeople(request)).toEqual([]);
    await page.goto("/#/people");
    await expect(peopleHeading(page)).toBeVisible();
    await expect(page.getByText("Henüz kişi yok")).toBeVisible();
    await expect(page.getByRole("link", { name: "Kişi ekle" })).toBeVisible();
  });

  // TC-36
  test("TC-36 position and center visible on people and live roster", async ({ page, request }) => {
    expect((await addPerson(request, SYNTHETIC.jane)).status).toBeLessThan(300);
    await page.goto("/#/people");
    const card = page.locator(".meeting-card", { hasText: "Jane Doe" });
    await expect(card).toContainText("QA Engineer");
    await expect(card).toContainText("QA");

    await page.goto("/#/people/10001");
    await expect(page.getByText("QA Engineer · QA")).toBeVisible();

    const meeting = await meetingByDate(request, SYNTHETIC.firstDate);
    await page.goto(`/#/meeting/${meeting.id}`);
    const row = page.locator(".person-row", { hasText: "Jane Doe" });
    await expect(row).toContainText("QA Engineer");
    await expect(row).toContainText("QA");
  });

  // TC-37
  test("TC-37 people forms are Turkish", async ({ page, request }) => {
    expect((await addPerson(request, { id: "10001", name: "Jane Doe" })).status).toBeLessThan(300);

    await page.goto("/#/people/new");
    await expect(page.getByRole("heading", { name: "Kişi ekle" })).toBeVisible();
    await expect(page.getByRole("textbox", { name: /Sicil/ })).toBeVisible();
    await expect(page.getByRole("textbox", { name: /^Ad/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "Kaydet" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Vazgeç" }).first()).toBeVisible();
    await assertNoEnglishSpecCopy(page);

    await page.goto("/#/people/10001/edit");
    await expect(page.getByRole("heading", { name: "Kişiyi düzenle" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Kaydet" })).toBeVisible();
    await assertNoEnglishSpecCopy(page);

    await page.goto("/#/people");
    await page.locator(".meeting-card", { hasText: "Jane Doe" }).getByRole("button", { name: "Sil" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: "Kişiyi sil" })).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Evet, sil" })).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Vazgeç" })).toBeVisible();
    const dialogText = await dialog.innerText();
    expect(dialogText).not.toContain("Delete person");
    expect(dialogText).not.toContain("Cancel");
  });
});
