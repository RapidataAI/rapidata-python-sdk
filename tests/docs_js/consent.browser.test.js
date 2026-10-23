const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");
const { test } = require("node:test");
const { chromium } = require("playwright");
const analytics = require("../../docs/js/analytics.js");

const SITE = path.resolve(process.env.DOCS_SITE_DIR || "site");
const ORIGIN = "https://docs.rapidata.ai";
const HOST = new URL(ORIGIN).hostname;
const COOKIE_DOMAIN = ".rapidata.ai";
// Heatmaps flush every 5 s into a batch queue sent every 3 s, so a shorter quiet window can still hold events.
const DRAIN_MS = 9_000;
// Analytics only runs on production hosts, so pages are served locally, and the ingest proxy and PostHog are
// unresolvable: unload flushes use sendBeacon, which bypasses Playwright routes.
const HOST_RULES =
  "--host-resolver-rules=MAP docs.rapidata.ai 127.0.0.1, MAP app.rapidata.ai 127.0.0.1, MAP rapidata.ai ~NOTFOUND, " +
  "MAP *.posthog.com ~NOTFOUND, MAP posthog.com ~NOTFOUND";
const INGEST_HOSTS = ["rapidata.ai", "app.rapidata.ai"];
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

async function openDocs() {
  const browser = await chromium.launch({ args: [HOST_RULES] });
  const probe = await browser.newPage();
  for (const url of ["https://eu.i.posthog.com/", "https://rapidata.ai/ingest/"]) {
    const blocked = await probe.goto(url).then(() => "", (error) => error.message);
    if (!/ERR_NAME_NOT_RESOLVED/.test(blocked)) {
      await browser.close();
      throw new Error(`${url} must be unreachable from the test browser`);
    }
  }
  await probe.close();
  const context = await browser.newContext({ userAgent: USER_AGENT, viewport: { width: 1280, height: 800 } });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    Object.defineProperty(navigator, "userAgentData", { get: () => undefined });
    const sendBeacon = navigator.sendBeacon.bind(navigator);
    navigator.sendBeacon = (url, data) => {
      if (String(url).includes("/ingest/") || String(url).includes("posthog.com")) {
        localStorage.setItem("journeyTestBeacons", String(Number(localStorage.getItem("journeyTestBeacons") || 0) + 1));
      }
      return sendBeacon(url, data);
    };
  });
  const requests = [];
  const direct = [];
  const events = [];
  await context.route("**/*", async (route) => {
    const request = route.request();
    const { hostname, pathname, search } = new URL(request.url());
    if (hostname.endsWith("posthog.com")) {
      direct.push(request.url());
      return route.abort();
    }
    if (INGEST_HOSTS.includes(hostname) && pathname.startsWith("/ingest/")) {
      requests.push(request.url());
      const upstream = pathname.slice("/ingest".length);
      // Like the Website rewrite, assets come from eu-assets, fetched from Node so the browser holds no connection.
      if (/^\/(static|array)\//.test(upstream)) {
        return route.fulfill({ response: await route.fetch({ url: `https://eu-assets.i.posthog.com${upstream}${search}` }) });
      }
      events.push(...decodeEvents(request));
      return route.fulfill({ status: 200, contentType: "application/json", body: '{"status":1}' });
    }
    if (hostname === HOST) {
      const file = localFile(request.url());
      return fs.existsSync(file) ? route.fulfill({ path: file }) : route.fulfill({ status: 404, body: "" });
    }
    if (hostname === "cdn.jsdelivr.net") return route.continue();
    return route.abort();
  });
  const close = async () => {
    await context.unrouteAll({ behavior: "ignoreErrors" });
    await browser.close();
  };
  return { context, close, requests, direct, events };
}

const beaconCount = (page) => page.evaluate(() => Number(localStorage.getItem("journeyTestBeacons") || 0));
const pageviewCount = (events, from) => events.slice(from).filter((event) => event.event === "$pageview").length;
const consentChanges = (events, from) =>
  events
    .slice(from)
    .filter((event) => event.event === "consent_granted")
    .map((event) => event.properties.change);

