from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from scheduler.cli import build_report
from scheduler.models import OFF, ScheduleRequest
from scheduler.solver import solve_schedule

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="Hospital Schedule Studio", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _request(data: dict[str, Any]) -> ScheduleRequest:
    return ScheduleRequest.from_dict(data)


def _payload(request: ScheduleRequest, result: Any) -> dict[str, Any]:
    return {
        "report": build_report(request, result),
        "periods": [
            {"id": period.id, "label": period.label} for period in request.periods
        ],
        "staff": [
            {"id": member.id, "name": member.name} for member in request.staff
        ],
        "assignments": result.assignments,
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/solve")
def solve(data: dict[str, Any]) -> JSONResponse:
    try:
        request = _request(data)
        result = solve_schedule(request)
        return JSONResponse(_payload(request, result))
    except (KeyError, TypeError, ValueError) as error:
        return JSONResponse(
            {
                "report": {
                    "status": "INVALID_INPUT",
                    "success": False,
                    "diagnostics": [str(error)],
                    "validation_errors": [],
                },
                "assignments": {},
                "periods": [],
                "staff": [],
            },
            status_code=400,
        )


@app.post("/api/export/xlsx")
def export_xlsx(data: dict[str, Any]) -> StreamingResponse:
    request = _request(data["request"])
    assignments: dict[str, dict[str, str]] = data["assignments"]
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Schedule"
    sheet.freeze_panes = "B2"

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    sheet.append(["Staff member", *(period.label for period in request.periods)])
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    palette = {
        OFF: "E7E6E6",
        "CTU": "D9EAD3",
        "Inpatient": "CFE2F3",
        "Clinic": "FFF2CC",
        "ER": "F4CCCC",
        "Consult": "D9D2E9",
        "Holiday Coverage": "FCE5CD",
    }
    for member in request.staff:
        row = [member.name]
        for period in request.periods:
            role = assignments[period.id][member.id]
            row.append("X" if role == OFF else role)
        sheet.append(row)
        for column, role in enumerate(row[1:], start=2):
            color = palette.get(OFF if role == "X" else role, "FFFFFF")
            sheet.cell(sheet.max_row, column).fill = PatternFill(
                "solid", fgColor=color
            )
            sheet.cell(sheet.max_row, column).alignment = Alignment(
                horizontal="center", vertical="center"
            )

    sheet.column_dimensions["A"].width = 24
    for column in range(2, len(request.periods) + 2):
        sheet.column_dimensions[sheet.cell(1, column).column_letter].width = 15
    sheet.auto_filter.ref = sheet.dimensions

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": 'attachment; filename="schedule.xlsx"'},
    )
