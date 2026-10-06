import { addPerson, configureProfile, SYNTHETIC } from "../helpers/api";
import { expect, test } from "../helpers/fixtures";
import { assertNoEnglishSpecCopy, openNav } from "../helpers/ui";

test.describe("certificates UI", () => {
  test.beforeEach(async ({ request }) => {
    expect((await configureProfile(request)).status).toBeLessThan(300);
  });

  test("catalog add, counts, have/have-not lists, person paste validation", async ({
    page,
    request,
  }) => {
    expect((await addPerson(request, SYNTHETIC.jane)).status).toBeLessThan(300);
    expect(
      (
        await addPerson(request, {
          id: "10002",
          name: "Jordan Example",
          position: "",
          center: "",
          email: "",
        })
      ).status,
    ).toBeLessThan(300);

    await page.goto("/#/");
    await expect(page.locator('[data-nav="certificates"]')).toHaveText("Sertifikalar");
    await openNav(page, "certificates");
    await expect(page.getByRole("heading", { name: "Sertifikalar", exact: true })).toBeVisible();
    await expect(page.getByText("Henüz sertifika yok")).toBeVisible();

    await page.getByRole("link", { name: "Sertifika ekle" }).click();
    await page.getByLabel(/Sertifika adı/).fill("Building with the Claude API");
    await page.getByRole("button", { name: "Kaydet" }).click();
    await expect(page.getByRole("heading", { name: "Building with the Claude API" })).toBeVisible();
    await expect(page.getByText("0 / 2 kişi aldı")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Aldı" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Almadı" })).toBeVisible();
    await expect(page.getByRole("link", { name: /Jane Doe/ })).toBeVisible();
    await expect(page.getByRole("link", { name: /Jordan Example/ })).toBeVisible();

    await openNav(page, "certificates");
    await expect(page.getByText("0 / 2 kişi aldı")).toBeVisible();
    await assertNoEnglishSpecCopy(page);

    await page.goto("/#/people/10001");
    await expect(page.getByRole("heading", { name: "Jane Doe" })).toBeVisible();
    await page.getByLabel(/Doğrulama bağlantısı/).fill("not-a-code");
    await page.getByRole("button", { name: "Kontrol et ve kaydet" }).click();
    await expect(page.getByText("Kayıt yapılmadı")).toBeVisible();
    await expect(page.getByText(/doğrulama kodu/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Yine de kaydet" })).toBeHidden();

    const listed = await request.get("/api/certificates");
    expect(listed.ok()).toBeTruthy();
    const certs = (await listed.json()) as { haveCount: number }[];
    expect(certs[0].haveCount).toBe(0);
  });
});