test("nothing reaches PostHog before consent or after Reject", { timeout: 180_000 }, async () => {
  const { context, close, requests, direct, events } = await openDocs();
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
    assert.equal(cookies.cc_cookie.domain, COOKIE_DOMAIN);
    assert.equal(cookies.rd_attribution_v1.domain, COOKIE_DOMAIN);
    assert.equal(cookies.rd_attribution_v1.secure, true);
    await waitFor(() => events.some((event) => event.event === "$set"), 20_000, "no $set after consent");
    const person = events.find((event) => event.event === "$set");
    assert.equal(person.properties.$set_once.first_source, "pypi");
    assert.equal(person.properties.$set.last_external_source, "pypi");

    const outbound = await page.evaluate(() => {
      const captured = [];
      window.posthog.on("eventCaptured", (event) => captured.push(event));
      const link = Object.assign(document.createElement("a"), { href: "https://app.rapidata.ai/settings/tokens?client=1#top" });
      link.addEventListener("click", (event) => event.preventDefault());
      document.body.appendChild(link).click();
      link.remove();
      return captured.filter((event) => event.event === "outbound_link_clicked").map((event) => event.properties);
    });
    assert.deepEqual(
      outbound.map((properties) => [properties.destination_host, properties.destination_path, properties.surface]),
      [["app.rapidata.ai", "/settings/tokens", "docs"]]
    );

    await navLink("audiences").click();
    await waitFor(
      () => events.some((event) => event.event === "$pageview" && event.properties.$pathname === "/audiences/"),
      20_000,
      "no $pageview after instant navigation"
    );
    await page.locator("button[data-rd-consent]").click();
    await page.locator("#cc-main .pm").waitFor({ state: "visible" });
    await waitForQuiet(requests, DRAIN_MS, 90_000);

    const reject = async () => {
      await page.locator("button[data-rd-consent]").click();
      await page.locator("#cc-main .pm").getByRole("button", { name: "Reject analytics" }).click();
    };
    const assertNothingStored = async () => {
      const names = (await context.cookies()).map((cookie) => cookie.name);
      assert.deepEqual(names.filter((name) => name.startsWith("ph_") || name === "rd_attribution_v1"), []);
      assert.deepEqual(await page.evaluate(() => Object.keys(localStorage).filter((key) => key.startsWith("ph_"))), []);
    };

    let before = requests.length;
    let eventsBefore = events.length;
    let beaconsBefore = await beaconCount(page);
    await page.locator("#cc-main .pm").getByRole("button", { name: "Reject analytics" }).click();
    await page.waitForTimeout(6_000);
    await navLink("signals").click();
    await page.waitForURL("**/signals/");
    await page.mouse.click(400, 400);
    await page.waitForTimeout(6_000);
    const leaked = () => events.slice(eventsBefore).map((event) => `${event.event} ${event.properties.$pathname}`);
    assert.deepEqual(requests.slice(before), [], `PostHog was contacted after Reject: ${leaked()}`);
    assert.equal(await beaconCount(page), beaconsBefore, "a beacon went to PostHog after Reject");
    await assertNothingStored();

    // Heatmaps flush every 5 s and drop clicks while opted out, so only a click just before re-granting can leak.
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.mouse.click(7, 400);
    await page.locator("button[data-rd-consent]").click();
    await page.locator("#cc-main .pm").getByRole("button", { name: "Allow analytics" }).click();
    const regranted = events.length;
    await page.mouse.click(9, 400);
    await waitFor(
      () => events.slice(regranted).some((event) => event.event === "$$heatmap"),
      20_000,
      "no $$heatmap after re-grant"
    );
    const heatmapX = events
      .slice(regranted)
      .filter((event) => event.event === "$$heatmap")
      .flatMap((event) => Object.values(event.properties.$heatmap_data).flat())
      .map((point) => point.x);
    assert.ok(heatmapX.includes(9), `expected the post-grant click in ${heatmapX}`);
    assert.ok(!heatmapX.includes(7), `a click made while rejected leaked into $$heatmap: ${heatmapX}`);

    await waitForQuiet(requests, DRAIN_MS, 90_000);
    before = requests.length;
    eventsBefore = events.length;
    beaconsBefore = await beaconCount(page);
    await reject();
    await page.waitForTimeout(6_000);
    await page.reload();
    await page.waitForTimeout(4_000);
    assert.deepEqual(requests.slice(before), [], `PostHog was contacted after the second Reject: ${leaked()}`);
    assert.equal(await beaconCount(page), beaconsBefore, "a beacon went to PostHog after the second Reject");
    await assertNothingStored();

    assert.ok(events.length > 0);
    for (const { event, properties } of events) {
      assert.equal(properties.environment, "production", event);
      assert.equal(properties.surface, "docs", event);
    }
    assert.deepEqual(direct, [], "the browser called PostHog directly instead of rapidata.ai/ingest");
    assert.ok(requests.every((url) => url.startsWith("https://rapidata.ai/ingest/")), requests.join("\n"));
    for (const path of [/\/ingest\/array\//, /\/ingest\/static\/1\.436\.1\//, /\/ingest\/(i\/v0\/)?e\//]) {
      assert.ok(requests.some((url) => path.test(url)), `expected a request matching ${path}`);
    }
  } finally {
    await close();
  }
});

