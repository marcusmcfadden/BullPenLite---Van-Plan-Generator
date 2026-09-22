# Bull City Battalion — LAB Van Plan Generator

Lightweight desktop tool to parse weekly cadet attendance sheets and compile single-page transportation manifests for LAB movements.

---

## Download (.exe)
No Python or installation required:
1. Go to **[Releases](../../releases)** on the right sidebar.
2. Download `BCB_Van_Plan_Generator.exe`.
3. Double-click to run.

---

## How to Use

1. **Double-click `BCB_Van_Plan_Generator.exe`**.
2. **Select Input Mode**:
   - **Google Sheets (Default)**: Paste the browser URL of this week's attendance sheet (make sure it includes `#gid=...` if it's a multi-tab workbook).
   - **Offline CSV**: Select a downloaded `.csv` file.
3. **Enter LAB Date**: Enter date formatted as `23SEP2026`.
4. The tool outputs a standardized, color-coded manifest (`BCB_Van_Plan_<DATE>.pdf`) directly into the folder where the `.exe` lives.

---

## Automated Failsafes Built-In
- **Late Override**: Cadets marked for an SP *and* Late are moved strictly to the Late Arrival roster.
- **Early Departures**: Cadets marked for an SP *and* Early are retained on the van manifest and logged under Early Departures.
- **Conflict Catcher**: Cadets with multiple SPs selected or missing late/early times are flagged under `REQUIRES UPDATE`.
- **Roster Index**: 1–24 master index aligned against Duke, NCCU, and Home Depot SPs.

---

## Building from Source

```bash
git clone [https://github.com/](https://github.com/)<your-username>/bcb-van-plan.git
cd bcb-van-plan

python -m venv venv
source venv/bin/activate  # Or .\venv\Scripts\activate on Windows

pip install reportlab pyinstaller
pyinstaller --onefile --noconsole --name "BCB_Van_Plan_Generator" app.py
