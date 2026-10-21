const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");
const { test } = require("node:test");
const { chromium } = require("playwright");

const SITE = path.resolve(process.env.DOCS_SITE_DIR || "site");
const ORIGIN = "https://docs.rapidata.ai";
// posthog-js drops HeadlessChrome (UA or userAgentData brand) as a bot, so "zero requests" would pass vacuously.
const USER_AGENT =
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36";

function localFile(url) {
  const file = path.join(SITE, decodeURIComponent(new URL(url).pathname));
  return file.endsWith(path.sep) ? path.join(file, "index.html") : file;
}

function decodeEvents(request) {
  const body = request.postDataBuffer();
  if (!body || body.length === 0) return [];
  const text = body[0] === 0x1f && body[1] === 0x8b ? zlib.gunzipSync(body).toString() : body.toString();
  const parsed = JSON.parse(text);
  return Array.isArray(parsed) ? parsed : parsed.batch || [parsed];
}

async function waitFor(predicate, timeout, message) {
  const deadline = Date.now() + timeout;
  while (!predicate()) {
    if (Date.now() > deadline) throw new Error(message);
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
}

async function waitForQuiet(requests, quietMs, timeout) {
  const deadline = Date.now() + timeout;
  let count = requests.length;
  let since = Date.now();
  while (Date.now() - since < quietMs) {
    if (Date.now() > deadline) throw new Error("PostHog traffic never went quiet");
    await new Promise((resolve) => setTimeout(resolve, 250));
    if (requests.length !== count) [count, since] = [requests.length, Date.now()];
  }
}

test("nothing reaches PostHog before consent or after Reject", { timeout: 180_000 }, async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ userAgent: USER_AGENT, viewport: { width: 1280, height: 800 } });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    Object.defineProperty(navigator, "userAgentData", { get: () => undefined });
  });
  const requests = [];
  const events = [];
  await context.route("**/*", async (route) => {
    const request = route.request();
    const { hostname } = new URL(request.url());
    if (hostname.endsWith("posthog.com")) requests.push(request.url());
    if (hostname === "docs.rapidata.ai") {
      const file = localFile(request.url());
      return fs.existsSync(file) ? route.fulfill({ path: file }) : route.fulfill({ status: 404, body: "" });
    }
    if (hostname === "eu.i.posthog.com") {
      events.push(...decodeEvents(request));
      return route.fulfill({ status: 200, contentType: "application/json", body: '{"status":1}' });
    }
    if (hostname === "cdn.jsdelivr.net" || hostname === "eu-assets.i.posthog.com") return route.continue();
    return route.abort();
  });

  try {
    const page = await context.newPage();
    const banner = page.locator("#cc-main .cm");
    const navLink = (slug) => page.locator(`a.md-nav__link[href$="${slug}/"]`).first();
    await page.goto(`${ORIGIN}/quickstart/?utm_source=pypi&utm_medium=referral&utm_campaign=python_sdk`, {
      referer: "https://pypi.org/project/rapidata/",
    });
    await banner.waitFor({ state: "visible" });

    await page.evaluate(() => (window.journeyTestMarker = true));
    await navLink("authentication").click();
    await page.waitForFunction(() => document.title.startsWith("Authentication"));
    await page.waitForTimeout(1_000);
    assert.equal(await page.evaluate(() => window.journeyTestMarker), true, "expected an instant navigation");
    assert.equal(await banner.evaluate((element) => getComputedStyle(element).position), "fixed");
    assert.deepEqual(requests, [], "PostHog was contacted before consent");

    await page.getByRole("button", { name: "Allow analytics" }).click();
    await waitFor(() => events.some((event) => event.event === "$pageview"), 20_000, "no $pageview after consent");
    const cookies = Object.fromEntries((await context.cookies()).map((cookie) => [cookie.name, cookie]));
    assert.equal(cookies.cc_cookie.domain, ".rapidata.ai");
    assert.equal(cookies.rd_attribution_v1.domain, ".rapidata.ai");
    assert.equal(cookies.rd_attribution_v1.secure, true);

    await navLink("audiences").click();
    await waitFor(
      () => events.some((event) => event.event === "$pageview" && event.properties.$pathname === "/audiences/"),
      20_000,
      "no $pageview after instant navigation"
    );
    await page.locator("button[data-rd-consent]").click();
    await page.locator("#cc-main .pm").waitFor({ state: "visible" });
    await waitForQuiet(requests, 6_000, 60_000);

    const before = requests.length;
    await page.locator("#cc-main .pm").getByRole("button", { name: "Reject analytics" }).click();
    await page.waitForTimeout(6_000);
    await navLink("signals").click();
    await page.waitForURL("**/signals/");
    await page.mouse.click(400, 400);
    await page.waitForTimeout(6_000);
    await page.reload();
    await page.waitForTimeout(4_000);
    assert.deepEqual(requests.slice(before), [], "PostHog was contacted after Reject");

    const names = (await context.cookies()).map((cookie) => cookie.name);
    assert.deepEqual(names.filter((name) => name.startsWith("ph_") || name === "rd_attribution_v1"), []);
    assert.deepEqual(await page.evaluate(() => Object.keys(localStorage).filter((key) => key.startsWith("ph_"))), []);

    assert.ok(events.length > 0);
    for (const { event, properties } of events) {
      assert.equal(properties.environment, "production", event);
      assert.equal(properties.surface, "docs", event);
    }
  } finally {
    await browser.close();
  }
});
