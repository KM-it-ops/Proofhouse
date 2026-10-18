import { expect, test } from "@playwright/test";
import { runningAnimationCount, settleMs } from "./dom-helpers";
import { WORLDS, type WorldId } from "./worlds";

const ANIMATED_WORLDS: WorldId[] = ["overdrive", "hybrid", "foundry"];

async function assertNoRunningAnimations(page: import("@playwright/test").Page): Promise<void> {
  const running = await runningAnimationCount(page);
  expect(running).toBe(0);
}

for (const world of WORLDS) {
  test(`[reduced-motion] ${world.id} has no running animations when reduced`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(`/?world=${world.id}`);
    await settleMs(page, 300);
    await assertNoRunningAnimations(page);

    const card = page.locator(".loadout-card").first();
    await card.hover();
    await card.focus();
    await settleMs(page, 300);
    await assertNoRunningAnimations(page);
  });
}

test("[reduced-motion] control worlds show running animations without reduce", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  for (const worldId of ANIMATED_WORLDS) {
    await page.goto(`/?world=${worldId}`);
    await settleMs(page, 300);
    const running = await runningAnimationCount(page);
    expect(running).toBeGreaterThan(0);
  }
});
