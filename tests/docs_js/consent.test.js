const assert = require("node:assert/strict");
const { afterEach, beforeEach, describe, it, mock } = require("node:test");

const analytics = require("../../docs/js/analytics.js");

const ISO_UTC = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/;
const REVOKE_SEQUENCE = [["opt_out_capturing"], ["stopSessionRecording"], ["reset", true], ["opt_out_capturing"]];

const settle = async () => {
  for (let round = 0; round < 3; round++) await new Promise((resolve) => setImmediate(resolve));
};

function fakeStorage() {
  const items = new Map();
  return {
    get length() {
      return items.size;
    },
    key: (index) => [...items.keys()][index] ?? null,
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => items.set(key, String(value)),
    removeItem: (key) => items.delete(key),
  };
}

function fakeWindow(globals) {
  const cookies = new Map();
  const listeners = new Set();
  const document = {
    referrer: "",
    visibilityState: "visible",
    hide() {
      this.visibilityState = "hidden";
      for (const [type, listener] of listeners) if (type === "visibilitychange") listener();
    },
    get cookie() {
      return [...cookies].map(([name, value]) => `${name}=${value}`).join("; ");
    },
    set cookie(value) {
      const [pair, ...attributes] = value.split("; ");
      const [name, ...rest] = pair.split("=");
      if (attributes.includes("Max-Age=0")) cookies.delete(name);
      else cookies.set(name, rest.join("="));
    },
    createElement: () => {
      const listeners = [];
      return { listeners, addEventListener: (type, listener) => listeners.push([type, listener]) };
    },
    body: {
      appended: [],
      appendChild(element) {
        this.appended.push(element);
        setImmediate(() => element.onload && element.onload());
        return element;
      },
    },
    documentElement: { classList: { add() {} } },
    listeners,
    addEventListener(type, listener) {
      listeners.add([type, listener]);
    },
    removeEventListener(type, listener) {
      for (const entry of listeners) if (entry[0] === type && entry[1] === listener) listeners.delete(entry);
    },
  };
  return {
    location: { hostname: "docs.rapidata.ai", href: "https://docs.rapidata.ai/quickstart/" },
    history: { state: null, replaceState() {} },
    document,
    localStorage: fakeStorage(),
    sessionStorage: fakeStorage(),
    // Resolved per call so node:test mock timers apply.
    setInterval: (...args) => setInterval(...args),
    clearInterval: (id) => clearInterval(id),
    setTimeout: (...args) => setTimeout(...args),
    clearTimeout: (id) => clearTimeout(id),
    ...globals,
  };
}

function fakePosthog(log) {
  let optedOut = false;
  const instance = {
    register: () => log.push(["register"]),
    has_opted_out_capturing: () => optedOut,
    opt_in_capturing: () => {
      optedOut = false;
      log.push(["opt_in_capturing"]);
    },
    opt_out_capturing: () => {
      optedOut = true;
      log.push(["opt_out_capturing"]);
    },
    stopSessionRecording: () => log.push(["stopSessionRecording"]),
    reset: (resetDeviceId) => {
      optedOut = false;
      log.push(["reset", resetDeviceId]);
    },
    setPersonProperties: () => log.push(["setPersonProperties"]),
    capture: (event, properties, options) => log.push(["capture", event, properties, options, { optedOut }]),
    heatmaps: { getAndClearBuffer() {} },
  };
  return {
    init: (token, config) => {
      log.push(["init"]);
      config.loaded(instance);
    },
  };
}

// Fires callbacks the way saveCookiePreferences does in vanilla-cookieconsent 3.1.0 (opt-in mode).
function fakeCookieConsent(stored, consentedAt) {
  let config = null;
  let analyticsAccepted = stored;
  let lastConsentTimestamp = stored === null ? undefined : consentedAt;
  let data = null;
  return {
    run(value) {
      config = value;
      if (analyticsAccepted !== null) config.onConsent({});
    },
    acceptedCategory: (name) => name === "analytics" && analyticsAccepted === true,
    getCookie: (field) => ({ lastConsentTimestamp, data })[field],
    setCookieData({ value, mode }) {
      assert.equal(mode, "update");
      data = Object.assign(data || {}, value);
    },
    showPreferences() {},
    choose(allow) {
      const first = analyticsAccepted === null;
      const changed = !first && analyticsAccepted !== allow;
      analyticsAccepted = allow;
      lastConsentTimestamp = new Date().toISOString();
      if (first) {
        config.onFirstConsent({});
        config.onConsent({});
      } else if (changed) {
        config.onChange({ changedCategories: ["analytics"], changedServices: {} });
      }
    },
  };
}

