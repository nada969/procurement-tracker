"""Excel export: one leveled comparison sheet per package (+ notes), and a project summary."""
import re
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

FONT = "Arial"
HDR = PatternFill("solid", fgColor="1F3864")
GREY = PatternFill("solid", fgColor="E7E6E6")
GREEN = PatternFill("solid", fgColor="D9EAD3")
LABEL = PatternFill("solid", fgColor="F2F2F2")
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
MONEY, PCT = '$#,##0;($#,##0);"-"', '0%;-0%;0%'

def f(bold=False, color="000000", size=10, italic=False):
    return Font(name=FONT, bold=bold, color=color, size=size, italic=italic)

def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "-", s or "").strip("-") or "export"

def sheet_title(name, used):
    base = re.sub(r"[\[\]\*\?/\\:]", "-", name or "Package")[:31] or "Package"
    t, i = base, 2
    while t.lower() in used:
        t = f"{base[:28]}-{i}"; i += 1
    used.add(t.lower())
    return t

def print_setup(ws):
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)

def package_status(sups):
    if any(s["stage"] == "Awarded" for s in sups): return "Awarded"
    if any(s["tech"] == "Compliant" for s in sups): return "Evaluating"
    return "Open"

def write_package_sheet(ws, project_name, pkg, sups, notes, supplier_names):
    ws.sheet_view.showGridLines = False
    ws["A1"] = f"{project_name}  |  {pkg['name']}"; ws["A1"].font = f(True, size=14)
    ws["A2"] = f"Exported {date.today().isoformat()}"; ws["A2"].font = f(italic=True, color="595959", size=9)
    ss = sorted(sups, key=lambda s: (s["total"] is None, s["total"] or 0, s["name"]))
    n = max(len(ss), 1)
    last = get_column_letter(1 + n)
    # summary block (budget is an input; the rest are formulas)
    ws["A4"], ws["B4"] = "Budget (USD)", pkg.get("budget")
    ws["A5"], ws["B5"] = "Required on site", pkg.get("ros") or ""
    ws["A6"] = "Lowest compliant bid (USD)"
    ws["B6"] = f'=IF(COUNTIFS(B10:{last}10,"Compliant",B12:{last}12,">0")=0,"",_xlfn.MINIFS(B12:{last}12,B10:{last}10,"Compliant",B12:{last}12,">0"))'
    ws["A7"] = "Lowest compliant vs budget"
    ws["B7"] = '=IF(AND(ISNUMBER(B6),N(B4)>0),B6/B4-1,"")'
    for r in range(4, 8):
        ws[f"A{r}"].font = f(True); ws[f"A{r}"].fill = LABEL; ws[f"A{r}"].border = BORDER
        ws[f"B{r}"].border = BORDER; ws[f"B{r}"].alignment = Alignment(horizontal="left")
    ws["B4"].font = f(color="0000FF"); ws["B4"].number_format = MONEY
    ws["B5"].font = f(color="0000FF")
    ws["B6"].font = f(); ws["B6"].number_format = MONEY
    ws["B7"].font = f(); ws["B7"].number_format = PCT
    # comparison matrix
    labels = ["Technical status", "Commercial stage", "Bid total (USD)", "vs budget", "Lead time (weeks)",
              "Incoterm / delivery", "Payment terms", "Next action", "Next action due", "Technical note"]
    ws["A9"] = "Supplier"; ws["A9"].font = f(True, "FFFFFF"); ws["A9"].fill = HDR; ws["A9"].border = BORDER
    for i, r in enumerate(range(10, 20)):
        c = ws.cell(row=r, column=1, value=labels[i]); c.font = f(True); c.fill = LABEL; c.border = BORDER
    ok = [s for s in ss if s["tech"] == "Compliant"]
    min_t = min([s["total"] for s in ok if s["total"]], default=None)
    min_l = min([s["leadWeeks"] for s in ok if s["leadWeeks"] is not None], default=None)
    for j, s in enumerate(ss):
        col = get_column_letter(2 + j)
        grey = s["tech"] != "Compliant"
        vals = [s["tech"], s["stage"], s["total"], f'=IF(AND(ISNUMBER({col}12),N($B$4)>0),{col}12/$B$4-1,"")',
                s["leadWeeks"], s["incoterm"], s["payment"], s["nextAction"], s["due"], s["reason"]]
        h = ws[f"{col}9"]; h.value = s["name"]; h.font = f(True, "FFFFFF"); h.fill = HDR; h.border = BORDER
        h.alignment = Alignment(wrap_text=True, vertical="center")
        for i, v in enumerate(vals):
            c = ws.cell(row=10 + i, column=2 + j, value=v if v != "" else None)
            c.font = f(color="7F7F7F" if grey else "000000"); c.border = BORDER
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if grey: c.fill = GREY
        ws[f"{col}12"].number_format = MONEY; ws[f"{col}13"].number_format = PCT
        if not grey and s["total"] and s["total"] == min_t: ws[f"{col}12"].fill = GREEN; ws[f"{col}12"].font = f(True, "18794E")
        if not grey and s["leadWeeks"] is not None and s["leadWeeks"] == min_l: ws[f"{col}14"].fill = GREEN; ws[f"{col}14"].font = f(True, "18794E")
    if ss:
        ws.conditional_formatting.add(f"B13:{last}13", CellIsRule(operator="greaterThan", formula=["0"], font=Font(name=FONT, color="B42318")))
    else:
        ws["B10"] = "No suppliers yet"; ws["B10"].font = f(italic=True, color="7F7F7F")
    ws.cell(row=21, column=1, value="Grey columns are not technically compliant. Green marks the best compliant value.").font = f(italic=True, color="595959", size=9)
    # notes log
    r = 23
    ws.cell(row=r, column=1, value="Notes log").font = f(True, size=12)
    r += 1
    for i, h in enumerate(["Date", "About", "Note"]):
        c = ws.cell(row=r, column=1 + i, value=h); c.font = f(True, "FFFFFF"); c.fill = HDR; c.border = BORDER
    ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=max(7, 1 + n))
    end_col = max(7, 1 + n)
    mine = sorted(notes, key=lambda x: x["createdAt"] or "", reverse=True)
    if not mine:
        ws.cell(row=r + 1, column=1, value="No notes yet").font = f(italic=True, color="7F7F7F")
    for x in mine:
        r += 1
        ws.cell(row=r, column=1, value=(x["createdAt"] or "")[:16].replace("T", " ")).font = f()
        ws.cell(row=r, column=2, value=supplier_names.get(x["supplierId"], "Whole package")).font = f()
        c = ws.cell(row=r, column=3, value=x["body"]); c.font = f(); c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=end_col)
        for k in (1, 2): ws.cell(row=r, column=k).alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[r].height = max(15, 15 * (len(x["body"]) // 95 + 1 + x["body"].count("\n")))
    ws.column_dimensions["A"].width = 28
    for j in range(n): ws.column_dimensions[get_column_letter(2 + j)].width = 24
    ws.row_dimensions[9].height = 30
    ws.freeze_panes = "B10"
    print_setup(ws)

def _data(snap, pkg_id):
    sups = [s for s in snap["suppliers"] if s["packageId"] == pkg_id]
    notes = [n for n in snap.get("notes", []) if n["packageId"] == pkg_id]
    names = {s["id"]: s["name"] for s in sups}
    return sups, notes, names

def package_workbook(snap, pkg_id):
    pkg = next(k for k in snap["packages"] if k["id"] == pkg_id)
    project = next(p for p in snap["projects"] if p["id"] == pkg["projectId"])
    wb = Workbook(); ws = wb.active; ws.title = sheet_title(pkg["name"], set())
    sups, notes, names = _data(snap, pkg_id)
    write_package_sheet(ws, project["name"], pkg, sups, notes, names)
    wb.calculation.fullCalcOnLoad = True
    return wb, f"{slug(project['name'])}-{slug(pkg['name'])}.xlsx"

def project_workbook(snap, project_id):
    project = next(p for p in snap["projects"] if p["id"] == project_id)
    pkgs = sorted([k for k in snap["packages"] if k["projectId"] == project_id], key=lambda k: k["name"])
    wb = Workbook(); ws = wb.active; ws.title = "Summary"; ws.sheet_view.showGridLines = False
    ws["A1"] = project["name"]; ws["A1"].font = f(True, size=14)
    ws["A2"] = f"{project.get('client') or ''}  |  Exported {date.today().isoformat()}"; ws["A2"].font = f(italic=True, color="595959", size=9)
    heads = ["Package", "Status", "Budget (USD)", "Suppliers", "Compliant", "Lowest compliant (USD)", "Supplier", "vs budget", "Required on site"]
    for i, h in enumerate(heads, 1):
        c = ws.cell(row=4, column=i, value=h); c.font = f(True, "FFFFFF"); c.fill = HDR; c.border = BORDER
        c.alignment = Alignment(wrap_text=True, vertical="center")
    used = {"summary"}; r = 4; first = 5
    for k in pkgs:
        sups, notes, names = _data(snap, k["id"])
        ok = sorted([s for s in sups if s["tech"] == "Compliant" and s["total"]], key=lambda s: s["total"])
        best = ok[0] if ok else None
        r += 1
        row = [k["name"], package_status(sups), k.get("budget"), len(sups), sum(1 for s in sups if s["tech"] == "Compliant"),
               best["total"] if best else None, best["name"] if best else "",
               f'=IF(AND(ISNUMBER(F{r}),N(C{r})>0),F{r}/C{r}-1,"")', k.get("ros") or ""]
        for i, v in enumerate(row, 1):
            c = ws.cell(row=r, column=i, value=v if v != "" else None); c.border = BORDER; c.font = f(i == 1)
        ws.cell(row=r, column=3).font = f(color="0000FF")
        ws.cell(row=r, column=3).number_format = ws.cell(row=r, column=6).number_format = MONEY
        ws.cell(row=r, column=8).number_format = PCT
        sh = wb.create_sheet(sheet_title(k["name"], used))
        write_package_sheet(sh, project["name"], k, sups, notes, names)
    if pkgs:
        t = r + 1
        ws.cell(row=t, column=1, value="Total").font = f(True)
        for col in (3, 4, 5, 6):
            L = get_column_letter(col)
            c = ws.cell(row=t, column=col, value=f"=SUM({L}{first}:{L}{r})"); c.font = f(True)
            c.number_format = MONEY if col in (3, 6) else "0"
        ws.cell(row=t, column=8, value=f'=IF(AND(COUNT(F{first}:F{r})=ROWS(A{first}:A{r}),N(C{t})>0),F{t}/C{t}-1,"")').number_format = PCT
        ws.cell(row=t, column=8).font = f(True)
        for col in range(1, 10): ws.cell(row=t, column=col).border = BORDER
        ws.cell(row=t + 2, column=1, value="Total vs budget is shown only when every package has a compliant bid.").font = f(italic=True, color="595959", size=9)
        ws.conditional_formatting.add(f"H{first}:H{t}", CellIsRule(operator="greaterThan", formula=["0"], font=Font(name=FONT, color="B42318")))
    else:
        ws["A5"] = "No packages yet"; ws["A5"].font = f(italic=True, color="7F7F7F")
    for col, w in zip("ABCDEFGHI", [26, 14, 16, 11, 11, 22, 24, 12, 18]): ws.column_dimensions[col].width = w
    ws.row_dimensions[4].height = 30; ws.freeze_panes = "A5"; print_setup(ws)
    wb.calculation.fullCalcOnLoad = True
    return wb, f"{slug(project['name'])}-summary.xlsx"

def to_bytes(wb):
    buf = BytesIO(); wb.save(buf); return buf.getvalue()
