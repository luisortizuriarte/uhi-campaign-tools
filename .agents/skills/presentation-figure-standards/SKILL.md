---
name: presentation-figure-standards
description: >-
  Provides strict visual design standards, layouts, typography, and code templates for presentation figures and graphs (16:9 widescreen, edgeless minimalist styling, Tufte-style de-cluttered axes, Figtree font, bespoke legends, and color-matched value annotations). Use whenever generating or modifying presentation charts, bar charts, anomaly plots, comparison figures, or slide graphics.
---

# Presentation Figure Design Standards

This skill defines the visual design standards and implementation templates for publication-grade, slide-ready presentation charts (PowerPoint 16:9 widescreen format). It enforces a minimalist, de-cluttered aesthetic inspired by Edward Tufte's data-ink ratio principles.

---

## 1. Canvas & Aspect Ratio

| Parameter | Specification | Matplotlib Implementation |
| :--- | :--- | :--- |
| **Aspect Ratio** | 16:9 widescreen | `figsize=(13.333, 7.5)` |
| **Resolution** | High-definition print / slide DPI | `dpi=300` |
| **Canvas Background** | Pure White | `facecolor="#FFFFFF"` |
| **Axes Inset Box** | Custom figure coordinates | `fig.add_axes([0.08, 0.16, 0.88, 0.62])` |

> [!IMPORTANT]
> The axes placement `[left=0.08, bottom=0.16, width=0.88, height=0.62]` guarantees generous vertical breathing room for a top-left aligned title (`y=0.94`), a lowered centered legend (`y ≈ 0.77`), and a bottom explanatory caption (`y=0.035`).

---

## 2. Color Palette Tokens

Always use these exact hex color tokens:

| Token Name | Hex Code | Role / Usage |
| :--- | :--- | :--- |
| `morning` / `am` | `#2980B9` | Morning series, primary blue fill and text |
| `afternoon` / `af` | `#F39C12` | Afternoon series, vibrant amber/orange fill and text |
| `evening` / `pm` | `#E74C3C` | Evening series, warm coral red fill and text |
| `neutral_dark` | `#1F2937` | Main title, category names, x-axis label |
| `neutral_gray` | `#7F8C8D` | Bottom subtitle/caption, explanatory notes |
| `baseline` | `#BDC3C7` | Zero reference baseline (`y=0` line) |
| `legend_bg` | `#ECF0F1` | Background fill of the legend container card |
| `canvas_bg` | `#FFFFFF` | Slide figure background |

---

## 3. Typography & Hierarchy

The required font family for all text elements is **`Figtree`**. Fall back to `["Figtree", "DejaVu Sans", "sans-serif"]` if necessary.

```python
plt.rcParams["font.family"] = ["Figtree", "DejaVu Sans", "sans-serif"]
```

| Element | Size | Weight | Color | Position / Alignment |
| :--- | :--- | :--- | :--- | :--- |
| **Main Title** | `16pt` | Bold | `#1F2937` | Canvas `(0.08, 0.94)`, `ha="left"`, `va="top"` |
| **Category Labels** | `12pt` | Regular | `#1F2937` | X-ticks on axes, `ha="center"` |
| **X-Axis Title** | `13pt` | Bold | `#1F2937` | `labelpad=12` |
| **Legend Text** | `11.5pt` | Bold | `#1F2937` | Inside legend box |
| **Data Value Labels** | `10.5pt` | Bold | Matches bar | Directly above/below bar and error cap |
| **Caption / Subtitle** | `10.5pt` | Italic | `#7F8C8D` | Canvas `(0.50, 0.035)`, `ha="center"`, `va="center"` |

---

## 4. De-Cluttering & Minimalist Axes Rules

1. **Remove All Outer Spines**:
   ```python
   for spine in ax.spines.values():
       spine.set_visible(False)
   ```
2. **Eliminate Y-Axis**:
   Do not draw y-axis spines, tick marks, or tick labels. Data values are conveyed directly via numerical labels on the bars.
   ```python
   ax.tick_params(left=False, labelleft=False, bottom=False)
   ```
3. **Zero Reference Baseline**:
   Draw a single subtle horizontal line at `y=0`:
   ```python
   ax.axhline(0, color="#BDC3C7", linestyle="-", linewidth=1.2, zorder=1)
   ```
4. **Edgeless Bars**:
   Bars must have no border or edge outline (`edgecolor="none"`, `linewidth=0`).

---

## 5. Direct Numerical Labels & Error Bars

- **Format**: Explicit signed formatting `+X.XX°` for positive and `-X.XX°` for negative (e.g. `+1.27°`, `-0.68°`).
- **Color Matching**: The font color of each label must match the fill color of its corresponding bar (`#2980B9`, `#F39C12`, or `#E74C3C`).
- **Positioning**:
  - Positive values: `val + err + 0.12`, `va="bottom"`
  - Negative values: `val - err - 0.16`, `va="top"`
- **Error Bars**:
  - Standard: 95% Confidence Interval (`1.96 * SEM`).
  - Cap size: `3.5`, `lw=1.3`, `capthick=1.3`.
  - Color matches the series bar color.

---

## 6. Legend Architecture

The legend is designed as a floating top card:
- **Position**: Lowered below the main title:
  ```python
  loc="upper center", bbox_to_anchor=(0.5, 0.98)
  ```
- **Columns**: 1 column per series (`ncols=3` for 3 collection periods).
- **Markers**: Solid squares instead of elongated rectangles:
  ```python
  handles = [mpatches.Patch(facecolor=c, edgecolor="none", label=lbl) for c, lbl in items]
  handlelength=1.0, handleheight=1.0
  ```
- **Container Box**:
  - Background fill: `#ECF0F1`
  - Border: None (`edgecolor="none"`)
  - Rounded corners: `leg.get_frame().set_boxstyle("round,pad=0.5,rounding_size=0.3")`

---

## 7. Reusable Code Template & Helpers

A complete, tested, reusable implementation is available in:
- [figure_template.py](./scripts/figure_template.py)
- [generate_example.py](./examples/generate_example.py)

### Quick Implementation Snippet

```python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

fig = plt.figure(figsize=(13.333, 7.5), dpi=300, facecolor="#FFFFFF")
ax = fig.add_axes([0.08, 0.16, 0.88, 0.62])

# Hide all outer borders & ticks
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(left=False, labelleft=False, bottom=False)
ax.axhline(0, color="#BDC3C7", linestyle="-", linewidth=1.2)

# Title at top-left
fig.text(0.08, 0.94, "Main Title", ha="left", va="top", fontsize=16, weight="bold", fontfamily="Figtree", color="#1F2937")

# Legend centered and lowered
leg = ax.legend(handles=handles, ncols=3, loc="upper center", bbox_to_anchor=(0.5, 0.98),
                facecolor="#ECF0F1", edgecolor="none", handlelength=1.0, handleheight=1.0)
leg.get_frame().set_boxstyle("round,pad=0.5,rounding_size=0.3")

# Caption at bottom
fig.text(0.50, 0.035, "Caption / metadata", ha="center", va="center", fontsize=10.5, color="#7F8C8D", style="italic")
```