test("one $pageview and one consent_granted per Allow click, none for a stored choice", { timeout: 180_000 }, async () => {
  const { context, close, requests, direct, events } = await openDocs();
  try {
    const page = await context.newPage();
    const preferences = page.locator("#cc-main .pm");
    const choose = async (name) => {
      await page.locator("button[data-rd-consent]").click();
      await preferences.getByRole("button", { name }).click();
    };
    await page.goto(`${ORIGIN}/quickstart/`);
    const clickedAt = Date.now();
    await page.getByRole("button", { name: "Allow analytics" }).click();
    await waitFor(() => pageviewCount(events, 0) > 0, 20_000, "no $pageview after consent");
    await waitFor(() => consentChanges(events, 0).length > 0, 20_000, "no consent_granted after Allow");
    await waitForQuiet(requests, 6_000, 60_000);
    assert.equal(pageviewCount(events, 0), 1, "first grant");
    assert.deepEqual(consentChanges(events, 0), ["first"]);
    const granted = events.find((event) => event.event === "consent_granted");
    assert.equal(granted.properties.policy_version, analytics.constants.consentCookie.policyVersion);
    assert.equal(granted.properties.surface, "docs");
    assert.equal(granted.properties.environment, "production");
    assert.equal(granted.properties.distinct_id, await page.evaluate(() => window.posthog.get_distinct_id()));
    assert.equal(granted.$set_once.first_consent_surface, "docs");
    assert.match(granted.$set_once.first_consent_at, /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/);
    assert.ok(Date.parse(granted.$set_once.first_consent_at) >= clickedAt - 1_000);

    const reloaded = events.length;
    await page.reload();
    await waitFor(() => pageviewCount(events, reloaded) > 0, 20_000, "no $pageview after reload");
    await waitForQuiet(requests, 6_000, 60_000);
    assert.equal(pageviewCount(events, reloaded), 1, "load with consent already given");
    assert.deepEqual(consentChanges(events, reloaded), [], "a stored choice sent consent_granted");

    await choose("Reject analytics");
    await page.waitForTimeout(1_000);
    await choose("Allow analytics");
    await waitFor(() => pageviewCount(events, reloaded) > 1, 20_000, "no $pageview after re-grant");
    await waitForQuiet(requests, 6_000, 60_000);
    assert.equal(pageviewCount(events, reloaded), 2, "Allow, Reject, Allow on one page");
    assert.deepEqual(consentChanges(events, reloaded), ["regrant"]);

    await choose("Reject analytics");
    await page.waitForTimeout(1_000);
    const later = events.length;
    await page.reload();
    await page.waitForFunction(() => window.CookieConsent);
    await choose("Allow analytics");
    await waitFor(() => pageviewCount(events, later) > 0, 20_000, "no $pageview when re-allowing on a later load");
    await waitForQuiet(requests, 6_000, 60_000);
    assert.equal(pageviewCount(events, later), 1, "re-allow on a later page load");
    assert.deepEqual(consentChanges(events, later), ["regrant"]);
    assert.deepEqual(direct, [], "the browser called PostHog directly");
  } finally {
    await close();
  }
});

test("an identity set on a sibling subdomain wins over docs' stale anonymous id", { timeout: 120_000 }, async () => {
  const { context, close, direct, events } = await openDocs();
  const { posthog } = analytics.constants.assets;
  const app = `https://app${COOKIE_DOMAIN}`;
  await context.route(`${app}/identify.html*`, (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<!doctype html><script src="${posthog.url}" integrity="${posthog.integrity}" crossorigin="anonymous"></script>
<script>
  posthog.init("${analytics.constants.token}", {
    api_host: "/ingest", ui_host: "https://eu.posthog.com", defaults: "2026-05-30", persistence: "localStorage+cookie",
    cross_subdomain_cookie: true, cookieWinsOnConflict: true, advanced_disable_feature_flags: true,
    autocapture: false, capture_pageview: false,
    loaded: (ph) => { window.before = ph.get_distinct_id(); ph.identify(new URLSearchParams(location.search).get("id")); },
  });
</script>`,
    })
  );
  try {
    const page = await context.newPage();
    await page.goto(`${ORIGIN}/quickstart/`);
    await page.getByRole("button", { name: "Allow analytics" }).click();
    await waitFor(() => pageviewCount(events, 0) > 0, 20_000, "no $pageview after consent");
    const anonymous = await page.evaluate(() => window.posthog.get_distinct_id());

    const customer = `journey-e2e-${Date.now()}`;
    await page.goto(`${app}/identify.html?id=${customer}`);
    await page.waitForFunction(() => window.before !== undefined);
    assert.equal(await page.evaluate(() => window.before), anonymous, "app did not read the shared cookie");

    const returned = events.length;
    await page.goto(`${ORIGIN}/audiences/`);
    await waitFor(() => pageviewCount(events, returned) > 0, 20_000, "no $pageview back on docs");
    assert.equal(await page.evaluate(() => window.posthog.get_distinct_id()), customer);
    assert.ok((await beaconCount(page)) > 0, "the unload flush to app should have gone out as a sendBeacon");
    const pageview = events.slice(returned).find((event) => event.event === "$pageview");
    assert.equal(pageview.properties.distinct_id, customer);
    assert.deepEqual(direct, [], "the browser called PostHog directly");
  } finally {
    await close();
  }
});
