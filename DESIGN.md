# PySide6 Frontend — Design & Context

## Overview

The PySide6 frontend is a rewrite of the original CustomTkinter (CTk) frontend, targeting the same `BaseDashboard` / `BaseMachineCard` interface contracts defined in `src/frontend/base/interfaces.py`. It uses Qt6 via PySide6 with QSS stylesheets for all visual styling and Matplotlib's `QtAgg` backend for embedded charts.

Entry point: `main.py` → `Dashboard(app, controller)` → `dashboard.run()` (calls `app.exec()`)

---

## File Structure

```
src/frontend/pyside6/
├── __init__.py          # empty — marks package
├── theme.py             # colour palette, QSS generator, T() accessor
├── dashboard.py         # QMainWindow — top-level shell
├── machine_card.py      # QFrame — per-machine panel
├── predictor.py         # QDialog — cycle end-date predictor
└── widgets.py           # reusable: DateRangeBar, Toast, LogPanel,
                         #           WeeklyAnalyticsPanel, DatabaseViewerDialog,
                         #           _RangePickerPopup, _ClickTimePicker
```

---

## Theme System (`theme.py`)

### Colour constants (accent colours shared across both modes)

| Name     | Hex       | Usage                          |
|----------|-----------|--------------------------------|
| `GREEN`  | `#00C853` | Live data, OK state, log text  |
| `RED`    | `#FF5252` | Offline / error state          |
| `YELLOW` | `#FFD740` | Warning / missing events       |
| `BLUE`   | `#40C4FF` | Informational                  |
| `ORANGE` | `#FF6D00` | Secondary accent               |
| `PURPLE` | `#CE93D8` | Predict button                 |

### Palette (`_PALETTE`)

Two modes — `"dark"` (default) and `"light"` — each define ~30 semantic colour keys:

- **Structural**: `bg`, `hdr`, `hdr_border`, `card`, `card_border`, `separator`
- **Component**: `counter_bg`, `stat_bg`, `stat_border`, `chart_bg`, `log_bg`, `log_border`
- **Typography**: `txt`, `txt_dim`, `txt_muted`, `log_ts`
- **Chart**: `grid`, `spine`, `tick`
- **Input**: `entry_fg`, `entry_border`
- **Popups**: `popup_bg`
- **Tints** (background washes for status badges): `tint_green`, `tint_green_border`, `tint_green_deep`, `tint_red`, `tint_red_deep`, `tint_yellow`, `tint_purple`, …

### Public API

```python
T(key: str) -> str          # returns hex for the active theme
set_theme(name: str)        # switches active theme ("dark" | "light")
build_qss(theme: str) -> str  # generates the full application QSS string
apply_theme(app, theme)     # calls build_qss and app.setStyleSheet(...)
current_theme() -> str      # returns current theme name
```

`build_qss` produces a single QSS string covering all `objectName`-targeted selectors. All widget colours are derived from the palette at stylesheet-build time, so a theme toggle calls `apply_theme` and then `refresh_theme()` on every widget that carries inline styles.

### Typography

- **UI font**: `"Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif` — base 12 px
- **Mono font**: `"Courier New", "Consolas", monospace` — used for counters, stat values, log text

---

## Layout Architecture

### Window (`Dashboard`)

```
QMainWindow
└── central QWidget (main_layout: QVBoxLayout, no margins, no spacing)
    ├── Header (QWidget #header, fixed 68 px)
    └── Body (QWidget, stretch=1, margins 16/14)
        ├── Toast (QFrame, fixed 36 px)
        ├── Cards row (QHBoxLayout, stretch=1)
        │   └── MachineCard × N
        ├── WeeklyAnalyticsPanel (fixed 240 px)
        └── LogPanel (fixed 130 px)
```

Default window size: **1920 × 980**, minimum **1500 × 780**.

### Header bar

Fixed 68 px. Left-to-right contents:
1. **Title** — "LTC Thermal Shock Monitoring" in GREEN, 15 pt bold, letter-spacing 2 px
2. **MQTT pill** — small badge, GREEN tint
3. (stretch)
4. **Live clock** — `YYYY-MM-DD   HH:MM:SS`, monospace, 12 px, updates every 1 s
5. Vertical divider
6. **Broker status badge** — pill toggling `● ONLINE` (GREEN) / `● OFFLINE` (RED)
7. Vertical divider
8. **Theme toggle** — `☾ Dark Mode` / `☀ Light Mode`, checkable QPushButton, 115 × 32 px
9. **Settings** — `⚙  Settings` button, opens a settings panel

### Machine card (`MachineCard` — `QFrame#machineCard`)

Each card gets an equal horizontal share of the cards row (`QSizePolicy.Expanding`).
Internal layout (`QVBoxLayout`, margins 0/0/0/14):

```
┌─────────────────────────────────────┐
│  ▬▬▬ Coloured accent bar (5 px)     │  #cardAccent, per-machine colour
├─────────────────────────────────────┤
│  inner QVBoxLayout (margins 16/12)  │
│  ├─ Header row                      │  pulse dot ● | name | [OFFLINE/ONLINE]
│  ├─ Counter panel (#counterPanel)   │  big mono value + "CYCLES" + invalid count
│  ├─ Separator (1 px)               │
│  ├─ Control buttons row             │  [⬡ Predict] + conditional extras
│  ├─ DateRangeBar                    │  centred, with Apply/Reset/calendar
│  ├─ Separator (1 px)               │
│  ├─ Stat tile grid (3 × 2)         │  AVG INTERVAL / CYCLES/HR / MIN / MAX / TODAY / SAVED
│  ├─ DB source label                 │  "DB" badge or "LIVE" when no DB history
│  └─ Matplotlib chart area          │  cycle-timeline line chart (QtAgg)
└─────────────────────────────────────┘
```

