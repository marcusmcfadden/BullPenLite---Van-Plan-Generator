import csv
import io
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import urllib.error
import urllib.parse
import urllib.request

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def get_csv_reader(source: str):
    source = source.strip()
    if "docs.google.com/spreadsheets" in source:
        match_id = re.search(r"/d/([a-zA-Z0-9-_]+)", source)
        if not match_id:
            raise ValueError("Invalid Google Sheets URL.")
        sheet_id = match_id.group(1)

        match_gid = re.search(r"[#&?]gid=([0-9]+)", source)
        urls_to_try = []

        if match_gid:
            gid = match_gid.group(1)
            urls_to_try.append(
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"
            )
            urls_to_try.append(
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            )
        else:
            urls_to_try.append(
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=LAB%20Van%20Plan"
            )
            urls_to_try.append(
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid=0"
            )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
        }
        content = None
        for u in urls_to_try:
            try:
                req = urllib.request.Request(u, headers=headers)
                with urllib.request.urlopen(req) as resp:
                    content = resp.read().decode("utf-8", errors="replace")
                    break
            except Exception:
                continue

        if not content:
            raise ConnectionError(
                "Could not access Google Sheet. Check link-sharing permissions or internet connection."
            )

        return csv.reader(io.StringIO(content))
    else:
        # Local offline CSV file
        clean_path = source.strip("\"'")
        f = open(clean_path, "r", encoding="utf-8", errors="replace")
        return csv.reader(f)


def parse_van_plan_csv(reader):
    categories = {
        "Battalion": [],
        "NCCU": [],
        "Home Depot": [],
        "Leaving Early": [],
        "Arriving Late": [],
        "Not Coming": [],
        "Unaccounted": [],
        "Requires Update": [],
    }

    for row in reader:
        if not row or not row[0].strip():
            continue

        cadet = row[0].strip()

        if any(
            cadet.startswith(k)
            for k in [
                "1st Squad",
                "2nd Squad",
                "3rd Squad",
                "4th Squad",
                "MS4s",
                "Total",
            ]
        ):
            continue

        if cadet.lower() == "page":
            continue

        is_duke = len(row) > 1 and row[1].strip().upper() == "TRUE"
        is_nccu = len(row) > 2 and row[2].strip().upper() == "TRUE"
        is_hd = len(row) > 3 and row[3].strip().upper() == "TRUE"
        is_early = len(row) > 4 and row[4].strip().upper() == "TRUE"
        is_late = len(row) > 5 and row[5].strip().upper() == "TRUE"
        is_not_coming = len(row) > 6 and row[6].strip().upper() == "TRUE"

        time_note = row[7].strip() if len(row) > 7 else ""

        if is_late and not time_note:
            categories["Requires Update"].append(
                f"{cadet} (Late: No Time Disclosed)"
            )
            late_entry = f"{cadet} (NO TIME DISCLOSED)"
        else:
            late_entry = f"{cadet} ({time_note})" if time_note else cadet

        if is_early and not time_note:
            categories["Requires Update"].append(
                f"{cadet} (Early: No Time Disclosed)"
            )
            early_entry = f"{cadet} (NO TIME DISCLOSED)"
        else:
            early_entry = f"{cadet} ({time_note})" if time_note else cadet

        big_three = []
        if is_duke:
            big_three.append("Battalion")
        if is_nccu:
            big_three.append("NCCU")
        if is_hd:
            big_three.append("Home Depot")

        # Failsafe 3: Multiple Big Three
        if len(big_three) > 1:
            categories["Requires Update"].append(
                f"{cadet} (Selected: {', '.join(big_three)})"
            )
            if is_late:
                categories["Arriving Late"].append(late_entry)
            if is_early:
                categories["Leaving Early"].append(early_entry)
            continue

        # Failsafe 1 & 2: Single Big Three
        if len(big_three) == 1:
            sp = big_three[0]
            if is_late:
                categories["Arriving Late"].append(late_entry)
            else:
                categories[sp].append(cadet)

            if is_early:
                categories["Leaving Early"].append(early_entry)
            continue

        # None of Big Three
        handled = False
        if is_late:
            categories["Arriving Late"].append(late_entry)
            handled = True
        if is_early:
            categories["Leaving Early"].append(early_entry)
            handled = True
        if is_not_coming:
            categories["Not Coming"].append(cadet)
            handled = True

        if not handled:
            categories["Unaccounted"].append(cadet)

    return categories


