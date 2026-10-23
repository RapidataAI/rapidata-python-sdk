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
    assert.equal(analytics.constants.consentCookie.name, constants.consentCookie.name);
    assert.equal(analytics.constants.consentCookie.revision, constants.consentCookie.revision);
    assert.equal(analytics.constants.consentCookie.policyVersion, constants.consentCookie.policyVersion);
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
