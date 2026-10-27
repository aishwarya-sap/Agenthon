"""Project-data boundary tests: SAP PS shaping, Excel/CSV adapter, mode resolution."""
import os

import pytest

from app import project_data as pd

pytestmark = pytest.mark.unit


def test_mock_mode_returns_fixtures():
    acts = pd.load_project_activities()  # IBD_TESTING=1 -> MOCK
    assert len(acts) == 2
    assert acts[0].material_number == "MAT-STRUCT-STEEL-01"
    assert acts[0].source == "MOCK"


def test_csv_adapter_parses_template():
    header = ",".join(pd.EXCEL_TEMPLATE_COLUMNS)
    row = "P-INFRA-07,P-INFRA-07.1.3,0040,MAT-STRUCT-STEEL-01,120,TO,2026-10-24,0,4500000123,MS-L3-SLAB,250000,EUR,2,8500,PM-ANDERSON"
    acts = pd.load_from_csv_text(header + "\n" + row)
    assert acts[0].milestone_payment_eur == 250000.0
    assert acts[0].resource_teams == 2
    assert acts[0].source == "EXCEL"


def test_csv_missing_required_columns_raises():
    with pytest.raises(ValueError):
        pd.load_from_csv_text("foo,bar\n1,2")


def test_sap_ps_rows_shaped_with_provenance(monkeypatch):
    monkeypatch.delenv("IBD_TESTING", raising=False)
    monkeypatch.setenv("PROJECT_DATA_SOURCE", "SAP_PS")
    rows = [{"project_code": "P1", "wbs_element": "P1.1", "material_number": "M1",
             "required_date": "2026-10-24", "available_float_days": "0"}]
    acts = pd.load_project_activities(sap_ps_rows=rows)
    assert acts[0].source == "SAP_PS"
    monkeypatch.setenv("IBD_TESTING", "1")


def test_excel_mode_without_path_raises(monkeypatch):
    monkeypatch.delenv("IBD_TESTING", raising=False)
    monkeypatch.setenv("PROJECT_DATA_SOURCE", "EXCEL")
    monkeypatch.delenv("PROJECT_DATA_EXCEL_PATH", raising=False)
    with pytest.raises(ValueError):
        pd.load_project_activities()
    monkeypatch.setenv("IBD_TESTING", "1")
