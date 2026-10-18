import { expect, test } from "@playwright/test";
import { DEFAULT_HEADING, WORLDS } from "./worlds";

const BROKEN_ENCODING = "%E0%A4%A";
const BAD_WORLD_QUERIES = [
  "nope",
  "",
  "x".repeat(400),
  "<img src=x onerror=alert(1)>",
  BROKEN_ENCODING,
];

test("[error-state] invalid ?world= values fall back safely", async ({ page }) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on("pageerror", (err) => pageErrors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  for (const value of BAD_WORLD_QUERIES) {
    pageErrors.length = 0;
    consoleErrors.length = 0;

    // Broken percent-encoding must reach the page as written, so only encode the others.
    const query = value === BROKEN_ENCODING ? `?world=${value}` : `?world=${encodeURIComponent(value)}`;
    await page.goto(`/${query}`);

    await expect(page.locator("h1")).toHaveText(DEFAULT_HEADING);
    await expect(page.locator("img[src='x']")).toHaveCount(0);

    const atlas = WORLDS.find((w) => w.id === "atlas");
    expect(atlas).toBeDefined();
    await page.getByRole("button", { name: atlas!.tabLabel, exact: true }).click();
    await expect(page.locator("h1")).toHaveText(atlas!.heading);

    expect(pageErrors).toEqual([]);
    expect(consoleErrors).toEqual([]);
  }
});
