import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";

const baseUrl = process.env.CAOS_URL || "http://127.0.0.1:8000";
const routes = ["/cases/", "/sources/", "/run-console/", "/deep-dive/", "/rv-screener/", "/command-center/", "/model-builder/", "/report-studio/", "/admin-studio/"];
const browser = await chromium.launch({ headless: true });
const violations = [];

try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  for (const route of routes) {
    await page.goto(`${baseUrl}${route}`, { waitUntil: "networkidle" });
    const result = await new AxeBuilder({ page }).analyze();
    for (const violation of result.violations) violations.push({ route, id: violation.id, impact: violation.impact, nodes: violation.nodes.map((node) => ({ target: node.target, html: node.html, summary: node.failureSummary })) });
  }
  await context.close();
} finally {
  await browser.close();
}

if (violations.length) {
  console.error(JSON.stringify({ violations }, null, 2));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ routes: routes.length, violations: 0 }));
}