**Counter panel**: monospace 56 px bold value label (`#counterValue`), 10 px spaced "CYCLES" caption (`#counterLabel`), 11 px invalid-cycle count beneath.

**Stat tiles** (`#statTile`): 9 px ALL-CAPS caption (`#statCap`) + 12 px monospace value (`#statVal`). Colour-coded: normal = `txt`, anomalous intervals = `YELLOW` or `RED`.

**Pulse dot**: animates GREEN for 240 ms on each new MQTT event via a `QTimer`.

**Connection badge**: pill toggling between `ONLINE` (GREEN tint) and `OFFLINE` (RED deep tint).

### Chart

Matplotlib figure embedded via `FigureCanvasQTAgg`. Each `MachineCard` owns one `Figure` + `Axes`. Chart background matches `chart_bg` from the active palette. Redrawn with `canvas.draw_idle()` on data updates. Series line colour = machine `color` from config.

---

## Widget Catalogue (`widgets.py`)

### `DateRangeBar`

Two-row widget:
- **Row 1**: `QDateTimeEdit` (start) → `QDateTimeEdit` (end), format `yyyy-MM-dd HH:mm`
- **Row 2**: `📅 Date Filter` button | `Apply` | `Reset`

**Live mode** (default): rolls both bounds forward every 1 s (yesterday 00:00 → now).  
**Frozen mode**: triggered by `Apply`; `Reset` resumes live mode.  
**Calendar popup** (`_RangePickerPopup`): `Qt.WindowType.Popup` frame with a `QCalendarWidget`, START/END toggle buttons, a click-only `_ClickTimePicker` (▲/▼ hour/minute, no keyboard spin), summary label, and a `Confirm range` button that enables only after both bounds are picked.

### `Toast`

Fixed 40 px banner that auto-hides via a `QSingleShot` timer. Three colour states:
- GREEN → `tint_green` / `tint_green_border`
- RED → `tint_red` / `tint_red_border`
- other → `tint_yellow` / `tint_yellow_border`

### `LogPanel`

Fixed 130 px `QFrame#logFrame`. Contains a read-only `QTextEdit#logText` (GREEN monospace, 10 px). Each `log()` call prepends a `[HH:MM:SS]` timestamp in `log_ts` colour via inline HTML, then scrolls to bottom.

### `WeeklyAnalyticsPanel`

Fixed 240 px, three-column layout:
1. **Bar chart** (Matplotlib, `stretch=3`) — grouped bars, one group per day for last 7 days, one bar per machine
2. **Stats panel** (stretch=1) — summary figures (total week cycles, best day, etc.)
3. **Uptime panel** (stretch=1) — monthly uptime indicators

Refreshes every 30 s via `QTimer`. Also manually triggered 1.2 s after startup.

### `DatabaseViewerDialog`

`QDialog` that presents all stored cycle events for one machine in a `QTableWidget`. Sortable, filterable.

---

## `CyclePredictor` Dialog (`predictor.py`)

`QDialog`, resizes to 900 × 620 (min 780 × 520). Per-machine colour used for title accent.

Layout:
1. Title + subtitle
2. **Input row** (`QFrame`): `Test start` `QDateTimeEdit` | `Target cycles` `QLineEdit` | `[Calculate]` button
3. **Result row**: End date, total days, avg cycles/hr, cycles/day — displayed as labelled value pairs
4. **Projection chart** (`FigureCanvasQTAgg`) — timeline from start to projected end with actual recorded data overlaid

Calculation uses the average interval derived from the card's in-memory `data` list (filtered MQTT events). Does not hit the database directly.

---

## Theme Toggle Flow

1. User clicks `☾ Dark Mode` / `☀ Light Mode` in header.
2. `_toggle_theme()` calls `set_theme(name)` → updates `_current` in `theme.py`.
3. `apply_theme(app, name)` regenerates QSS and calls `app.setStyleSheet(qss)`.
4. Dashboard iterates all `MachineCard` instances → `card.refresh_theme()`.
5. Each card calls `_date_bar.refresh_theme()` and rebuilds any inline-styled chart elements.

---

## Threading Notes

- All UI construction and updates happen on the Qt main thread.
- `AppController` callbacks (`on_telemetry`, `on_status`, `on_log`, etc.) are posted to the Qt event loop via `QTimer.singleShot(0, callback)` inside the controller, ensuring thread safety.
- Matplotlib chart redraws use `canvas.draw_idle()` to coalesce updates.
- `WeeklyAnalyticsPanel` refreshes via a 30 s `QTimer` on the main thread; it reads from the database through the card's `controller.db` reference.

---

## Differences vs CTk Frontend

| Concern              | CTk frontend                          | PySide6 frontend                       |
|----------------------|---------------------------------------|----------------------------------------|
| Styling              | CTk theme JSON + per-widget kwargs    | QSS stylesheets via `build_qss()`      |
| Chart embedding      | `FigureCanvasTkAgg`                   | `FigureCanvasQTAgg` (QtAgg backend)    |
| Layout               | CTk grid/pack geometry manager        | Qt layout managers (VBox/HBox/Grid)    |
| Date picker          | `ui_calendar.py` custom widget        | `_RangePickerPopup` with `QCalendarWidget` |
| Thread posting       | `widget.after(0, callback)`           | `QTimer.singleShot(0, callback)`       |
| Window resize quirks | Force-repaint via `touchLabels`       | None required                          |
| Weekly analytics     | Not present                           | `WeeklyAnalyticsPanel` (new)           |
| DB viewer            | Not present                           | `DatabaseViewerDialog` (new)           |
