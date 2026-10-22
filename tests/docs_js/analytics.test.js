const assert = require("node:assert/strict");
const { describe, it } = require("node:test");

const analytics = require("../../docs/js/analytics.js");
const fixtures = require("./journey-protocol-v1.fixtures.json");

describe("journey protocol v1 fixtures", () => {
  it("uses the contract constants", () => {
    const { constants } = fixtures;
    assert.equal(analytics.constants.token, constants.token);
    assert.deepEqual(analytics.constants.productionHosts, constants.productionHosts);
    assert.deepEqual(analytics.constants.internalReferrerExact, constants.internalReferrerExact);
    assert.deepEqual(analytics.constants.internalReferrerSuffix, constants.internalReferrerSuffix);
    assert.deepEqual(analytics.constants.referrerRules, constants.referrerRules);
    assert.equal(analytics.constants.handoffKey, constants.handoffKey);
    assert.equal(analytics.constants.attributionCookie.name, constants.attributionCookie.name);
    assert.equal(analytics.constants.attributionCookie.maxAgeSeconds, constants.attributionCookie.maxAgeSeconds);
    assert.equal(analytics.constants.attributionCookie.maxChars, constants.attributionCookie.maxChars);
    assert.deepEqual(analytics.constants.limits, constants.limits);
  });

  for (const testCase of fixtures.parseCampaignTouch) {
    it(`parseCampaignTouch: ${testCase.name}`, () => {
      const actual = analytics.parseCampaignTouch(testCase.url, testCase.referrer, new Date(testCase.now));
      assert.equal(JSON.stringify(actual), JSON.stringify(testCase.expected));
    });
  }

  for (const testCase of fixtures.mergeAttribution) {
    it(`mergeAttribution: ${testCase.name}`, () => {
      const actual = analytics.mergeAttribution(testCase.existing, testCase.entry);
      assert.equal(JSON.stringify(actual), JSON.stringify(testCase.expected));
    });
  }

  for (const testCase of fixtures.attributionCookie.encode) {
    it(`encodeAttributionCookie: ${testCase.name}`, () => {
      assert.equal(analytics.encodeAttributionCookie(testCase.value), testCase.encoded);
    });
  }

  for (const testCase of fixtures.attributionCookie.decode) {
    it(`decodeAttributionCookie: ${testCase.name}`, () => {
      const actual = analytics.decodeAttributionCookie(testCase.encoded);
      assert.equal(JSON.stringify(actual), JSON.stringify(testCase.expected));
    });
  }

  for (const testCase of fixtures.stripHandoff) {
    it(`stripHandoff: ${testCase.url.slice(0, 60)}`, () => {
      assert.equal(analytics.stripHandoff(testCase.url), testCase.expected);
    });
  }

  for (const testCase of fixtures.resolveAnalyticsTarget) {
    it(`resolveAnalyticsTarget: ${testCase.hostname}`, () => {
      assert.deepEqual(analytics.resolveAnalyticsTarget(testCase.hostname), testCase.expected);
    });
  }
});

class CookieJar {
  constructor() {
    this.cookies = new Map();
    this.writes = [];
  }

  get header() {
    return [...this.cookies.values()].map((cookie) => `${cookie.name}=${cookie.value}`).join("; ");
  }

  set(raw) {
    this.writes.push(raw);
    const [pair, ...attributes] = raw.split(";").map((part) => part.trim());
    const separator = pair.indexOf("=");
    const name = pair.slice(0, separator);
    const value = pair.slice(separator + 1);
    const attribute = (key) => {
      const found = attributes.find((part) => part.toLowerCase().startsWith(key.toLowerCase() + "="));
      return found ? found.slice(key.length + 1) : null;
    };
    const domain = attribute("Domain");
    const key = `${name}|${domain || "host"}`;
    if (attribute("Max-Age") === "0") this.cookies.delete(key);
    else this.cookies.set(key, { name, value, domain, attributes });
  }

  names() {
    return [...this.cookies.values()].map((cookie) => cookie.name);
  }
}

class FakeStorage {
  constructor(entries = {}) {
    this.items = new Map(Object.entries(entries));
  }

  get length() {
    return this.items.size;
  }

  key(index) {
    return [...this.items.keys()][index] ?? null;
  }

  getItem(key) {
    return this.items.has(key) ? this.items.get(key) : null;
  }

