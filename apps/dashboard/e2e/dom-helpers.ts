import type { Page } from "@playwright/test";

const INTERACTIVE_SELECTOR =
  "button, a[href], input, select, textarea, summary, [tabindex]:not([tabindex='-1']), [role='button']";

export type InteractiveControl = {
  tag: string;
  text: string;
};

export async function listVisibleInteractiveControls(page: Page): Promise<InteractiveControl[]> {
  return page.evaluate((selector) => {
    const nodes = Array.from(document.querySelectorAll(selector)).filter((el) => {
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) {
        return false;
      }
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) return false;
      if (el instanceof HTMLElement && el.hasAttribute("disabled")) return false;
      const tabIndex = el.getAttribute("tabindex");
      if (tabIndex === "-1") return false;
      return true;
    });
    return nodes.map((el) => ({
      tag: el.tagName.toLowerCase(),
      text: (el.textContent ?? "").trim().slice(0, 80),
    }));
  }, INTERACTIVE_SELECTOR);
}

export async function assertVisibleFocusOutline(page: Page): Promise<void> {
  const outline = await page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) {
      return { style: "none", width: "0px" };
    }
    const computed = window.getComputedStyle(el);
    return { style: computed.outlineStyle, width: computed.outlineWidth };
  });
  if (outline.style === "none" || outline.width === "0px") {
    throw new Error(`Focused element lacks visible outline: ${JSON.stringify(outline)}`);
  }
}

export async function findMouseOnlyPointerTargets(page: Page): Promise<string[]> {
  return page.evaluate((selector) => {
    const visible = (el: Element): boolean => {
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) {
        return false;
      }
      const rect = el.getBoundingClientRect();
      return rect.width > 0 || rect.height > 0;
    };

    const focusableControl = (el: Element): boolean => {
      if (!(el instanceof HTMLElement)) return false;
      if (!el.matches(selector)) return false;
      if (el.hasAttribute("disabled")) return false;
      if (el.getAttribute("tabindex") === "-1") return false;
      return true;
    };

    const offenders: string[] = [];
    document.querySelectorAll("*").forEach((el) => {
      if (!visible(el)) return;
      const style = window.getComputedStyle(el);
      if (style.cursor !== "pointer") return;
      let node: Element | null = el;
      while (node) {
        if (focusableControl(node)) return;
        node = node.parentElement;
      }
      offenders.push(`${el.tagName.toLowerCase()}.${el.className}`.slice(0, 120));
    });
    return offenders;
  }, INTERACTIVE_SELECTOR);
}

export async function runningAnimationCount(page: Page): Promise<number> {
  return page.evaluate(() => {
    return document.getAnimations().filter((anim) => anim.playState === "running").length;
  });
}

export async function settleMs(page: Page, ms: number): Promise<void> {
  await page.waitForTimeout(ms);
}
