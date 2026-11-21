/**
 * Caso de uso 04 — Completo vs. sanitizado vs. denegado
 *
 * Same PII file (casos/caso04_proyecto_mixto.pdf) as:
 *   ana.alta  → completo  (200, toast completo)
 *   bruno.media → sanitizado (200, toast sanitizado)
 *   carla.baja → denegado (403 ACL miss; no rule on caso04)
 *
 * Auth: real NetBird OIDC in Chromium (replaces Kali intruder demo for now).
 */
import { expect, test, type APIResponse, type Page } from "@playwright/test";
import { labUsers } from "./helpers/env";
import { signInWithNetBird, signOut } from "./helpers/auth";

const FILE = "casos/caso04_proyecto_mixto.pdf";
const FILE_URL = `/files/${FILE}`;

async function downloadWithHtmx(page: Page): Promise<APIResponse> {
  return page.request.get(FILE_URL, {
    headers: { "HX-Request": "true" },
  });
}

function toastMessage(resp: APIResponse): string {
  const raw = resp.headers()["hx-trigger"];
  if (!raw) return "";
  try {
    const parsed = JSON.parse(raw) as { toast?: { message?: string; type?: string } };
    return parsed.toast?.message || "";
  } catch {
    return raw;
  }
}

test.describe.configure({ mode: "serial" });

test.describe("UC04 completo / sanitizado / denegado", () => {
  const users = labUsers();

  test("alta → completo", async ({ page }) => {
    await signInWithNetBird(page, users.alta);
    await page.goto("/browse?path=casos");
    await expect(page.getByText("caso04_proyecto_mixto.pdf")).toBeVisible();

    const resp = await downloadWithHtmx(page);
    expect(resp.status(), await resp.text()).toBe(200);
    expect(resp.headers()["content-disposition"] || "").toMatch(/attachment/i);
    expect(toastMessage(resp)).toMatch(/Descarga \(completo\).*caso04_proyecto_mixto\.pdf/i);

    // UI path: Descargar → success toast
    const downloadPromise = page.waitForEvent("download", { timeout: 30_000 }).catch(() => null);
    await page
      .locator("tr", { hasText: "caso04_proyecto_mixto.pdf" })
      .getByRole("button", { name: /Descargar/i })
      .click();
    await expect(page.getByText(/Descarga \(completo\)/i)).toBeVisible({ timeout: 30_000 });
    await downloadPromise;

    await signOut(page);
  });

  test("media → sanitizado", async ({ page }) => {
    await signInWithNetBird(page, users.media);
    await page.goto("/browse?path=casos");
    await expect(page.getByText("caso04_proyecto_mixto.pdf")).toBeVisible();

    const resp = await downloadWithHtmx(page);
    expect(resp.status(), await resp.text()).toBe(200);
    expect(resp.headers()["content-disposition"] || "").toMatch(/attachment/i);
    expect(toastMessage(resp)).toMatch(/Descarga \(sanitizado\).*caso04_proyecto_mixto\.pdf/i);

    await page
      .locator("tr", { hasText: "caso04_proyecto_mixto.pdf" })
      .getByRole("button", { name: /Descargar/i })
      .click();
    await expect(page.getByText(/Descarga \(sanitizado\)/i)).toBeVisible({ timeout: 30_000 });

    await signOut(page);
  });

  test("baja / ACL miss → denegado", async ({ page }) => {
    await signInWithNetBird(page, users.baja);
    // carla can browse the tree (ACL only on download) but caso04 has no matching rule.
    await page.goto("/browse?path=casos");
    await expect(page.getByText("caso04_proyecto_mixto.pdf")).toBeVisible();

    const resp = await downloadWithHtmx(page);
    expect(resp.status(), await resp.text()).toBe(403);
    expect(resp.headers()["content-disposition"] || "").not.toMatch(/attachment/i);
    expect(toastMessage(resp)).toMatch(/Denegado/i);

    await page
      .locator("tr", { hasText: "caso04_proyecto_mixto.pdf" })
      .getByRole("button", { name: /Descargar/i })
      .click();
    await expect(page.getByText(/Denegado/i)).toBeVisible({ timeout: 30_000 });

    await signOut(page);
  });
});
