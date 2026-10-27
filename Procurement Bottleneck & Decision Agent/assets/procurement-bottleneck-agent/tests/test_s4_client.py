"""Tests for the Accelerator Hub live-read client (field mapping) + dev-auth bypass.

The OData HTTP layer (`s4_client._get`) is monkeypatched with canned V2 responses so
the mapping logic is verified offline without network.
"""
import pytest

from app import s4_client

pytestmark = pytest.mark.unit


@pytest.fixture
def canned(monkeypatch):
    """Patch s4_client._get to serve canned OData rows keyed by (service, entityset)."""
    responses: dict[str, list] = {}

    async def fake_get(_client, service, entityset, params):
        # exact entity-set match (strip any key predicate like A_PurchaseOrder('x'))
        base = entityset.split("(")[0]
        return responses.get(base, [])

    monkeypatch.setattr(s4_client, "_get", fake_get)
    monkeypatch.setenv("S4_BASE_URL", "https://sandbox.example/odata")
    monkeypatch.setenv("S4_API_KEY", "test-key")
    return responses


async def test_po_chain_maps_real_fields(canned):
    canned["A_PurchaseOrder"] = [{"PurchaseOrder": "4500000123", "Supplier": "17300001",
                                  "PurchaseOrderDate": "/Date(1470268800000)/"}]
    canned["A_PurchaseOrderItem"] = [{"PurchaseOrderItem": "10", "Material": "MAT-1",
                                      "MaterialGroup": "STEEL", "NetPriceAmount": "180000",
                                      "IsCompletelyDelivered": False, "PurchasingDocumentDeletionCode": ""}]
    canned["A_PurchaseOrderScheduleLine"] = [{"ScheduleLineDeliveryDate": "/Date(1761264000000)/"}]
    res = await s4_client.get_open_pr_po_chain(po_number="4500000123")
    row = res["value"][0]
    assert res["signal_status"] == "live"
    assert row["po_number"] == "4500000123"
    assert row["supplier_lifnr"] == "17300001"
    assert row["material_category"] == "STEEL"
    assert row["po_net_value_eur"] == 180000.0
    assert row["delivery_complete_flag_elikz"] is False
    assert row["delivery_due_date"]  # parsed from /Date(ms)/ to ISO
    assert "-" in row["po_issued_date"]


async def test_vendor_performance_is_labelled_simulated(canned):
    canned["A_Supplier"] = [{"PurchasingIsBlocked": True, "SupplierName": "ACME"}]
    res = await s4_client.get_vendor_delivery_performance(supplier_lifnr="17300001")
    assert res["signal_status"] == "simulated"          # never presented as live
    assert res["value"][0]["supplier_delivery_risk_score"] == 90   # blocked -> high


async def test_date_parser():
    assert s4_client._parse_date("/Date(1470268800000)/") == "2016-08-04"
    assert s4_client._parse_date("") == ""


def test_accelerator_hub_tools_wire_real_and_mock():
    from app import tools
    ah = {t.name: t for t in tools.build_accelerator_hub_tools()}
    assert ah["get_open_pr_po_chain"].ord_id == "accelerator-hub"          # real
    assert ah["link_po_to_project_wbs"].ord_id != "accelerator-hub"        # stays mock (no PS API)
    assert "write_decision_record" in ah                                   # in-process retained


def test_auth_mode_none_bypasses_with_warning(monkeypatch):
    monkeypatch.delenv("IBD_TESTING", raising=False)
    monkeypatch.setenv("AGENT_AUTH_MODE", "none")
    from app.agent_executor import validate_identity
    assert validate_identity({}) == "dev-bypass-user"   # no token needed in dev bypass
