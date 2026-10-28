# NOVA Campaign Project Guidelines & Visual Standards

## Figure & Graph Design Standards
When creating, editing, or styling figures, charts, and visualizations for this project:

1. **Aspect Ratio & Layout**:
   - Always use 16:9 widescreen presentation dimensions: `figsize=(13.333, 7.5)`, `dpi=300`.
   - White canvas: `facecolor="#FFFFFF"`.
   - Axes inset: `fig.add_axes([0.08, 0.16, 0.88, 0.62])` to leave dedicated margins for top title, lowered legend, and bottom caption.

2. **Typography**:
   - Universal font family: **`Figtree`** across all text elements (titles, axis labels, tick labels, legend, value annotations).
   - Main title: 16pt, bold, `#1F2937`, left-aligned at `(0.08, 0.94)`.
   - Caption / notes: 10.5pt, italic, `#7F8C8D`, centered at bottom `(0.50, 0.035)`.
   - Category labels: 12pt, `#1F2937`.
   - Data value labels: 10.5pt, bold, color matching the respective series.

3. **Color Palette**:
   - Morning (AM): `#2980B9`
   - Afternoon (AF): `#F39C12`
   - Evening (PM): `#E74C3C`
   - Reference baseline (`y=0`): `#BDC3C7` (linewidth 1.2)
   - Legend card fill: `#ECF0F1`
   - Primary text: `#1F2937`
   - Muted text / caption: `#7F8C8D`

4. **De-cluttering & Axes Rules (Tufte Style)**:
   - Remove all 4 outer spines (`spines.values() -> set_visible(False)`).
   - Remove Y-axis spine, ticks, and tick labels entirely.
   - Display values directly on bars with matching series color and explicit sign (`+` / `-`).
   - Draw a subtle zero baseline at `y=0`.
   - Remove bar edges (`edgecolor="none"`, `linewidth=0`).
   - Error bars: 95% Confidence Interval with series color.

5. **Legend Styling**:
   - Lowered below the top title with ample clearance: `loc="upper center"`, `bbox_to_anchor=(0.5, 0.98)`.
   - 1 column per series (`ncols=3`).
   - Square markers (`matplotlib.patches.Patch`, `handlelength=1.0`, `handleheight=1.0`).
   - `#ECF0F1` background, no border, rounded corners (`boxstyle="round,pad=0.5,rounding_size=0.3"`).

6. **Skill & Template Reference**:
   - Skill documentation: `.agents/skills/presentation-figure-standards/SKILL.md`
   - Standalone reusable template script: `.agents/skills/presentation-figure-standards/scripts/figure_template.py`

