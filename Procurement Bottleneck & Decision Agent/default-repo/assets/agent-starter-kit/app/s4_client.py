"""S/4HANA OData client — credentials via BTP Destination Service.

ALL S/4HANA credentials live in the BTP Destination Service — never in code, never
in environment variables directly. The client resolves the named destination at
runtime through the Destination Service API (which is bound via VCAP_SERVICES).

This means:
  - Rotating credentials = update the BTP destination → no code change, no redeploy.
  - Promoting DEV→TEST→PROD = change S4_DESTINATION env var to point to the correct
    destination name → same code, different binding.
  - Public cloud S/4: destination uses OAuth2SAMLBearerAssertion, ProxyType Internet.
  - On-premise S/4: destination uses PrincipalPropagation, ProxyType OnPremise
    (requires Cloud Connector + STRUST + CERTRULE configured in S/4).

Advisory / read-only: GET only. Never POST, PATCH, or DELETE.
Hard cap: $top=100 on all list reads to prevent unbounded data pulls.

Required environment variable (set via cf set-env, not in any file):
  S4_DESTINATION  — name of the BTP destination pointing to S/4HANA, e.g. S4_AGENT_DEV

Required VCAP binding: destination service instance (bound via mta.yaml).

TODO: Implement _resolve_destination_url() to call the Destination Service API and
      exchange the XSUAA service token for the destination's resolved URL and auth headers.
      Reference: https://help.sap.com/docs/connectivity/sap-btp-connectivity-cf/consuming-destination-service-v2
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30
_MAX_TOP = 100


def _destination_name() -> str:
    name = os.environ.get("S4_DESTINATION", "")
    if not name:
        raise RuntimeError(
            "S4_DESTINATION is not set. "
            "Set it via cf set-env to the BTP destination name for your S/4HANA system."
        )
    return name


def _resolve_destination(name: str) -> dict[str, Any]:
    """Resolve a named BTP destination via the Destination Service API.

    Returns a dict with keys: url, headers (auth headers to forward to S/4).

    TODO: Implement this by:
    1. Reading VCAP_SERVICES["destination"][0]["credentials"] for the service URL + XSUAA token URL.
    2. Obtaining an XSUAA client credentials token for the Destination Service.
    3. Calling GET <dest-service-url>/destination-configuration/v1/destinations/<name>.
    4. Returning the resolved URL and auth headers from destinationConfiguration.
    """
    vcap_raw = os.environ.get("VCAP_SERVICES", "{}")
    vcap = json.loads(vcap_raw)
    dest_instances = vcap.get("destination", [])
    if not dest_instances:
        raise RuntimeError(
            "Destination Service not bound. "
            "Add it to mta.yaml and redeploy: cf deploy mta_archives/*.mtar"
        )
    # TODO: replace with real Destination Service API call (see module docstring)
    raise NotImplementedError(
        f"_resolve_destination('{name}') not yet implemented. "
        "See module docstring for implementation steps."
    )


class S4Client:
    """Thin async OData client for S/4HANA reads via BTP Destination Service.

    Usage:
        client = S4Client()
        results = await client.get("API_PURCHASEORDER_PROCESS_SRV", "A_PurchaseOrder",
                                   {"$filter": "Supplier eq 'LIFNR-001'", "$top": 50})
    """

    def __init__(self, destination: str | None = None) -> None:
        self._destination = destination or _destination_name()

    async def get(
        self,
        service: str,
        entity_set: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a GET request against an OData entity set.

        Enforces $top ≤ 100. Returns the results list or empty list on no data.
        Raises httpx.HTTPStatusError on 4xx/5xx.
        """
        resolved = _resolve_destination(self._destination)
        base_url = resolved["url"].rstrip("/")
        headers = resolved.get("headers", {})
        headers.setdefault("Accept", "application/json")

        query: dict[str, Any] = dict(params or {})
        query["$format"] = "json"
        if "$top" in query:
            query["$top"] = min(int(query["$top"]), _MAX_TOP)

        url = f"{base_url}/{service}/{entity_set}"
        log.debug("S4Client GET %s params=%s", url, list(query.keys()))

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.get(url, params=query, headers=headers)
            resp.raise_for_status()

        data = resp.json().get("d", {})
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return [data] if data else []
