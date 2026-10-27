"""Project-data boundary — SAP Project System (live) **and** a Phase-1 Excel/CSV adapter.

Both procurement agents must accept project material-requirement / schedule data
from SAP **or** from a structured Excel/CSV upload (customer requirement). This
module hides that choice behind one interface (`load_project_activities`) so the
rest of the agent is identical whichever source is active:

* ``SAP_PS``   — read PRPS / AFKO / AFVV / MLST via OData/CDS/RFC (Phase 2 target).
                 Live reads happen through the MCP tool layer; this module shapes
                 the result into ``ProjectActivity`` records.
* ``EXCEL``    — Phase-1 structured workbook / CSV maintained by the PMO.
* ``MOCK``     — deterministic fixtures for offline tests/demos.

The Excel path uses ``openpyxl`` when available and falls back to CSV (stdlib
``csv``) so the module imports and runs with no third-party dependency.
"""
from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass, asdict
from typing import Any

from . import config

# Agreed Phase-1 Excel/CSV template (header row). Material numbers must match the
# S/4HANA material master exactly; dates ISO (YYYY-MM-DD).
EXCEL_TEMPLATE_COLUMNS = [
    "project_code",       # PSPHI / project definition
    "wbs_element",        # PRPS.POSID
    "activity_id",        # AFVV.VORNR
    "material_number",    # must match S/4HANA MATNR exactly
    "required_qty",
    "uom",
    "required_date",      # activity requirement date (ISO)
    "available_float_days",  # AFVV: EFAVD - SSAVD
    "po_reference",       # linked PO (EBELN) if known
    "milestone_id",       # MLST.MSVNR
    "milestone_payment_eur",
    "milestone_currency",
    "resource_teams",     # count of teams blocked if the activity slips
    "daily_team_cost_rate_eur",
    "responsible_person",  # PRPS.VERNR → PM notification routing
]


@dataclass
class ProjectActivity:
    project_code: str
    wbs_element: str
    activity_id: str
    material_number: str
    required_qty: float
    uom: str
    required_date: str
    available_float_days: int
    po_reference: str
    milestone_id: str
    milestone_payment_eur: float
    milestone_currency: str
    resource_teams: int
    daily_team_cost_rate_eur: float
    responsible_person: str
    source: str = "MOCK"  # provenance stamp: SAP_PS | EXCEL | MOCK

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def project_data_mode() -> str:
    """Resolve the active source. Mock always wins; else PROJECT_DATA_SOURCE env."""
    if config.is_mock_mode():
        return "MOCK"
    return os.environ.get("PROJECT_DATA_SOURCE", "SAP_PS").upper()


# --- deterministic offline fixtures ----------------------------------------
def _mock_activities() -> list[ProjectActivity]:
    return [
        ProjectActivity(
            project_code="P-INFRA-07", wbs_element="P-INFRA-07.1.3",
            activity_id="0040", material_number="MAT-STRUCT-STEEL-01",
            required_qty=120.0, uom="TO", required_date="2026-10-24",
            available_float_days=0, po_reference="4500000123",
            milestone_id="MS-L3-SLAB", milestone_payment_eur=250_000.0,
            milestone_currency="EUR", resource_teams=2, daily_team_cost_rate_eur=8_500.0,
            responsible_person="PM-ANDERSON", source="MOCK",
        ),
        ProjectActivity(
            project_code="P-INFRA-07", wbs_element="P-INFRA-07.1.4",
            activity_id="0050", material_number="MAT-REBAR-16MM",
            required_qty=40.0, uom="TO", required_date="2026-11-02",
            available_float_days=6, po_reference="4500000124",
            milestone_id="MS-L3-SLAB", milestone_payment_eur=250_000.0,
            milestone_currency="EUR", resource_teams=1, daily_team_cost_rate_eur=6_200.0,
            responsible_person="PM-ANDERSON", source="MOCK",
        ),
    ]


# --- Excel / CSV adapter ----------------------------------------------------
def _coerce(row: dict[str, str]) -> ProjectActivity:
    def f(key: str, default: float = 0.0) -> float:
        try:
            return float(str(row.get(key, "")).strip() or default)
        except ValueError:
            return default

    def i(key: str, default: int = 0) -> int:
        return int(f(key, default))

    return ProjectActivity(
        project_code=str(row.get("project_code", "")).strip(),
        wbs_element=str(row.get("wbs_element", "")).strip(),
        activity_id=str(row.get("activity_id", "")).strip(),
        material_number=str(row.get("material_number", "")).strip(),
        required_qty=f("required_qty"),
        uom=str(row.get("uom", "")).strip(),
        required_date=str(row.get("required_date", "")).strip(),
        available_float_days=i("available_float_days"),
        po_reference=str(row.get("po_reference", "")).strip(),
        milestone_id=str(row.get("milestone_id", "")).strip(),
        milestone_payment_eur=f("milestone_payment_eur"),
        milestone_currency=str(row.get("milestone_currency", "EUR")).strip() or "EUR",
        resource_teams=i("resource_teams"),
        daily_team_cost_rate_eur=f("daily_team_cost_rate_eur"),
        responsible_person=str(row.get("responsible_person", "")).strip(),
        source="EXCEL",
    )


def load_from_csv_text(text: str) -> list[ProjectActivity]:
    """Parse the Phase-1 CSV template text into activities (stdlib only)."""
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in ("project_code", "wbs_element", "material_number", "required_date")
               if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"Excel/CSV template missing required columns: {missing}")
    return [_coerce(row) for row in reader]


def load_from_excel(path: str) -> list[ProjectActivity]:
    """Parse the Phase-1 workbook. Uses openpyxl if present; otherwise expects CSV."""
    if path.lower().endswith(".csv"):
        with open(path, "r", encoding="utf-8-sig") as fh:
            return load_from_csv_text(fh.read())
    try:
        from openpyxl import load_workbook  # type: ignore
    except Exception as exc:  # pragma: no cover - only when openpyxl absent + .xlsx given
        raise RuntimeError(
            "openpyxl is required to read .xlsx project files; install it or supply CSV."
        ) from exc
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    out = [_coerce({header[i]: ("" if v is None else str(v)) for i, v in enumerate(r)})
           for r in rows[1:]]
    return out


def load_project_activities(
    *, excel_path: str | None = None, sap_ps_rows: list[dict[str, Any]] | None = None
) -> list[ProjectActivity]:
    """Load project activities from the active source.

    * MOCK   → deterministic fixtures.
    * EXCEL  → ``excel_path`` (or ``PROJECT_DATA_EXCEL_PATH`` env).
    * SAP_PS → ``sap_ps_rows`` shaped from the PS MCP tool read.
    """
    mode = project_data_mode()
    if mode == "MOCK":
        return _mock_activities()
    if mode == "EXCEL":
        path = excel_path or os.environ.get("PROJECT_DATA_EXCEL_PATH")
        if not path:
            raise ValueError("PROJECT_DATA_SOURCE=EXCEL but no PROJECT_DATA_EXCEL_PATH provided.")
        return load_from_excel(path)
    # SAP_PS
    rows = sap_ps_rows or []
    acts = [_coerce(r) for r in rows]
    for a in acts:
        a.source = "SAP_PS"
    return acts
