(function () {
  "use strict";

  const TOKEN = "phc_sPu43oDPe9Gfd3Pg8nVHvhLj3rzyHQa8ujPFP7muBqtZ";
  const PRODUCTION_HOSTS = [
    "rapidata.ai",
    "www.rapidata.ai",
    "app.rapidata.ai",
    "docs.rapidata.ai",
    "benchmark.ai",
    "www.benchmark.ai",
  ];
  const INTERNAL_REFERRER_EXACT = PRODUCTION_HOSTS.concat([
    "auth.rapidata.ai",
    "accounts.google.com",
    "checkout.stripe.com",
    "billing.stripe.com",
    "localhost",
    "127.0.0.1",
    "[::1]",
  ]);
  const INTERNAL_REFERRER_SUFFIX = [".vercel.app", ".rabbitdata.ch", ".rapidata.dev", ".localhost"];
  // First match wins.
  const REFERRER_RULES = [
    { match: "suffix", value: ".hf.space", source: "huggingface", medium: "referral" },
    { match: "domain", value: "huggingface.co", source: "huggingface", medium: "referral" },
    { match: "exact", value: "gemini.google.com", source: "gemini", medium: "ai" },
    {
      match: "regex",
      value: "(^|\\.)google\\.(com|[a-z]{2}|co\\.[a-z]{2}|com\\.[a-z]{2})$",
      source: "google",
      medium: "organic",
    },
    { match: "domain", value: "bing.com", source: "bing", medium: "organic" },
    { match: "domain", value: "duckduckgo.com", source: "duckduckgo", medium: "organic" },
    { match: "exact", value: "search.yahoo.com", source: "yahoo", medium: "organic" },
    { match: "exact", value: "search.brave.com", source: "brave", medium: "organic" },
    { match: "domain", value: "github.com", source: "github", medium: "referral" },
    { match: "suffix", value: ".github.io", source: "github", medium: "referral" },
    { match: "domain", value: "pypi.org", source: "pypi", medium: "referral" },
    { match: "domain", value: "linkedin.com", source: "linkedin", medium: "social" },
    { match: "exact", value: "lnkd.in", source: "linkedin", medium: "social" },
    { match: "exact", value: "t.co", source: "x", medium: "social" },
    { match: "domain", value: "x.com", source: "x", medium: "social" },
    { match: "domain", value: "twitter.com", source: "x", medium: "social" },
    { match: "domain", value: "reddit.com", source: "reddit", medium: "social" },
    { match: "exact", value: "news.ycombinator.com", source: "hackernews", medium: "social" },
    { match: "exact", value: "chatgpt.com", source: "chatgpt", medium: "ai" },
    { match: "exact", value: "chat.openai.com", source: "chatgpt", medium: "ai" },
    { match: "domain", value: "perplexity.ai", source: "perplexity", medium: "ai" },
    { match: "exact", value: "claude.ai", source: "claude", medium: "ai" },
  ];
  const HANDOFF_KEY = "rd_journey";
  const ATTRIBUTION_COOKIE = "rd_attribution_v1";
  const ATTRIBUTION_MAX_AGE_SECONDS = 7776000;
  const ATTRIBUTION_MAX_CHARS = 2048;
  const UTM_MAX = 64;
  const PATH_MAX = 128;
  const HOST_MAX = 128;
  const TOUCH_KEYS = ["source", "medium", "campaign", "content", "landingPath", "referrerHost", "observedAt"];
  const TOUCH_PROPERTIES = ["source", "medium", "campaign", "content", "landing_path", "referrer_host", "observed_at"];
  const COOKIE_ROOTS = ["rapidata.ai", "rabbitdata.ch", "rapidata.dev"];
  const OUTBOUND_HOSTS = ["app.rapidata.ai", "docs.rapidata.ai", "benchmark.ai", "www.benchmark.ai"];
  // Python's str.strip() set, not String.prototype.trim(), so UTM values match reference.py.
  const PY_WHITESPACE = /^[\t-\r\x1c-\x20\x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\t-\r\x1c-\x20\x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g;
  const LONE_SURROGATE = /\p{Cs}/u;
  const ISO_TIMESTAMP = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)\.(\d{3})Z$/;

  const PRIVACY_URL = "https://rapidata.ai/privacy";
  const POSTHOG_SCRIPT = {
    url: "https://cdn.jsdelivr.net/npm/posthog-js@1.436.1/dist/array.js",
    integrity: "sha384-Fkj8KW31wHGhQjix5qziB/fcuOMhFevLxnEKrZ1qbPPIPdP5I0Kt1/fYJ3TgFLL1",
  };
  const CONSENT_SCRIPT = {
    url: "https://cdn.jsdelivr.net/npm/vanilla-cookieconsent@3.1.0/dist/cookieconsent.umd.js",
    integrity: "sha384-xOY5eqzqHsjfa8YYAomICWjVJ3g9q1C1tWgRF09ut5PzRJjLFSpKH7gCsIN3hKcA",
  };
  const CONSENT_STYLE = {
    url: "https://cdn.jsdelivr.net/npm/vanilla-cookieconsent@3.1.0/dist/cookieconsent.css",
    integrity: "sha384-9KcNFt4axT+TNOVPHpwGHOm4Kv0UcMjdVya1kl+EPBQG+Vmqtz28cnx0f5PZYcnF",
  };

  // Python slices and len() count code points; JS strings count UTF-16 units.
  function truncate(value, max) {
    const points = Array.from(value);
    return points.length > max ? points.slice(0, max).join("") : value;
  }

  function codePointLength(value) {
    return Array.from(value).length;
  }

  function isWellFormedString(value) {
    return typeof value === "string" && !LONE_SURROGATE.test(value);
  }

  function isInternalHost(host) {
    return INTERNAL_REFERRER_EXACT.includes(host) || INTERNAL_REFERRER_SUFFIX.some((suffix) => host.endsWith(suffix));
  }

  function matchesRule(host, rule) {
    switch (rule.match) {
      case "exact":
        return host === rule.value;
      case "suffix":
        return host.endsWith(rule.value);
      case "domain":
        return host === rule.value || host.endsWith("." + rule.value);
      case "regex":
        return new RegExp(rule.value).test(host);
      default:
        return false;
    }
  }

  function classifyReferrer(host) {
    const rule = REFERRER_RULES.find((candidate) => matchesRule(host, candidate));
    if (rule) return { source: rule.source, medium: rule.medium };
    return { source: truncate(host.startsWith("www.") ? host.slice(4) : host, UTM_MAX), medium: "referral" };
  }

  function normalizeUtm(value) {
    if (value === null) return null;
    return truncate(value.replace(PY_WHITESPACE, "").toLowerCase(), UTM_MAX) || null;
  }

  function referrerHostOf(referrer) {
    if (!referrer) return null;
    try {
      return truncate(new URL(referrer).hostname.toLowerCase(), HOST_MAX) || null;
    } catch (error) {
      return null;
    }
  }

  function touch(source, medium, campaign, content, landingPath, referrerHost, observedAt) {
    return { source, medium, campaign, content, landingPath, referrerHost, observedAt };
  }

  function parseCampaignTouch(url, referrer, now) {
    const parsed = new URL(String(url));
    const utm = {};
    for (const key of ["source", "medium", "campaign", "content"]) {
      utm[key] = normalizeUtm(parsed.searchParams.get("utm_" + key));
    }
    const referrerHost = referrerHostOf(referrer);
    const landingPath = truncate(parsed.pathname || "/", PATH_MAX);
    const observedAt = new Date(now).toISOString();
    if (referrerHost && isInternalHost(referrerHost)) {
      return { kind: "internal", touch: touch(null, null, null, null, landingPath, referrerHost, observedAt) };
    }
    if (utm.source || utm.medium || utm.campaign || utm.content) {
      return {
        kind: "campaign",
        touch: touch(utm.source, utm.medium, utm.campaign, utm.content, landingPath, referrerHost, observedAt),
      };
    }
    if (referrerHost) {
      const { source, medium } = classifyReferrer(referrerHost);
      return { kind: "referral", touch: touch(source, medium, null, null, landingPath, referrerHost, observedAt) };
    }
    return { kind: "direct", touch: touch(null, null, null, null, landingPath, null, observedAt) };
  }

  function mergeAttribution(existing, entry) {
    const first = existing ? existing.first : entry.touch;
    const external = entry.kind === "campaign" || entry.kind === "referral";
    const last = external ? entry.touch : existing ? existing.last : null;
    return { v: 1, first, last };
  }

  function encodeAttributionCookie(attribution) {
    let binary = "";
    for (const byte of new TextEncoder().encode(JSON.stringify(attribution))) binary += String.fromCharCode(byte);
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function hasExactKeys(value, keys) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
    const actual = Object.keys(value);
    return actual.length === keys.length && actual.every((key, index) => key === keys[index]);
  }

  function parseIsoTimestamp(value) {
    const match = typeof value === "string" ? ISO_TIMESTAMP.exec(value) : null;
    if (!match) return null;
    const [year, month, day, hour, minute, second, millisecond] = match.slice(1).map(Number);
    if (year < 1 || hour > 23 || minute > 59 || second > 59) return null;
    const date = new Date(0);
    date.setUTCFullYear(year, month - 1, day);
    date.setUTCHours(hour, minute, second, millisecond);
    const sameDay = date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
    return sameDay ? date : null;
  }

  function isValidTouch(value) {
    if (!hasExactKeys(value, TOUCH_KEYS)) return false;
    for (const key of ["source", "medium", "campaign", "content", "referrerHost"]) {
      const field = value[key];
      const max = key === "referrerHost" ? HOST_MAX : UTM_MAX;
      if (field !== null && !(isWellFormedString(field) && field.length > 0 && codePointLength(field) <= max)) {
        return false;
      }
    }
    const path = value.landingPath;
    if (!(isWellFormedString(path) && path.startsWith("/") && codePointLength(path) <= PATH_MAX)) return false;
    return parseIsoTimestamp(value.observedAt) !== null;
  }

  function decodeAttributionCookie(value) {
    if (typeof value !== "string" || value.length > ATTRIBUTION_MAX_CHARS || !/^[A-Za-z0-9_-]*$/.test(value)) {
      return null;
    }
    let decoded;
    try {
      const base64 = value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (value.length % 4)) % 4);
      const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0));
      decoded = JSON.parse(new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes));
    } catch (error) {
      return null;
    }
    if (!hasExactKeys(decoded, ["v", "first", "last"]) || decoded.v !== 1) return null;
    if (!isValidTouch(decoded.first) || !(decoded.last === null || isValidTouch(decoded.last))) return null;
    return decoded;
  }

  function stripHandoff(url) {
    const href = String(url);
    const hash = href.indexOf("#");
    return hash >= 0 && href.startsWith(HANDOFF_KEY + "=", hash + 1) ? href.slice(0, hash) : href;
  }

  function resolveAnalyticsTarget(hostname) {
    const host = String(hostname).toLowerCase();
    if (PRODUCTION_HOSTS.includes(host)) return { environment: "production", token: TOKEN };
    if (host.endsWith(".vercel.app")) return { environment: "preview", token: TOKEN };
    if (host.endsWith(".rabbitdata.ch")) return { environment: "test", token: TOKEN };
    if (["localhost", "127.0.0.1", "[::1]", "rapidata.dev"].includes(host) || host.endsWith(".localhost") || host.endsWith(".rapidata.dev")) {
      return { environment: "development", token: TOKEN };
    }
    return null;
  }

  function sharedCookieDomain(hostname) {
    return COOKIE_ROOTS.find((root) => hostname === root || hostname.endsWith("." + root)) || null;
  }

  function touchProperties(prefix, value) {
    const properties = {};
    TOUCH_KEYS.forEach((key, index) => {
      properties[prefix + TOUCH_PROPERTIES[index]] = value ? value[key] : null;
    });
    return properties;
  }

  function surfaceProperties(environment) {
    return { surface: "docs", environment, tracking_version: 1, event_source: "browser" };
  }

  function superProperties(environment, attribution) {
    return Object.assign(
      surfaceProperties(environment),
      touchProperties("first_", attribution.first),
      touchProperties("last_external_", attribution.last)
    );
  }

  function isOutboundHost(host) {
    return OUTBOUND_HOSTS.includes(host) || host === "huggingface.co" || host.endsWith(".huggingface.co");
  }

  function consentConfig(cookieDomain, root, onDecision) {
    const description =
      "Allow analytics to connect your visits across our sites and understand how you use Rapidata. " +
      "You can change this choice later.";
    const privacyLink = '<a href="' + PRIVACY_URL + '" target="_blank" rel="noopener">Privacy policy</a>';
    return {
      root,
      revision: 1,
      cookie: { name: "cc_cookie", domain: cookieDomain },
      categories: {
        necessary: { enabled: true, readOnly: true },
        analytics: {},
      },
      guiOptions: {
        consentModal: { layout: "box", position: "bottom right" },
        preferencesModal: { layout: "box" },
      },
      onConsent: onDecision,
      onChange: onDecision,
      language: {
        default: "en",
        translations: {
          en: {
            consentModal: {
              title: "Analytics preferences",
              description,
              acceptAllBtn: "Allow analytics",
              acceptNecessaryBtn: "Reject analytics",
              footer: privacyLink,
            },
            preferencesModal: {
              title: "Analytics preferences",
              acceptAllBtn: "Allow analytics",
              acceptNecessaryBtn: "Reject analytics",
              savePreferencesBtn: "Save preferences",
              closeIconLabel: "Close",
              sections: [
                { title: "Necessary", description: "Required for the site to work.", linkedCategory: "necessary" },
                { title: "Analytics", description, linkedCategory: "analytics" },
                { description: privacyLink },
              ],
            },
          },
        },
      },
    };
  }

  function loadAsset(doc, asset, stylesheet) {
    return new Promise((resolve, reject) => {
      const element = doc.createElement(stylesheet ? "link" : "script");
      if (stylesheet) {
        element.rel = "stylesheet";
        element.href = asset.url;
      } else {
        element.async = true;
        element.src = asset.url;
      }
      element.integrity = asset.integrity;
      element.crossOrigin = "anonymous";
      element.onload = resolve;
      element.onerror = reject;
      // Material's instant navigation drops <head> nodes the next page lacks; <body> children survive.
      doc.body.appendChild(element);
    });
  }

  function startJourneyAnalytics(win, loaders) {
    const target = resolveAnalyticsTarget(win.location.hostname);
    if (!target) return null;
    const doc = win.document;
    const load = loaders || {
      script: (asset) => loadAsset(doc, asset, false),
      style: (asset) => loadAsset(doc, asset, true),
    };

    const stripped = stripHandoff(win.location.href);
    if (stripped !== win.location.href) win.history.replaceState(win.history.state, "", stripped);
    const entry = parseCampaignTouch(stripped, doc.referrer, new Date());

    const hostname = win.location.hostname;
    const sharedDomain = sharedCookieDomain(hostname);
    const secure = win.location.protocol === "https:" ? "; Secure" : "";
    const cookieAttributes = "; Path=/" + (sharedDomain ? "; Domain=" + sharedDomain : "") + "; SameSite=Lax" + secure;
    let consented = false;
    let initialized = false;
    let posthog = null;
    let posthogScript = null;
    let current = null;

    function readCookie(name) {
      const prefix = name + "=";
      const pair = doc.cookie.split("; ").find((candidate) => candidate.startsWith(prefix));
      return pair ? pair.slice(prefix.length) : null;
    }

    function expireCookie(name) {
      doc.cookie = name + "=; Path=/; Max-Age=0; SameSite=Lax" + secure;
      if (sharedDomain) doc.cookie = name + "=; Path=/; Domain=" + sharedDomain + "; Max-Age=0; SameSite=Lax" + secure;
    }

    function sendPersonProperties(instance) {
      const lastExternal = current.attribution.last ? touchProperties("last_external_", current.attribution.last) : undefined;
      instance.setPersonProperties(lastExternal, touchProperties("first_", current.attribution.first));
    }

    function grant() {
      consented = true;
      const attribution = mergeAttribution(decodeAttributionCookie(readCookie(ATTRIBUTION_COOKIE)), entry);
      const encoded = encodeAttributionCookie(attribution);
      if (encoded.length <= ATTRIBUTION_MAX_CHARS) {
        doc.cookie = ATTRIBUTION_COOKIE + "=" + encoded + "; Max-Age=" + ATTRIBUTION_MAX_AGE_SECONDS + cookieAttributes;
      }
      current = { attribution, properties: superProperties(target.environment, attribution) };

      if (posthog) {
        posthog.register(current.properties);
        if (posthog.has_opted_out_capturing()) {
          // Heatmaps keep buffering clicks while opted out; drop what was recorded during the refusal.
          if (posthog.heatmaps) posthog.heatmaps.getAndClearBuffer();
          posthog.opt_in_capturing({ captureEventName: false });
          posthog.capture("$pageview");
        }
        sendPersonProperties(posthog);
        return Promise.resolve();
      }
      posthogScript = posthogScript || load.script(POSTHOG_SCRIPT);
      return posthogScript.then(initPosthog, () => undefined);
    }

    function initPosthog() {
      if (!consented || initialized) return;
      initialized = true;
      win.posthog.init(target.token, {
        api_host: "https://eu.i.posthog.com",
        ui_host: "https://eu.posthog.com",
        defaults: "2026-05-30",
        persistence: "localStorage+cookie",
        cross_subdomain_cookie: true,
        // A stale per-origin localStorage id would otherwise overwrite the identified id in the shared cookie.
        cookieWinsOnConflict: true,
        capture_pageview: "history_change",
        opt_out_persistence_by_default: true,
        // reset() on revoke would otherwise reload flags, contacting PostHog after consent is withdrawn.
        advanced_disable_feature_flags: true,
        disable_session_recording: true,
        // One project serves every environment and reset() drops super properties, so stamp each event.
        before_send: (event) => {
          if (event) event.properties = Object.assign(event.properties || {}, surfaceProperties(target.environment));
          return event;
        },
        loaded: (instance) => {
          instance.register(current.properties);
          // The opt-out flag survives a revoke in localStorage; without this the first $pageview is dropped.
          if (instance.has_opted_out_capturing()) instance.opt_in_capturing({ captureEventName: false });
          sendPersonProperties(instance);
          posthog = instance;
        },
      });
    }

    function revoke() {
      consented = false;
      if (posthog) {
        posthog.opt_out_capturing();
        posthog.stopSessionRecording();
        posthog.reset(true);
        // reset() deletes the opt-out flag, so opt out again or capturing resumes.
        posthog.opt_out_capturing();
      }
      expireCookie(ATTRIBUTION_COOKIE);
      for (const pair of doc.cookie.split("; ")) {
        const name = pair.split("=")[0];
        if (name.startsWith("ph_")) expireCookie(name);
      }
      for (const storage of [win.localStorage, win.sessionStorage]) {
        for (let index = storage.length - 1; index >= 0; index--) {
          const key = storage.key(index);
          if (key && key.startsWith("ph_")) storage.removeItem(key);
        }
      }
    }

    function onDecision() {
      if (win.CookieConsent.acceptedCategory("analytics")) return grant();
      revoke();
      return Promise.resolve();
    }

    function trackOutbound(event) {
      if (!posthog || !consented || (event.type === "auxclick" && event.button !== 1)) return;
      const link = event.target && event.target.closest ? event.target.closest("a[href]") : null;
      if (!link) return;
      let url;
      try {
        url = new URL(link.href, win.location.href);
      } catch (error) {
        return;
      }
      const host = url.hostname.toLowerCase();
      if (host === hostname || !isOutboundHost(host)) return;
      posthog.capture(
        "outbound_link_clicked",
        { destination_host: host, destination_path: url.pathname },
        { send_instantly: true, transport: "sendBeacon" }
      );
    }

    function openPreferences(event) {
      const trigger = event.target && event.target.closest ? event.target.closest("[data-rd-consent]") : null;
      if (!trigger || !win.CookieConsent) return;
      event.preventDefault();
      win.CookieConsent.showPreferences();
    }

    doc.addEventListener("click", trackOutbound, true);
    doc.addEventListener("auxclick", trackOutbound, true);
    doc.addEventListener("click", openPreferences);
    doc.documentElement.classList.add("cc--darkmode");
    const consentRoot = doc.createElement("div");
    consentRoot.className = "ph-no-capture";
    doc.body.appendChild(consentRoot);

    const ready = Promise.all([load.style(CONSENT_STYLE), load.script(CONSENT_SCRIPT)])
      .then(() => win.CookieConsent.run(consentConfig(sharedDomain || hostname, consentRoot, onDecision)))
      .catch(() => undefined);
    return { entry, ready };
  }

  const api = {
    constants: {
      token: TOKEN,
      assets: { posthog: POSTHOG_SCRIPT, consentScript: CONSENT_SCRIPT, consentStyle: CONSENT_STYLE },
      productionHosts: PRODUCTION_HOSTS,
      internalReferrerExact: INTERNAL_REFERRER_EXACT,
      internalReferrerSuffix: INTERNAL_REFERRER_SUFFIX,
      referrerRules: REFERRER_RULES,
      handoffKey: HANDOFF_KEY,
      attributionCookie: { name: ATTRIBUTION_COOKIE, maxAgeSeconds: ATTRIBUTION_MAX_AGE_SECONDS, maxChars: ATTRIBUTION_MAX_CHARS },
      limits: { utmMaxChars: UTM_MAX, landingPathMaxChars: PATH_MAX, referrerHostMaxChars: HOST_MAX },
    },
    parseCampaignTouch,
    mergeAttribution,
    encodeAttributionCookie,
    decodeAttributionCookie,
    stripHandoff,
    resolveAnalyticsTarget,
    startJourneyAnalytics,
  };

  if (typeof module === "object" && module.exports) {
    module.exports = api;
    return;
  }
  startJourneyAnalytics(window);
})();
