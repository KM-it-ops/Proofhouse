import { expect, test } from "@playwright/test";
import {
  assertVisibleFocusOutline,
  findMouseOnlyPointerTargets,
  listVisibleInteractiveControls,
} from "./dom-helpers";
import { WORLDS } from "./worlds";

test("[keyboard] tab order, focus rings, pointer targets, Enter and Space", async ({ page }) => {
  await page.goto("/?world=hybrid");

  const controls = await listVisibleInteractiveControls(page);
  expect(controls.length).toBeGreaterThan(0);

  await page.keyboard.press("Tab");
  for (let i = 0; i < controls.length; i++) {
    const active = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      return { tag: el.tagName.toLowerCase(), text: (el.textContent ?? "").trim().slice(0, 80) };
    });
    expect(active).toEqual(controls[i]);
    await assertVisibleFocusOutline(page);
    if (i < controls.length - 1) {
      await page.keyboard.press("Tab");
    }
  }

  const mouseOnly = await findMouseOnlyPointerTargets(page);
  expect(mouseOnly).toEqual([]);

  const foundry = WORLDS.find((w) => w.id === "foundry");
  expect(foundry).toBeDefined();
  await page.getByRole("button", { name: foundry!.tabLabel, exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("h1")).toHaveText(foundry!.heading);

  const blitz = page.locator("button.full-blitz");
  await blitz.focus();
  await expect(blitz).not.toHaveClass(/live/);
  await page.keyboard.press("Space");
  await expect(blitz).toHaveClass(/live/);
  await page.keyboard.press("Space");
  await expect(blitz).not.toHaveClass(/live/);
});