def generate_van_plan_pdf(categories, lab_date: str, output_dir: str = "."):
    safe_date = re.sub(r"[^\w\-.]", "_", lab_date.strip())
    output_filename = os.path.join(output_dir, f"BCB_Van_Plan_{safe_date}.pdf")

    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=20,
        bottomMargin=20,
    )

    styles = getSampleStyleSheet()

    DUKE_BLUE = colors.HexColor("#003087")
    NCCU_MAROON = colors.HexColor("#862633")
    HOMEDEPOT_ORANGE = colors.HexColor("#F96302")
    GRAY_HEADER = colors.HexColor("#4A5568")
    NOT_COMING_GRAY = colors.HexColor("#4A5568")
    UNACCOUNTED_RED = colors.HexColor("#9B2C2C")
    UPDATE_PURPLE = colors.HexColor("#6B46C1")
    LATE_BLUE = colors.HexColor("#2B6CB0")
    EARLY_ORANGE = colors.HexColor("#C05621")
    BLACK = colors.HexColor("#000000")
    WHITE = colors.HexColor("#FFFFFF")

    def badge(count, label="CADETS"):
        return f"""<font color="black" backcolor="#FEFCBF"><b>&nbsp;{count} {label}&nbsp;</b></font>"""

    title_style = ParagraphStyle(
        "CenteredTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        alignment=TA_CENTER,
        textColor=BLACK,
    )
    col_header_style = ParagraphStyle(
        "ColHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=WHITE,
    )
    num_header_style = ParagraphStyle(
        "NumHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8.5,
        alignment=TA_CENTER,
        textColor=WHITE,
    )
    cell_num_style = ParagraphStyle(
        "CellNum",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=5,
        leading=6.5,
        alignment=TA_CENTER,
        textColor=BLACK,
    )
    cell_text_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=8,
        alignment=TA_LEFT,
        textColor=BLACK,
    )
    section_head_style = ParagraphStyle(
        "SectionHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        alignment=TA_CENTER,
        textColor=WHITE,
    )

    story = [
        Paragraph(
            f"VAN PLAN — BULL CITY BATTALION ({lab_date.upper()})", title_style
        ),
        Spacer(1, 4),
    ]

    bldg = categories.get("Battalion", [])
    nccu = categories.get("NCCU", [])
    hd = categories.get("Home Depot", [])
    max_rows = max(len(bldg), len(nccu), len(hd), 1)

    h1 = f"BATTALION BLDG @ 1330<br/>({badge(len(bldg))})"
    h2 = f"NCCU BOOK STORE @ 1330<br/>({badge(len(nccu))})"
    h3 = f"HOME DEPOT @ 1400<br/>({badge(len(hd))})"

    col_widths = [18, 174, 174, 174]
    main_table_data = [[
        Paragraph("#", num_header_style),
        Paragraph(h1, col_header_style),
        Paragraph(h2, col_header_style),
        Paragraph(h3, col_header_style),
    ]]

    for i in range(max_rows):
        c1 = bldg[i] if i < len(bldg) else ""
        c2 = nccu[i] if i < len(nccu) else ""
        c3 = hd[i] if i < len(hd) else ""
        main_table_data.append([
            Paragraph(str(i + 1), cell_num_style),
            Paragraph(c1, cell_text_style),
            Paragraph(c2, cell_text_style),
            Paragraph(c3, cell_text_style),
        ])

    main_table = Table(main_table_data, colWidths=col_widths, repeatRows=1)
    main_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), GRAY_HEADER),
            ("BACKGROUND", (1, 0), (1, 0), DUKE_BLUE),
            ("BACKGROUND", (2, 0), (2, 0), NCCU_MAROON),
            ("BACKGROUND", (3, 0), (3, 0), HOMEDEPOT_ORANGE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("PADDING", (0, 0), (-1, -1), 1.0),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.HexColor("#FFFFFF"), colors.HexColor("#F7FAFC")],
            ),
        ])
    )
    story.append(main_table)
    story.append(Spacer(1, 4))

    # Unified Late & Early Table
    late = categories.get("Arriving Late", [])
    early = categories.get("Leaving Early", [])
    bottom_pair_rows = max(len(late), len(early), 1)

    late_head = f"ARRIVING LATE ({badge(len(late))})"
    early_label = "CADET" if len(early) == 1 else "CADETS"
    early_head = f"LEAVING EARLY ({badge(len(early), early_label)})"

    pair_data = [[
        Paragraph(late_head, section_head_style),
        Paragraph(early_head, section_head_style),
    ]]

    for i in range(bottom_pair_rows):
        l_val = late[i] if i < len(late) else ""
        e_val = early[i] if i < len(early) else ""
        pair_data.append([
            Paragraph(l_val, cell_text_style),
            Paragraph(e_val, cell_text_style),
        ])

    pair_table = Table(pair_data, colWidths=[270, 270])
    pair_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), LATE_BLUE),
            ("BACKGROUND", (1, 0), (1, 0), EARLY_ORANGE),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("PADDING", (0, 0), (-1, -1), 1.2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.HexColor("#FFFFFF"), colors.HexColor("#F7FAFC")],
            ),
        ])
    )
    story.append(pair_table)
    story.append(Spacer(1, 4))

    # Grid tables
    def make_cell_grid_table(title, items, header_color, num_cols=4):
        b_tag = badge(len(items))
        header_row = [
            Paragraph(f"{title} ({b_tag})", section_head_style)
        ] + [""] * (num_cols - 1)
        data = [header_row]
        col_w = 540 / num_cols
        if not items:
            row = [Paragraph("None", cell_text_style)] + [""] * (num_cols - 1)
            data.append(row)
        else:
            for r_idx in range(0, len(items), num_cols):
                chunk = items[r_idx : r_idx + num_cols]
                row = [Paragraph(name, cell_text_style) for name in chunk]
                while len(row) < num_cols:
                    row.append(Paragraph("", cell_text_style))
                data.append(row)

        t = Table(data, colWidths=[col_w] * num_cols)
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), header_color),
                ("SPAN", (0, 0), (-1, 0)),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("PADDING", (0, 0), (-1, -1), 1.2),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#FFFFFF"), colors.HexColor("#F7FAFC")],
                ),
            ])
        )
        return t

    not_coming = categories.get("Not Coming", [])
    unaccounted = categories.get("Unaccounted", [])
    req_update = categories.get("Requires Update", [])

    nc_table = make_cell_grid_table(
        "NOT COMING", not_coming, NOT_COMING_GRAY, num_cols=4
    )
    story.append(nc_table)
    story.append(Spacer(1, 4))

    unacc_table = make_cell_grid_table(
        "UNACCOUNTED / MISSING", unaccounted, UNACCOUNTED_RED, num_cols=4
    )
    story.append(unacc_table)

    if req_update:
        story.append(Spacer(1, 4))
        update_table = make_cell_grid_table(
            "REQUIRES UPDATE (ACTION REQUIRED)",
            req_update,
            UPDATE_PURPLE,
            num_cols=2,
        )
        story.append(update_table)

    doc.build(story)
    return output_filename