  setItem(key, value) {
    this.items.set(key, String(value));
  }

  removeItem(key) {
    this.items.delete(key);
  }
}

// Mirrors the posthog-js 1.436.1 behaviour the controller depends on: the opt-out flag lives in
// localStorage, reset() clears it, and the initial $pageview only fires while opted in.
class FakePostHog {
  constructor(win) {
    this.win = win;
    this.calls = [];
    this.events = [];
    this.properties = {};
    this.initialPageviewCaptured = false;
    this.heatmaps = { getAndClearBuffer: () => this.calls.push(["heatmaps.getAndClearBuffer"]) };
  }

  get flagKey() {
    return `__ph_opt_in_out_${this.token}`;
  }

  init(token, config) {
    this.token = token;
    this.config = config;
    this.calls.push(["init", token]);
    this.win.localStorage.setItem(`ph_${token}_posthog`, "{}");
    this.win.document.cookie = `ph_${token}_posthog=%7B%7D; Path=/; Domain=rapidata.ai`;
    config.loaded(this);
    if (!this.has_opted_out_capturing()) this.captureInitialPageview();
  }

  captureInitialPageview() {
    if (this.initialPageviewCaptured) return;
    this.initialPageviewCaptured = true;
    this.capture("$pageview");
  }

  has_opted_out_capturing() {
    return this.win.localStorage.getItem(this.flagKey) === "0";
  }

  register(properties) {
    this.calls.push(["register", properties]);
    Object.assign(this.properties, properties);
  }

  capture(event, properties, options) {
    this.calls.push(["capture", event, options]);
    if (this.has_opted_out_capturing()) return;
    const data = this.config.before_send({ event, properties: { ...this.properties, ...properties } });
    if (data) this.events.push(data);
  }

  setPersonProperties(set, setOnce) {
    this.calls.push(["setPersonProperties", set, setOnce]);
    this.capture("$set", { $set: set || {}, $set_once: setOnce || {} });
  }

  reset(resetDeviceId) {
    this.calls.push(["reset", resetDeviceId]);
    this.win.localStorage.removeItem(this.flagKey);
    this.properties = {};
  }

  stopSessionRecording() {
    this.calls.push(["stopSessionRecording"]);
  }

  opt_out_capturing() {
    this.calls.push(["opt_out_capturing"]);
    this.win.localStorage.setItem(this.flagKey, "0");
  }

  opt_in_capturing(options) {
    this.calls.push(["opt_in_capturing", options]);
    this.win.localStorage.setItem(this.flagKey, "1");
    this.captureInitialPageview();
  }
}

function fakeWindow({ href, referrer = "", localStorage = {}, cookies = [] }) {
  const url = new URL(href);
  const jar = new CookieJar();
  cookies.forEach((cookie) => jar.set(cookie));
  const listeners = [];
  const win = {
    location: { href: url.href, hostname: url.hostname, protocol: url.protocol },
    history: {
      state: null,
      replaced: [],
      replaceState(state, title, next) {
        this.replaced.push(next);
        win.location.href = next;
      },
    },
    localStorage: new FakeStorage(localStorage),
    sessionStorage: new FakeStorage(),
    document: {
      referrer,
      get cookie() {
        return jar.header;
      },
      set cookie(raw) {
        jar.set(raw);
      },
      documentElement: { classList: { add() {} } },
      body: { children: [], appendChild(child) { this.children.push(child); } },
      createElement: (tag) => ({ tag, className: "" }),
      addEventListener(type, listener, capture) {
        listeners.push({ type, listener, capture });
      },
    },
  };
  return { win, jar, listeners };
}

function start(options = {}) {
  const env = fakeWindow({ href: "https://docs.rapidata.ai/quickstart/", ...options });
  const loaded = [];
  env.consent = { analytics: false, config: null };
  const loaders = {
    style: async (asset) => loaded.push(asset.url),
    script: async (asset) => {
      loaded.push(asset.url);
      if (asset.url.includes("cookieconsent")) {
        env.win.CookieConsent = {
          run: (config) => (env.consent.config = config),
          acceptedCategory: (category) => category === "analytics" && env.consent.analytics,
          showPreferences: () => (env.consent.preferencesShown = true),
        };
      } else {
        env.posthog = new FakePostHog(env.win);
        env.win.posthog = env.posthog;
      }
    },
  };
  env.loaded = loaded;
  env.controller = analytics.startJourneyAnalytics(env.win, loaders);
  env.decide = async (analyticsAllowed, callback = "onConsent") => {
    await env.controller.ready;
    env.consent.analytics = analyticsAllowed;
    await env.consent.config[callback]();
  };
  env.click = (type, href, button = 0) => {
    const link = { href };
    const target = { closest: (selector) => (selector === "a[href]" ? link : null) };
    for (const { type: listenerType, listener } of env.listeners) {
      if (listenerType === type) listener({ type, button, target, preventDefault() {} });
    }
  };
  return env;
}

