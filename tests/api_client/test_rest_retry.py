"""Tests for the REST client's timeout resolution and transient-error retries.

Both behaviours here were the cause of long upload stalls that surfaced to users
as unexplained connection errors: httpx2 treats an explicit ``timeout=None`` as
"wait forever", and the retry predicate only covered part of the transport-error
family, so an aborted upload was never retried.
"""

from __future__ import annotations

import logging

import httpx2
import pytest
from httpx2 import USE_CLIENT_DEFAULT

from rapidata.api_client.rest import RESTClientObject, _RetryNoiseThrottle


class _Configuration:
    """The subset of ``Configuration`` that ``_get_session_defaults`` reads."""

    ssl_ca_cert = None
    verify_ssl = True
    proxy = None
    proxy_headers = None
    retries = None


def _rest_client() -> RESTClientObject:
    client = RESTClientObject.__new__(RESTClientObject)
    client.configuration = _Configuration()  # type: ignore[attr-defined]
    return client


class TestBuildTimeout:
    def test_unset_timeout_defers_to_client_default(self):
        """A bare None would disable timeouts entirely rather than inherit them."""
        assert RESTClientObject._build_timeout(None) is USE_CLIENT_DEFAULT

    def test_malformed_timeout_defers_to_client_default(self):
        assert RESTClientObject._build_timeout(("only-one",)) is USE_CLIENT_DEFAULT

    def test_single_number_applies_to_every_phase(self):
        assert RESTClientObject._build_timeout(5) == httpx2.Timeout(5)

    def test_pair_splits_connect_and_read(self):
        timeout = RESTClientObject._build_timeout((3, 30))
        assert timeout.connect == 3
        assert timeout.read == 30


class TestSessionDefaults:
    def test_client_is_given_a_bounded_timeout(self):
        defaults = _rest_client()._get_session_defaults()
        timeout = defaults["timeout"]
        assert None not in (
            timeout.connect,
            timeout.read,
            timeout.write,
            timeout.pool,
        ), "every phase needs a bound, or a stalled request hangs forever"

    def test_oauth_session_uses_httpx2_client(self):
        client = _rest_client()

        client.setup_oauth_with_token(
            client_id="client-id",
            client_secret="client-secret",
            token={
                "access_token": "access-token",
                "token_type": "Bearer",
                "expires_at": 4_102_444_800,
            },
            token_endpoint="https://auth.example/connect/token",
        )

        assert isinstance(client.session, httpx2.Client)
        client.session.close()


class TestRetryableErrors:
    @pytest.mark.parametrize(
        "error",
        [
            httpx2.ReadError("aborted by local software"),
            httpx2.WriteError("aborted mid-upload"),
            httpx2.PoolTimeout("no free connection"),
            httpx2.ConnectTimeout("no response"),
            httpx2.ReadTimeout("no response"),
            httpx2.RemoteProtocolError("server disconnected"),
            httpx2.ConnectError("connection refused"),
        ],
    )
    def test_transient_transport_errors_are_retried(self, error):
        assert RESTClientObject._is_retryable_error(error) is True

    def test_certificate_failure_is_not_retried(self):
        error = httpx2.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] unable to verify")
        assert RESTClientObject._is_retryable_error(error) is False

    def test_unrelated_error_is_not_retried(self):
        assert (
            RESTClientObject._is_retryable_error(httpx2.UnsupportedProtocol("nope"))
            is False
        )


class TestRetryNoiseThrottle:
    def test_first_retry_warns_once_then_stays_quiet(self, caplog):
        """One line tells the user retries are happening; the rest would be spam."""
        throttle = _RetryNoiseThrottle(interval=3600.0)

        with caplog.at_level(logging.WARNING, logger="rapidata.api_client"):
            for _ in range(500):
                throttle.record("ReadError")

        assert len(caplog.records) == 1
        assert "ReadError" in caplog.records[0].message

    def test_summary_covers_the_interval_that_elapsed(self, caplog):
        throttle = _RetryNoiseThrottle(interval=0.0)

        with caplog.at_level(logging.WARNING, logger="rapidata.api_client"):
            throttle.record("ReadError")  # first occurrence
            throttle.record("ReadError")
            throttle.record("HTTP 429")

        # The counters reset each time they are reported, so the totals across the
        # summaries account for every recorded retry exactly once.
        assert len(caplog.records) == 3
        assert "HTTP 429" in caplog.records[-1].message
