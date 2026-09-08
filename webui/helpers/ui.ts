import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";
import { englishSpecStrings } from "./api";

export const wizardHeading = (page: Page) => page.getByRole("heading", { name: "Grubunu ayarla" });
export const meetingsHeading = (page: Page) => page.locator("#meeting-list-title");
export const settingsHeading = (page: Page) => page.getByRole("heading", { name: "Ayarlar" });
export const peopleHeading = (page: Page) => page.getByRole("heading", { name: "Kişiler", exact: true });

export async function expectWizard(page: Page) {
  await expect(wizardHeading(page)).toBeVisible();
  await expect(page.getByLabel(/Grup adı/)).toBeVisible();
  await expect(page.getByLabel(/İlk toplantı tarihi/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Tekrarlama yok" })).toBeVisible();
  await expect(page.locator("#meeting-list")).toHaveCount(0);
  await expect(page.locator("#add-meeting")).toHaveCount(0);
  await expect(page.locator("#person-form")).toHaveCount(0);
}

export async function expectMeetingList(page: Page) {
  await expect(page.locator("#add-meeting")).toBeVisible();
  await expect(wizardHeading(page)).toHaveCount(0);
}

export async function openNav(page: Page, key: "home" | "people" | "settings") {
  await page.locator(`[data-nav="${key}"]`).click();
}

export async function assertNoEnglishSpecCopy(page: Page) {
  const text = await page.locator("#app").innerText();
  for (const banned of englishSpecStrings()) {
    expect(text, `spec-English label leaked: ${banned}`).not.toContain(banned);
  }
}

export async function completeDontRepeatWizard(page: Page, name = "Grup 5", firstDate = "2026-09-09") {
  await expectWizard(page);
  await page.getByLabel(/Grup adı/).fill(name);
  await page.getByLabel(/İlk toplantı tarihi/).fill(firstDate);
  await page.getByRole("button", { name: "Tekrarlama yok" }).click();
  await page.getByRole("button", { name: "Kaydet ve devam et" }).click();
  await expectMeetingList(page);
}

export async function waitInputLock(page: Page) {
  await page.waitForTimeout(600);
}
