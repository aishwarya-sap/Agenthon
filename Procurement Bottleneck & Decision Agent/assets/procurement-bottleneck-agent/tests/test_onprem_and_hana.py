"""Unit tests for the on-prem S/4 transport (BTP Destination + Cloud Connector) and the
HANA Cloud decision store. All network + driver calls are faked so these run offline.
"""
import json
import sys
import types

import httpx
import pytest

from app import memory, s4_client


class _Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=httpx.Request("GET", "http://x"), response=self)


DEST_BODY = {
    "destinationConfiguration": {"URL": "https://s4.int", "Authentication": "BasicAuthentication",
                                 "ProxyType": "OnPremise", "sap-client": "150"},
    "authTokens": [{"type": "BasicAuthentication", "value": "x",
                    "http_header": {"key": "Authorization", "value": "Basic x"}}],
}


@pytest.fixture(autouse=True)
def _clean():
    s4_client.clear_onprem_cache()
    yield
    s4_client.clear_onprem_cache()


class _FakeResolveClient:
    def __init__(self, *a, **k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def post(self, url, data=None): return _Resp(200, {"access_token": "tok"})
    async def get(self, url, headers=None): return _Resp(200, DEST_BODY)


async def test_resolve_onprem_ctx(monkeypatch):
    monkeypatch.setenv("VCAP_SERVICES", json.dumps({
        "destination": [{"credentials": {"url": "https://xsuaa", "uri": "https://dest",
                                          "clientid": "c", "clientsecret": "s"}}],
        "connectivity": [{"credentials": {"url": "https://cxsuaa", "clientid": "c", "clientsecret": "s",
                                          "onpremise_proxy_host": "p.int", "onpremise_proxy_port": "20003"}}],
    }))
    monkeypatch.setattr(httpx, "AsyncClient", _FakeResolveClient)
    ctx = await s4_client._resolve_onprem_ctx()
    assert ctx["base_url"] == "https://s4.int"
    assert ctx["auth_header"] == "Basic x"
    assert ctx["proxy_url"] == "http://p.int:20003"
    assert ctx["proxy_token"] == "tok"
    assert ctx["sap_client"] == "150"


class _FakeODataClient:
    captured: dict = {}
    def __init__(self, *a, **k): _FakeODataClient.captured["kw"] = k
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def get(self, url, params=None, headers=None):
        _FakeODataClient.captured.update(url=url, params=params, headers=headers)
        return _Resp(200, {"d": {"results": [{"PurchaseOrder": "45001"}]}})


async def test_get_onprem_routes_via_proxy(monkeypatch):
    monkeypatch.setenv("SAP_MODE", "onprem")

    async def fake_ctx(user_token=None):
        return {"base_url": "https://s4.int", "auth_header": "Basic x",
                "proxy_url": "http://p.int:20003", "proxy_token": "ptok", "sap_client": "150"}

    monkeypatch.setattr(s4_client, "_resolve_onprem_ctx", fake_ctx)
    monkeypatch.setattr(httpx, "AsyncClient", _FakeODataClient)
    rows = await s4_client._get(None, "API_PURCHASEORDER_PROCESS_SRV", "A_PurchaseOrderItem", {"$top": "100"})
    cap = _FakeODataClient.captured
    assert rows == [{"PurchaseOrder": "45001"}]
    assert "A_PurchaseOrderItem" in cap["url"]
    assert cap["params"]["sap-client"] == "150"
    assert cap["headers"]["Authorization"] == "Basic x"
    assert cap["headers"]["Proxy-Authorization"] == "Bearer ptok"
    assert cap["kw"].get("proxy") == "http://p.int:20003"
    assert "APIKey" not in cap["headers"]


# --- HANA Cloud decision store ----------------------------------------------

def _install_fake_hdbcli(monkeypatch):
    executed = []

    class Cur:
        def __init__(self, store): self.store = store
        def execute(self, sql, params=None):
            executed.append((sql.strip().split()[0], params))
            self._rows = self.store["rows"] if sql.strip().startswith("SELECT") else []
        def fetchall(self): return self._rows
        def close(self): pass

    class Conn:
        def __init__(self): self.store = {"rows": []}
        def cursor(self): return Cur(self.store)

    conn = Conn()
    fake = types.ModuleType("hdbcli")
    fake.dbapi = types.SimpleNamespace(connect=lambda **k: conn)
    monkeypatch.setitem(sys.modules, "hdbcli", fake)
    monkeypatch.setenv("HANA_HOST", "h")
    monkeypatch.setenv("HANA_USER", "u")
    monkeypatch.setenv("HANA_PASSWORD", "p")
    monkeypatch.setenv("HANA_SCHEMA", "S")
    return conn, executed


def _record() -> memory.DecisionRecord:
    return memory.DecisionRecord(
        supplier_lifnr="1001", material_group="STEEL", plant="1710", po_reference="45001",
        silence_duration_at_detection=5, consequence_exposure_at_decision=1000.0,
        action_taken="escalate", hod_reviewer_id="H1", approval_keyword_received="approve")


def test_hana_store_append_and_recall(monkeypatch):
    conn, executed = _install_fake_hdbcli(monkeypatch)
    store = memory.HanaMemoryStore()
    rec = _record()
    assert store.append(rec) == rec.record_id
    assert any(op == "INSERT" for op, _ in executed)
    # all() reconstructs DecisionRecords from the stored JSON payload
    conn.store["rows"] = [("decision", json.dumps(rec.as_dict()))]
    allrecs = store.all()
    assert len(allrecs) == 1 and allrecs[0].supplier_lifnr == "1001"
    # inherited recall() ranks by similarity over all()
    hits = store.recall("1001", "STEEL", 5)
    assert hits and hits[0]["supplier_lifnr"] == "1001"


def test_hana_store_append_outcome_is_append_only(monkeypatch):
    conn, executed = _install_fake_hdbcli(monkeypatch)
    store = memory.HanaMemoryStore()
    rec = _record()
    conn.store["rows"] = [("decision", json.dumps(rec.as_dict()))]
    assert store.append_outcome(rec.record_id, "supplier_responded", 3) is True
    # outcome written as a NEW row (append-only), never an UPDATE
    ops = [op for op, _ in executed]
    assert "INSERT" in ops and "UPDATE" not in ops
