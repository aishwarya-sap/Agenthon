"""Data fixtures + catalog consistency (asset.yaml / mcp-mock.json <-> tools)."""
import json
from pathlib import Path

import tools as tool_mod
from domain import data

_AGENT_ROOT = Path(__file__).resolve().parent.parent


def test_excel_template_columns_present():
    cols = data.EXCEL_TEMPLATE_COLUMNS
    for required in ("Project ID", "Activity ID", "Material Number", "Required Quantity",
                     "Required Date", "Float (days)"):
        assert required in cols


def test_seed_scenario_shape():
    acts = data.get_activities(project_id="P-ALPHA-01")
    assert len(acts) == 4
    steel = data.get_activities(material="1000234")[0]
    assert steel["float_days"] == -3 and steel["required_date"] == "2026-10-16"
    gr = data.get_gr_history("1001", "1000234")
    assert [g["delay_days"] for g in gr] == [8, 8, 12, 9]


def test_mock_catalog_matches_registered_tools():
    catalog = json.loads((_AGENT_ROOT / "mcp-mock.json").read_text())
    cat_tools = set()
    side_effect_in_catalog = set()
    for server in catalog["servers"].values():
        for name, spec in server["tools"].items():
            cat_tools.add(name)
            if spec.get("side_effect"):
                side_effect_in_catalog.add(name)
    assert cat_tools == set(tool_mod.TOOL_NAMES)
    # the 3 write tools are the side-effecting ones in both catalog and code
    from domain import hitl
    assert side_effect_in_catalog == set(hitl.BLOCKED_TOOLS)


def test_ord_ids_align_between_catalog_and_asset():
    catalog = json.loads((_AGENT_ROOT / "mcp-mock.json").read_text())
    ords = {s["mcp_server_name"] for s in catalog["servers"].values()}
    asset_text = (_AGENT_ROOT / "asset.yaml").read_text()
    for ord_id in ords:
        assert ord_id in asset_text, f"ORD id {ord_id} missing from asset.yaml requires[]"