def run_gui():
    root = tk.Tk()
    root.withdraw()  # Hide root window

    # 1. Ask user for Google Sheet link or file
    choice = messagebox.askyesno(
        "BCB Van Plan Generator",
        "Do you want to import directly from a Google Sheet URL?\n\n(Click 'No' to pick an offline CSV file)",
    )

    source = None
    if choice:
        source = simpledialog.askstring(
            "Google Sheets Link",
            "Paste the Google Sheets URL for this week's Van Plan:\n(Include #gid=... if multi-tab)",
        )
        if not source:
            return
    else:
        source = filedialog.askopenfilename(
            title="Select Van Plan Attendance CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if not source:
            return

    # 2. Ask for the Lab Date
    lab_date = simpledialog.askstring(
        "LAB Date",
        "Enter the Date of LAB (e.g., 23SEP2026):",
        initialvalue="23SEP2026",
    )
    if not lab_date:
        lab_date = "LAB_MANIFEST"

    try:
        reader = get_csv_reader(source)
        data = parse_van_plan_csv(reader)
        # Determine executable folder to save PDF right next to the .exe
        target_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        pdf_path = generate_van_plan_pdf(data, lab_date, output_dir=target_dir)

        messagebox.showinfo(
            "Success!", f"Manifest generated successfully:\n\n{os.path.basename(pdf_path)}"
        )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate manifest:\n\n{str(e)}")


if __name__ == "__main__":
    run_gui()