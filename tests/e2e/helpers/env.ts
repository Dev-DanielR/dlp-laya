import fs from "node:fs";
import path from "node:path";

/** Load docker/.env (shell-quoted values) plus process env for E2E. */
export function loadLabEnv(): void {
  const root = path.resolve(__dirname, "../../..");
  const envPath = process.env.E2E_ENV_FILE || path.join(root, "docker", ".env");
  if (!fs.existsSync(envPath)) {
    return;
  }
  const text = fs.readFileSync(envPath, "utf8");
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq < 1) continue;
    const key = line.slice(0, eq).trim();
    let val = line.slice(eq + 1).trim();
    if (
      (val.startsWith("'") && val.endsWith("'")) ||
      (val.startsWith('"') && val.endsWith('"'))
    ) {
      val = val.slice(1, -1);
    }
    if (process.env[key] === undefined) {
      process.env[key] = val;
    }
  }
}

export type LabUser = {
  email: string;
  password: string;
  role: "alta" | "media" | "baja";
};

export function labUsers(): Record<"alta" | "media" | "baja", LabUser> {
  loadLabEnv();
  const need = (key: string): string => {
    const v = process.env[key];
    if (!v) {
      throw new Error(
        `Missing ${key}. Set it in docker/.env or the environment before running Playwright.`
      );
    }
    return v;
  };
  return {
    alta: {
      role: "alta",
      email: need("USER_ALTA_EMAIL"),
      password: need("USER_ALTA_PASS"),
    },
    media: {
      role: "media",
      email: need("USER_MEDIA_EMAIL"),
      password: need("USER_MEDIA_PASS"),
    },
    baja: {
      role: "baja",
      email: need("USER_BAJA_EMAIL"),
      password: need("USER_BAJA_PASS"),
    },
  };
}
