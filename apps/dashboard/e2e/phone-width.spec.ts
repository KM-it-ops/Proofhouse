import { expect, test } from "@playwright/test";
import { PHONE_VIEWPORT, WORLDS, type WorldId } from "./worlds";

async function assertFitsPhoneWidth(page: import("@playwright/test").Page, world: WorldId): Promise<void> {
  await page.setViewportSize(PHONE_VIEWPORT);
  await page.goto(`/?world=${world}`);

  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(scrollWidth).toBeLessThanOrEqual(375);

  const overflow = await page.evaluate(() => {
    const maxRight = 375;
    const offenders: string[] = [];
    const tags = ["BUTTON", "H1", "H2", "H3", "P"];
    for (const el of document.querySelectorAll(tags.join(","))) {
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") continue;
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;
      if (rect.left < -1 || rect.right > maxRight + 1) {
        offenders.push(`${el.tagName} "${(el.textContent ?? "").trim().slice(0, 40)}" left=${rect.left} right=${rect.right}`);
      }
    }
    return offenders;
  });
  expect(overflow).toEqual([]);
}

for (const world of WORLDS) {
  test(`[phone-width] ${world.id} content stays within 375px`, async ({ page }) => {
    await assertFitsPhoneWidth(page, world.id);
  });
}
