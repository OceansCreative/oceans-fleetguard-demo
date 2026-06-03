import { test, expect } from "@playwright/test";

test.describe("FleetGuard smoke tests", () => {
  test("dashboard renders with app title", async ({ page }) => {
    await page.goto("/");

    // The brand name is always visible in the header
    await expect(page.locator(".brand-name")).toBeVisible();
    await expect(page.locator(".brand-name")).toHaveText("FleetGuard");
  });

  test("fleet vehicle list shows at least one vehicle from WebSocket", async ({
    page,
  }) => {
    await page.goto("/");

    // Wait for vehicle data to arrive over WebSocket — at least one vehicle
    // name must appear in the list (mock data streams shortly after connect).
    const vehicleName = page.locator(".vrow-name").first();
    await expect(vehicleName).toBeVisible({ timeout: 20_000 });

    // Confirm there is at least one vehicle row rendered
    const count = await page.locator(".vrow-name").count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test("basemap switch: clicking Dark makes it active", async ({ page }) => {
    await page.goto("/");

    // Ensure the map switcher is rendered
    const switchGroup = page.locator('[aria-label="Basemap style"]');
    await expect(switchGroup).toBeVisible();

    // Click the Dark button
    const darkBtn = switchGroup.getByRole("button", { name: "Dark" });
    await expect(darkBtn).toBeVisible();
    await darkBtn.click();

    // The Dark button should now have aria-pressed=true and the active class
    await expect(darkBtn).toHaveAttribute("aria-pressed", "true");
    await expect(darkBtn).toHaveClass(/is-active/);

    // Light should no longer be active
    const lightBtn = switchGroup.getByRole("button", { name: "Light" });
    await expect(lightBtn).toHaveAttribute("aria-pressed", "false");
  });
});
