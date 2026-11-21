import { expect, type Page } from "@playwright/test";
import type { LabUser } from "./env";

/** NetBird embedded Dex local login (prompt=login from /auth/login). */
export async function signInWithNetBird(page: Page, user: LabUser): Promise<void> {
  await page.goto("/");
  await expect(page.getByRole("link", { name: /Sign in with NetBird/i })).toBeVisible();
  await page.getByRole("link", { name: /Sign in with NetBird/i }).click();

  // Dex/NetBird login form on knowsyn.dev
  await page.waitForURL(/knowsyn\.dev\/oauth2\/auth/, { timeout: 60_000 });
  await expect(page.locator("#login")).toBeVisible({ timeout: 30_000 });
  await page.locator("#login").fill(user.email);
  await page.locator("#password").fill(user.password);
  await page.locator("#submit-login").click();

  // Callback → browse
  await page.waitForURL(/localhost:8443\/(browse)?/, { timeout: 60_000 });
  await expect(page.getByRole("link", { name: /^Salir$/i })).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText(user.email, { exact: false })).toBeVisible();
}

/** Clear local session + IdP SSO so the next Sign-in must re-authenticate. */
export async function signOut(page: Page): Promise<void> {
  const salir = page.getByRole("link", { name: /^Salir$/i });
  if (await salir.isVisible().catch(() => false)) {
    await salir.click();
  } else {
    await page.goto("/auth/logout");
  }

  // Dex/NetBird often lands on an intermediate "Logged Out" page.
  const back = page.getByRole("link", { name: /Back to Application/i });
  try {
    await back.waitFor({ state: "visible", timeout: 15_000 });
    await back.click();
  } catch {
    // Already redirected, or logout skipped the interstitial.
  }

  await page.waitForURL(/localhost:8443\/?$/, { timeout: 60_000 });
  // Ensure we are on the landing shell (not a stale browse session).
  if (!(await page.getByRole("link", { name: /Sign in with NetBird/i }).isVisible().catch(() => false))) {
    await page.goto("/");
  }
  await expect(page.getByRole("link", { name: /Sign in with NetBird/i })).toBeVisible({
    timeout: 30_000,
  });
}