async function openDocs({ stored = null, consentedAt = new Date().toISOString(), cookies = [] } = {}) {
  const log = [];
  const consent = fakeCookieConsent(stored, consentedAt);
  const win = fakeWindow({ CookieConsent: consent, posthog: fakePosthog(log) });
  for (const name of cookies) win.document.cookie = `${name}=1`;
  analytics.startJourneyAnalytics(win);
  await settle();
  const choose = async (allow) => {
    consent.choose(allow);
    await settle();
  };
  const granted = () => log.filter(([kind, event]) => kind === "capture" && event === "consent_granted");
  const changes = () => granted().map(([, , properties]) => properties.change);
  const twq = () => (win.twq ? win.twq.queue.map((args) => [...args]) : []);
  // Fires after the library's own handler, as the click bubbles from the button to the consent root.
  const clickConsentButton = (role) => {
    const root = win.document.body.appended.find((element) => element.className === "ph-no-capture");
    const target = { closest: (selector) => (selector.includes(`"${role}"`) ? {} : null) };
    for (const [type, listener] of root.listeners) if (type === "click") listener({ target });
  };
  return { log, consent, choose, granted, changes, twq, win, clickConsentButton };
}

describe("consent_granted", () => {
  it("is captured once, opted in, on the first Allow click", async () => {
    const { log, choose, granted } = await openDocs();
    const clickedAt = Date.now();
    await choose(true);

    assert.equal(granted().length, 1);
    const [entry] = granted();
    const [, , properties, options, state] = entry;
    assert.deepEqual(properties, { policy_version: "2026-10-29", change: "first" });
    assert.deepEqual(Object.keys(options), ["$set_once"]);
    assert.equal(options.$set_once.first_consent_surface, "docs");
    assert.match(options.$set_once.first_consent_at, ISO_UTC);
    assert.ok(Date.parse(options.$set_once.first_consent_at) >= clickedAt - 1);
    assert.equal(state.optedOut, false);
    assert.ok(log.indexOf(entry) > log.findIndex(([kind]) => kind === "setPersonProperties"));
  });

  it("is not captured on the first Reject click", async () => {
    const { log, choose } = await openDocs();
    await choose(false);
    assert.deepEqual(log, []);
  });

  it("is not captured when a stored choice is replayed on page load", async () => {
    const accepted = await openDocs({ stored: true });
    assert.ok(
      accepted.log.some(([kind]) => kind === "init"),
      "a stored Allow should still start PostHog"
    );
    assert.deepEqual(accepted.granted(), []);

    const rejected = await openDocs({ stored: false });
    assert.deepEqual(rejected.log, []);
  });

  it("is captured as a regrant when Allow follows a Reject", async () => {
    const samePage = await openDocs();
    await samePage.choose(false);
    await samePage.choose(true);
    assert.deepEqual(samePage.changes(), ["regrant"]);

    const laterLoad = await openDocs({ stored: false });
    await laterLoad.choose(true);
    assert.deepEqual(laterLoad.changes(), ["regrant"]);

    const loaded = await openDocs();
    await loaded.choose(true);
    await loaded.choose(false);
    await loaded.choose(true);
    assert.deepEqual(
      loaded.granted().map(([, , properties, , state]) => [properties.change, state.optedOut]),
      [
        ["first", false],
        ["regrant", false],
      ]
    );
  });

  it("is not captured on revoke, and the opt-out sequence is unchanged", async () => {
    const { log, choose } = await openDocs();
    await choose(true);
    const before = log.length;
    await choose(false);
    assert.deepEqual(log.slice(before), REVOKE_SEQUENCE);
  });

  it("is dropped when Reject comes before PostHog finished loading", async () => {
    const { log, consent, choose, changes } = await openDocs();
    consent.choose(true);
    consent.choose(false);
    await settle();
    assert.deepEqual(log, []);

    await choose(true);
    assert.deepEqual(changes(), ["regrant"]);
  });
});

