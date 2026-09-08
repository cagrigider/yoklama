import {
  addPerson,
  appPySource,
  configureProfile,
  meetingByDate,
  SYNTHETIC,
} from "../helpers/api";
import { expect, test } from "../helpers/fixtures";
import { waitInputLock } from "../helpers/ui";

test.describe("live tick", () => {
  // TC-21
  test("TC-21 live tick, tags, notes, summaries; attendance UPSERT remains", async ({ page, request }) => {
    const saved = await configureProfile(request);
    expect(saved.status).toBeLessThan(300);
    const person = await addPerson(request, SYNTHETIC.jane);
    expect(person.status).toBeLessThan(300);
    const meeting = await meetingByDate(request, SYNTHETIC.firstDate);
    expect(meeting).toBeTruthy();

    const src = appPySource();
    expect(src).toMatch(/\/api\/meetings\/.*\/attendance\//);
    expect(src).toContain("ON CONFLICT(meeting_id, person_id) DO UPDATE");

    await page.goto(`/#/meeting/${meeting.id}`);
    const row = page.locator(".person-row", { hasText: SYNTHETIC.jane.name });
    await expect(row).toBeVisible();

    await row.getByRole("button", { name: "Katıldı" }).click();
    await expect(row.getByRole("button", { name: "Katıldı" })).toHaveAttribute("aria-pressed", "true");
    let roster = await (await request.get(`/api/meetings/${meeting.id}/roster`)).json();
    expect(roster.roster[0].status).toBe("present");

    await waitInputLock(page);
    await row.getByRole("button", { name: "Gelmedi" }).click();
    await expect(row.getByRole("button", { name: "Gelmedi" })).toHaveAttribute("aria-pressed", "true");
    roster = await (await request.get(`/api/meetings/${meeting.id}/roster`)).json();
    expect(roster.roster[0].status).toBe("absent");

    await waitInputLock(page);
    await row.getByRole("button", { name: "Soru sordu" }).click();
    await expect(row.locator('[data-tag="question"]')).toHaveAttribute("data-on", "true");
    await waitInputLock(page);
    await row.locator(".note").fill("deneme notu");
    await row.locator(".note").blur();
    await expect.poll(async () => {
      const fresh = await (await request.get(`/api/meetings/${meeting.id}/roster`)).json();
      return fresh.roster[0].note;
    }).toBe("deneme notu");

    await page.reload();
    const rowAfter = page.locator(".person-row", { hasText: SYNTHETIC.jane.name });
    await expect(rowAfter.locator('[data-tag="question"]')).toHaveAttribute("data-on", "true");
    await expect(rowAfter.locator(".note")).toHaveValue("deneme notu");

    await page.goto(`/#/meeting/${meeting.id}/report`);
    await expect(page.locator("#summary.summary, pre.summary")).toBeVisible();
    await expect(page.getByRole("button", { name: "Özeti kopyala" })).toBeVisible();

    await page.goto(`/#/people/${SYNTHETIC.jane.id}`);
    await expect(page.getByRole("button", { name: "Yönetici özetini kopyala" })).toBeVisible();
    await expect(page.locator(".report-card")).toBeVisible();
  });
});
