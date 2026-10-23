const assert = require("node:assert/strict");
const { describe, it } = require("node:test");

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
  const document = {
    referrer: "",
    get cookie() {
      return [...cookies].map(([name, value]) => `${name}=${value}`).join("; ");
    },
    set cookie(value) {
      const [pair, ...attributes] = value.split("; ");
      const [name, ...rest] = pair.split("=");
      if (attributes.includes("Max-Age=0")) cookies.delete(name);
      else cookies.set(name, rest.join("="));
    },
    createElement: () => ({}),
    body: {
      appendChild: (element) => {
        setImmediate(() => element.onload && element.onload());
        return element;
      },
    },
    documentElement: { classList: { add() {} } },
    addEventListener() {},
  };
  return {
    location: { hostname: "docs.rapidata.ai", href: "https://docs.rapidata.ai/quickstart/" },
    history: { state: null, replaceState() {} },
    document,
    localStorage: fakeStorage(),
    sessionStorage: fakeStorage(),
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
function fakeCookieConsent(stored) {
  let config = null;
  let analyticsAccepted = stored;
  return {
    run(value) {
      config = value;
      if (analyticsAccepted !== null) config.onConsent({});
    },
    acceptedCategory: (name) => name === "analytics" && analyticsAccepted === true,
    showPreferences() {},
    choose(allow) {
      const first = analyticsAccepted === null;
      const changed = !first && analyticsAccepted !== allow;
      analyticsAccepted = allow;
      if (first) {
        config.onFirstConsent({});
        config.onConsent({});
      } else if (changed) {
        config.onChange({ changedCategories: ["analytics"], changedServices: {} });
      }
    },
  };
}

async function openDocs({ stored = null } = {}) {
  const log = [];
  const consent = fakeCookieConsent(stored);
  analytics.startJourneyAnalytics(fakeWindow({ CookieConsent: consent, posthog: fakePosthog(log) }));
  await settle();
  const choose = async (allow) => {
    consent.choose(allow);
    await settle();
  };
  const granted = () => log.filter(([kind, event]) => kind === "capture" && event === "consent_granted");
  const changes = () => granted().map(([, , properties]) => properties.change);
  return { log, consent, choose, granted, changes };
}

describe("consent_granted", () => {
  it("is captured once, opted in, on the first Allow click", async () => {
    const { log, choose, granted } = await openDocs();
    const clickedAt = Date.now();
    await choose(true);

    assert.equal(granted().length, 1);
    const [entry] = granted();
    const [, , properties, options, state] = entry;
    assert.deepEqual(properties, { policy_version: "2026-10-20", change: "first" });
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