describe("X pixel", () => {
  const { id, visitEvent, cookies, disabledFeatures } = analytics.constants.xPixel;
  const since = Date.parse(analytics.constants.xPixelConsentSince);
  const before = new Date(since - 1).toISOString();
  beforeEach(() => mock.timers.enable({ apis: ["Date", "setInterval", "setTimeout"], now: since + 3_600_000 }));
  afterEach(() => mock.timers.reset());
  const LOAD = [
    ...disabledFeatures.map((feature) => ["set", feature, "false", id]),
    ["config", id],
    ["event", visitEvent, {}],
  ];

  it("loads and sends one visit after a consent given on or after the new banner text", async () => {
    const atRollout = await openDocs({ stored: true, consentedAt: new Date(since).toISOString() });
    assert.deepEqual(atRollout.twq(), LOAD);

    const fresh = await openDocs();
    await fresh.choose(true);
    assert.deepEqual(fresh.twq(), LOAD);
  });

  it("does not load for a consent given to the older banner text", async () => {
    const stale = await openDocs({ stored: true, consentedAt: before });
    assert.ok(stale.log.some(([kind]) => kind === "init"), "PostHog consent must stay valid");
    assert.equal(stale.win.twq, undefined);
  });

  it("does not load before consent or after Reject", async () => {
    const pending = await openDocs();
    assert.equal(pending.win.twq, undefined);
    await pending.choose(false);
    assert.equal(pending.win.twq, undefined);

    const rejected = await openDocs({ stored: false, consentedAt: new Date(since).toISOString() });
    assert.equal(rejected.win.twq, undefined);
  });

  it("loads when an older consent is re-confirmed with Allow or Save", async () => {
    for (const role of ["all", "save"]) {
      const page = await openDocs({ stored: true, consentedAt: before });
      page.clickConsentButton(role);
      assert.deepEqual(page.twq(), LOAD, role);
      assert.equal(Date.parse(page.consent.getCookie("data").adConsentAt), since + 3_600_000);
    }
  });

  it("is not stamped by Reject, or by Save with analytics off", async () => {
    const rejected = await openDocs({ stored: false, consentedAt: before });
    rejected.clickConsentButton("necessary");
    rejected.clickConsentButton("save");
    assert.equal(rejected.consent.getCookie("data"), null);
    assert.equal(rejected.win.twq, undefined);
  });

  describe("after a ?twclid= landing", () => {
    // Mirrors uwt.js 2.4.12's keep-alive: re-writes _twclid at 5 s, every 10 s for 120 s, and on hide.
    function uwtKeepAlive(win) {
      const write = () => {
        if (!win.document.cookie.includes("_twclid=")) win.document.cookie = "_twclid=abc";
      };
      setTimeout(write, 5_000);
      const interval = setInterval(write, 10_000);
      setTimeout(() => clearInterval(interval), 120_000);
      win.document.addEventListener("visibilitychange", write);
    }
    const hasTwclid = (win) => win.document.cookie.split("; ").some((pair) => pair.startsWith("_twclid="));
    const sweeps = (win) => [...win.document.listeners].filter(([type]) => type === "visibilitychange").length;

    it("keeps _twclid expired for 130 s after Reject, then stops sweeping", async () => {
      const page = await openDocs({ stored: true, consentedAt: new Date(since).toISOString(), cookies: ["_twclid"] });
      page.win.location.href = "https://docs.rapidata.ai/quickstart/?twclid=abc";
      uwtKeepAlive(page.win);
      await page.choose(false);
      for (let second = 1; second <= 130; second++) {
        mock.timers.tick(1_000);
        if (second === 60) page.win.document.hide();
        if (second % 10 === 0) assert.equal(hasTwclid(page.win), false, `_twclid back after ${second} s`);
      }
      assert.equal(hasTwclid(page.win), false);
      assert.equal(sweeps(page.win), 1, "only uwt.js's own listener should remain");
    });

    it("stops the sweep when consent is granted again", async () => {
      const page = await openDocs({ stored: true, consentedAt: new Date(since).toISOString(), cookies: ["_twclid"] });
      await page.choose(false);
      mock.timers.tick(3_000);
      await page.choose(true);
      page.win.document.cookie = "_twclid=abc";
      mock.timers.tick(10_000);
      assert.equal(hasTwclid(page.win), true);
      assert.equal(sweeps(page.win), 0);
    });
  });

  it("sends the visit once per page load across Allow, Reject, Allow", async () => {
    const page = await openDocs({ stored: true, consentedAt: new Date(since).toISOString() });
    await page.choose(false);
    await page.choose(true);
    assert.deepEqual(page.twq(), LOAD);
  });

  it("expires its first-party cookies on Reject", async () => {
    const page = await openDocs({ stored: true, consentedAt: new Date(since).toISOString(), cookies });
    await page.choose(false);
    const left = page.win.document.cookie.split("; ").map((pair) => pair.split("=")[0]);
    assert.deepEqual(left.filter((name) => cookies.includes(name)), []);
  });
});
