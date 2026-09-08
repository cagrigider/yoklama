import { configureProfile, getMeetings, getMeta, getPeople, SYNTHETIC } from "../helpers/api";
import { expect, test } from "../helpers/fixtures";
import { completeDontRepeatWizard, openNav, peopleHeading } from "../helpers/ui";

test.describe("wizard empty roster", () => {
  // TC-15
  test("TC-15 zero people persist and empty list is valid", async ({ page, request }) => {
    await page.goto("/");
    await completeDontRepeatWizard(page, SYNTHETIC.group5, SYNTHETIC.firstDate);

    const meta = await getMeta(request);
    expect(meta.configured).toBe(true);
    expect(meta.groupName).toBe(SYNTHETIC.group5);
    const meetings = await getMeetings(request);
    expect(meetings).toHaveLength(1);
    expect(meetings[0].date).toBe(SYNTHETIC.firstDate);
    expect(await getPeople(request)).toEqual([]);

    await openNav(page, "people");
    await expect(peopleHeading(page)).toBeVisible();
    await expect(page.getByText("Henüz kişi yok")).toBeVisible();
    await expect(page.getByRole("link", { name: "Kişi ekle" })).toBeVisible();
  });
});