const callNames = (posthog) => posthog.calls.map((call) => call[0]);
const pageviews = (posthog) => posthog.events.filter((event) => event.event === "$pageview");

describe("docs consent controller", () => {
  it("loads nothing but the consent banner before a choice", async () => {
    const env = start({ href: "https://docs.rapidata.ai/?utm_source=pypi", referrer: "https://pypi.org/" });
    await env.controller.ready;
    assert.equal(env.loaded.length, 2);
    assert.ok(env.loaded.every((url) => url.includes("vanilla-cookieconsent@3.1.0")));
    assert.equal(env.win.posthog, undefined);
    assert.deepEqual(env.jar.names(), []);
    assert.equal(env.controller.entry.kind, "campaign");
  });

  it("configures the shared consent cookie", async () => {
    const env = start();
    await env.controller.ready;
    const { config } = env.consent;
    const { consentCookie } = fixtures.constants;
    assert.equal(config.revision, consentCookie.revision);
    assert.deepEqual(config.cookie, { name: consentCookie.name, domain: "rapidata.ai" });
    assert.deepEqual(Object.keys(config.categories), ["necessary", consentCookie.category]);
    assert.deepEqual(config.categories.necessary, { enabled: true, readOnly: true });
    assert.equal(config.language.translations.en.consentModal.title, "Analytics preferences");
    assert.equal(config.language.translations.en.consentModal.acceptAllBtn, "Allow analytics");
    assert.equal(config.language.translations.en.consentModal.acceptNecessaryBtn, "Reject analytics");
    assert.match(config.language.translations.en.consentModal.footer, /https:\/\/rapidata\.ai\/privacy/);
    assert.equal(config.root.className, "ph-no-capture");
    assert.ok(env.win.document.body.children.includes(config.root));
  });

  it("uses the production cookie domain on docs.rapidata.ai", async () => {
    const env = start({ href: "https://docs.rapidata.ai/" });
    await env.decide(true);
    const { consentCookie, attributionCookie } = fixtures.constants;
    assert.deepEqual(env.consent.config.cookie, { name: consentCookie.name, domain: consentCookie.domain.rapidata });
    const cookie = env.jar.cookies.get(`${attributionCookie.name}|${attributionCookie.domain.rapidata}`);
    for (const attribute of ["Path=/", `Max-Age=${attributionCookie.maxAgeSeconds}`, `SameSite=${attributionCookie.sameSite}`, "Secure"]) {
      assert.ok(cookie.attributes.includes(attribute), attribute);
    }
  });

  for (const [href, domain] of [
    ["https://docs.rapidata.ai/", "rapidata.ai"],
    ["https://www.benchmark.ai/", "benchmark.ai"],
  ]) {
    it(`shares the consent and attribution cookies on ${domain}`, async () => {
      const env = start({ href });
      await env.decide(true);
      assert.deepEqual(env.consent.config.cookie, { name: "cc_cookie", domain });
      assert.ok(env.jar.cookies.has(`rd_attribution_v1|${domain}`));
      assert.equal(env.posthog.events[0].properties.environment, "production");
    });
  }

  it("injects the consent and PostHog assets into <body> with SRI", () => {
    const { win } = fakeWindow({ href: "https://docs.rapidata.ai/" });
    analytics.startJourneyAnalytics(win);
    const assets = win.document.body.children.filter((child) => child.integrity);
    assert.deepEqual(
      assets.map((child) => [child.tag, child.crossOrigin]),
      [
        ["link", "anonymous"],
        ["script", "anonymous"],
      ]
    );
    assert.match(assets[0].href, /vanilla-cookieconsent@3\.1\.0\/dist\/cookieconsent\.css$/);
    assert.match(assets[1].src, /vanilla-cookieconsent@3\.1\.0\/dist\/cookieconsent\.umd\.js$/);
  });

  for (const href of [
    "https://rapidataai.github.io/rapidata-python-sdk/",
    "https://docs-preview-rapidata.vercel.app/",
    "https://docs.rabbitdata.ch/",
    "https://docs.rapidata.dev/",
    "http://localhost:8000/",
    "http://127.0.0.1:8000/",
  ]) {
    it(`does nothing on non-production host ${new URL(href).hostname}`, () => {
      const env = start({ href });
      assert.equal(env.controller, null);
      assert.deepEqual(env.loaded, []);
      assert.deepEqual(env.listeners, []);
    });
  }

  it("strips a stray handoff fragment before parsing", () => {
    const env = start({ href: "https://docs.rapidata.ai/quickstart/#rd_journey=abc" });
    assert.deepEqual(env.win.history.replaced, ["https://docs.rapidata.ai/quickstart/"]);
  });

  it("initialises PostHog with super properties before the first pageview on grant", async () => {
    const env = start({ href: "https://docs.rapidata.ai/quickstart/?utm_source=pypi", referrer: "https://pypi.org/" });
    await env.decide(true);
    const { posthog } = env;
    assert.equal(posthog.token, fixtures.constants.token);
    assert.equal(posthog.config.api_host, "https://eu.i.posthog.com");
    assert.equal(posthog.config.ui_host, "https://eu.posthog.com");
    assert.equal(posthog.config.capture_pageview, "history_change");
    assert.equal(posthog.config.cross_subdomain_cookie, true);
    assert.equal(posthog.config.cookieWinsOnConflict, true);
    assert.equal(posthog.config.opt_out_persistence_by_default, true);
    assert.equal(posthog.config.persistence, "localStorage+cookie");
    assert.equal(posthog.config.advanced_disable_feature_flags, true);
    assert.equal("advanced_disable_flags" in posthog.config, false);
    const [pageview] = pageviews(posthog);
    assert.equal(pageview.properties.surface, "docs");
    assert.equal(pageview.properties.environment, "production");
    assert.equal(pageview.properties.tracking_version, 1);
    assert.equal(pageview.properties.event_source, "browser");
    assert.equal(pageview.properties.first_source, "pypi");
    assert.equal(pageview.properties.last_external_source, "pypi");
    const cookie = env.jar.cookies.get("rd_attribution_v1|rapidata.ai");
    assert.ok(cookie.attributes.includes("Max-Age=7776000"));
    assert.ok(cookie.attributes.includes("SameSite=Lax"));
    assert.equal(analytics.decodeAttributionCookie(cookie.value).first.source, "pypi");
  });

  it("stamps surface and environment on every event, including after reset()", async () => {
    const env = start({ href: "https://docs.rapidata.ai/quickstart/" });
    await env.decide(true);
    await env.decide(false, "onChange");
    await env.decide(true, "onChange");
    env.posthog.properties = {};
    env.posthog.capture("$web_vitals");
    env.click("click", "https://app.rapidata.ai/");
    const names = new Set(env.posthog.events.map(({ event }) => event));
    for (const name of ["$pageview", "$set", "$web_vitals", "outbound_link_clicked"]) assert.ok(names.has(name), name);
    for (const { event, properties } of env.posthog.events) {
      assert.equal(properties.environment, "production", event);
      assert.equal(properties.surface, "docs", event);
      assert.equal(properties.tracking_version, 1, event);
      assert.equal(properties.event_source, "browser", event);
    }
  });

  it("sets first touch once and last external touch on the person", async () => {
    const env = start({ href: "https://docs.rapidata.ai/", referrer: "https://github.com/RapidataAI" });
    await env.decide(true);
    const call = env.posthog.calls.find(([name]) => name === "setPersonProperties");
    assert.equal(call[1].last_external_source, "github");
    assert.equal(call[2].first_source, "github");
    assert.equal(call[2].first_landing_path, "/");
  });

  it("revokes in the contract order and clears journey storage", async () => {
    const env = start();
    await env.decide(true);
    env.win.localStorage.setItem("ph_other_key", "1");
    const before = env.posthog.calls.length;
    await env.decide(false, "onChange");
    assert.deepEqual(env.posthog.calls.slice(before), [
      ["opt_out_capturing"],
      ["stopSessionRecording"],
      ["reset", true],
      ["opt_out_capturing"],
    ]);
    assert.equal(env.posthog.has_opted_out_capturing(), true);
    assert.deepEqual(env.jar.names(), []);
    assert.deepEqual([...env.win.localStorage.items.keys()], [env.posthog.flagKey]);
  });

  it("regrants in the same page with opt_in_capturing and a fresh pageview", async () => {
    const env = start();
    await env.decide(true);
    await env.decide(false, "onChange");
    await env.decide(true, "onChange");
    const optIn = env.posthog.calls.filter(([name]) => name === "opt_in_capturing");
    assert.deepEqual(optIn.at(-1)[1], { captureEventName: false });
    const names = callNames(env.posthog);
    assert.equal(names.lastIndexOf("heatmaps.getAndClearBuffer"), names.lastIndexOf("opt_in_capturing") - 1);
    assert.equal(pageviews(env.posthog).length, 2);
    assert.equal(pageviews(env.posthog)[1].properties.surface, "docs");
    assert.ok(env.jar.cookies.has("rd_attribution_v1|rapidata.ai"));
  });

  it("does not add a pageview when consent is confirmed again without a revoke", async () => {
    const env = start();
    await env.decide(true);
    await env.decide(true, "onChange");
    assert.equal(pageviews(env.posthog).length, 1);
    assert.equal(callNames(env.posthog).includes("opt_in_capturing"), false);
  });

  it("regrants on a later page load despite the persisted opt-out flag", async () => {
    const first = start();
    await first.decide(true);
    await first.decide(false, "onChange");
    const flag = Object.fromEntries(first.win.localStorage.items);

    const later = start({ localStorage: flag });
    await later.decide(true);
    assert.deepEqual(later.posthog.calls.find(([name]) => name === "opt_in_capturing")[1], {
      captureEventName: false,
    });
    assert.equal(pageviews(later.posthog).length, 1);
    assert.equal(pageviews(later.posthog)[0].properties.surface, "docs");
  });

  it("does not initialise PostHog when consent is revoked while the script loads", async () => {
    const env = start();
    await env.controller.ready;
    env.consent.analytics = true;
    const granting = env.consent.config.onConsent();
    env.consent.analytics = false;
    await env.consent.config.onChange();
    await granting;
    assert.equal(env.posthog.calls.length, 0);
    await env.decide(true, "onChange");
    assert.equal(callNames(env.posthog)[0], "init");
  });

  it("captures outbound clicks without query or hash, only after consent", async () => {
    const env = start();
    env.click("click", "https://app.rapidata.ai/settings/tokens?client=1#top");
    await env.decide(true);
    env.click("click", "https://app.rapidata.ai/settings/tokens?client=1#top");
    env.click("click", "https://docs.rapidata.ai/audiences/");
    env.click("click", "https://github.com/RapidataAI");
    env.click("auxclick", "https://huggingface.co/Rapidata", 1);
    env.click("auxclick", "https://huggingface.co/Rapidata", 2);
    const outbound = env.posthog.events.filter((event) => event.event === "outbound_link_clicked");
    assert.deepEqual(
      outbound.map(({ properties }) => [properties.destination_host, properties.destination_path]),
      [
        ["app.rapidata.ai", "/settings/tokens"],
        ["huggingface.co", "/Rapidata"],
      ]
    );
    assert.equal(outbound[0].properties.surface, "docs");
    const options = env.posthog.calls.find(([name, event]) => name === "capture" && event === "outbound_link_clicked")[2];
    assert.deepEqual(options, { send_instantly: true, transport: "sendBeacon" });
  });

  it("opens the preferences modal from any [data-rd-consent] element", async () => {
    const env = start();
    await env.controller.ready;
    const target = { closest: (selector) => (selector === "[data-rd-consent]" ? {} : null) };
    for (const { type, listener, capture } of env.listeners) {
      if (type === "click" && !capture) listener({ type, target, preventDefault() {} });
    }
    assert.equal(env.consent.preferencesShown, true);
  });

  it("clears leftovers when analytics is rejected", async () => {
    const env = start({ cookies: ["ph_x_posthog=1; Path=/; Domain=rapidata.ai", "rd_attribution_v1=abc; Path=/; Domain=rapidata.ai"] });
    await env.decide(false);
    assert.equal(env.win.posthog, undefined);
    assert.deepEqual(env.jar.names(), []);
  });
});
