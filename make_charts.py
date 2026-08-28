#!/usr/bin/env python3
"""Create mobile-friendly PNG charts without external plotting dependencies."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "charts"
COLORS = {
    "employee_win": "#1B8A3A",
    "employer_win": "#B54A4A",
    "mixed_unclear": "#D99A22",
    "excluded": "#B8C2CC",
    "included": "#4E8B73",
    "confirmed_yes": "#B54A4A",
    "confirmed_no": "#1B8A3A",
    "authority_not_determined": "#8FA6B5",
    "not_alleged": "#B7D5C2",
    "not_reviewed": "#DDE5EA",
}
COLLAR_COLORS = {
    "white_collar": "#253B6E",
    "blue_collar": "#2F80B7",
    "pink_collar": "#E978A8",
    "not_stated": "#B8C2CC",
}
INDUSTRY_COLORS = {
    "healthcare": "#00897B",
    "education": "#7E57C2",
    "hospitality": "#F28E2B",
    "construction": "#8C564B",
    "retail": "#4E79A7",
    "transport": "#D4A72C",
    "public_sector": "#59A14F",
    "not_stated": "#B8C2CC",
}


def font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    """Use a legible scalable font when available, with a Pillow fallback."""
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


TITLE_FONT = font(34, bold=True)
LABEL_FONT = font(24)
SMALL_FONT = font(20)
VALUE_FONT = font(22, bold=True)
LEGEND_FONT = font(22)


def pretty(label: str) -> str:
    return label.replace("_", " ")


def text_width(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.ImageFont) -> float:
    box = draw.textbbox((0, 0), text, font=text_font)
    return box[2] - box[0]


def rows() -> list[dict[str, str]]:
    with (ROOT / "output" / "combined_2020_2025_full_classification.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def baseline_rows() -> list[dict[str, str]]:
    """Load the manually reviewed 2024 baseline export for the focused chart."""
    with (ROOT / "output" / "baseline_substantive_claims.csv").open(newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("included_in_baseline") == "yes"]


def bar_chart(
    title: str,
    labels: list[str],
    series: dict[str, list[int]],
    path: Path,
    stacked: bool = False,
) -> None:
    # Near-square output makes the chart occupy materially more screen height on phones.
    width, height = 900, 820
    left, right, top, bottom = 90, 35, 95, 165
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((left, 28), title, fill="#111111", font=TITLE_FONT)

    max_value = max(
        sum(series[k][i] for k in series) if stacked else max(series[k][i] for k in series)
        for i in range(len(labels))
    ) or 1
    chart_h, chart_w = height - bottom - top, width - left - right
    slot_w = chart_w / max(1, len(labels))
    bar_w = max(34, min(82, int(slot_w * 0.58)))

    for j in range(5):
        y = height - bottom - j * chart_h / 4
        draw.line((left, y, width - right, y), fill="#E2E6E9", width=2)
        tick = round(max_value * j / 4)
        tick_text = str(tick)
        draw.text(
            (left - text_width(draw, tick_text, SMALL_FONT) - 12, y - 12),
            tick_text,
            fill="#555555",
            font=SMALL_FONT,
        )

    for i, label in enumerate(labels):
        x = left + (i + 0.5) * chart_w / len(labels)
        label_text = pretty(label)
        draw.text(
            (x - text_width(draw, label_text, LABEL_FONT) / 2, height - bottom + 18),
            label_text,
            fill="#333333",
            font=LABEL_FONT,
        )
        y_base = height - bottom
        running = 0
        for key, values in series.items():
            value = values[i]
            h = int(value / max_value * chart_h)
            y1 = y_base - running - h
            y2 = y_base - running
            draw.rectangle(
                (x - bar_w / 2, y1, x + bar_w / 2, y2),
                fill=COLORS.get(key, "#607D8B"),
            )
            if stacked:
                running += h
            else:
                y_base -= h

        total = sum(series[k][i] for k in series) if stacked else max(series[k][i] for k in series)
        value_text = str(total)
        top_y = height - bottom - int(total / max_value * chart_h)
        draw.text(
            (x - text_width(draw, value_text, VALUE_FONT) / 2, max(top + 5, top_y - 30)),
            value_text,
            fill="#222222",
            font=VALUE_FONT,
        )

    legend_y = height - 58
    legend_items = list(series)
    item_width = chart_w / max(1, len(legend_items))
    for idx, key in enumerate(legend_items):
        x = left + idx * item_width
        draw.rounded_rectangle(
            (x, legend_y, x + 20, legend_y + 20),
            radius=4,
            fill=COLORS.get(key, "#607D8B"),
        )
        draw.text((x + 29, legend_y - 3), pretty(key), fill="#333333", font=LEGEND_FONT)

    image.save(path, optimize=True)


def line_chart(title: str, labels: list[str], series: dict[str, list[float]], path: Path) -> None:
    """Draw a phone-readable percentage line chart using only Pillow."""
    width, height = 900, 820
    left, right, bottom, top = 95, 35, 165, 95
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((left, 28), title, fill="#111111", font=TITLE_FONT)
    chart_w, chart_h = width - left - right, height - bottom - top

    for tick in range(0, 101, 20):
        y = height - bottom - tick / 100 * chart_h
        draw.line((left, y, width - right, y), fill="#E2E6E9", width=2)
        tick_text = f"{tick}%"
        draw.text(
            (left - text_width(draw, tick_text, SMALL_FONT) - 12, y - 12),
            tick_text,
            fill="#555555",
            font=SMALL_FONT,
        )

    colors = [COLORS["employee_win"], "#287C8E"]
    for idx, (name, values) in enumerate(series.items()):
        points = []
        for i, value in enumerate(values):
            x = left + i * chart_w / (len(labels) - 1)
            y = height - bottom - value / 100 * chart_h
            points.append((x, y))
            draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=colors[idx % len(colors)])
            value_text = f"{value:.1f}%"
            draw.text(
                (x - text_width(draw, value_text, SMALL_FONT) / 2, y - 34),
                value_text,
                fill=colors[idx % len(colors)],
                font=SMALL_FONT,
            )
        if len(points) > 1:
            draw.line(points, fill=colors[idx % len(colors)], width=6)

    for i, label in enumerate(labels):
        x = left + i * chart_w / (len(labels) - 1)
        draw.text(
            (x - text_width(draw, label, LABEL_FONT) / 2, height - bottom + 18),
            label,
            fill="#333333",
            font=LABEL_FONT,
        )

    legend_y = height - 58
    item_width = chart_w / max(1, len(series))
    for idx, name in enumerate(series):
        x = left + idx * item_width
        color = colors[idx % len(colors)]
        draw.line((x, legend_y + 10, x + 28, legend_y + 10), fill=color, width=6)
        draw.text((x + 38, legend_y - 3), pretty(name), fill="#333333", font=LEGEND_FONT)

    image.save(path, optimize=True)


def pie_chart(
    title: str,
    counts: Counter[str],
    path: Path,
    semantic_colors: dict[str, str] | None = None,
) -> None:
    """Draw a mobile-friendly labelled donut chart for a categorical distribution."""
    width, height = 900, 940
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((55, 28), title, fill="#111111", font=TITLE_FONT)
    total = sum(counts.values()) or 1
    palette = [
        "#4E8B73",
        "#6C9FB3",
        "#84A98C",
        "#78A6A8",
        "#9BB7A5",
        "#A7B8C2",
        "#B8C2CC",
        "#C7D3D9",
    ]

    box = (130, 105, 770, 745)
    start = 0.0
    ordered = counts.most_common()
    for index, (label, count) in enumerate(ordered):
        extent = 360 * count / total
        color = (semantic_colors or {}).get(label, palette[index % len(palette)])
        draw.pieslice(box, start=start, end=start + extent, fill=color, outline="white", width=3)
        start += extent

    # Donut centre gives slices more visual separation at phone size.
    draw.ellipse((320, 295, 580, 555), fill="white")
    total_text = f"{total:,}"
    draw.text(
        ((width - text_width(draw, total_text, TITLE_FONT)) / 2, 385),
        total_text,
        fill="#111111",
        font=TITLE_FONT,
    )
    centre_label = "cases"
    draw.text(
        ((width - text_width(draw, centre_label, LABEL_FONT)) / 2, 430),
        centre_label,
        fill="#666666",
        font=LABEL_FONT,
    )

    legend_x, legend_y = 70, 785
    columns = 2 if len(ordered) > 4 else 1
    col_width = 410
    row_height = 44
    rows_per_col = (len(ordered) + columns - 1) // columns
    for index, (label, count) in enumerate(ordered):
        col = index // rows_per_col
        row = index % rows_per_col
        x = legend_x + col * col_width
        y = legend_y + row * row_height
        color = (semantic_colors or {}).get(label, palette[index % len(palette)])
        draw.rounded_rectangle((x, y, x + 22, y + 22), radius=4, fill=color)
        pct = 100 * count / total
        legend = f"{pretty(label)}  {count} · {pct:.1f}%"
        draw.text((x + 34, y - 3), legend, fill="#333333", font=SMALL_FONT)

    image.save(path, optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = rows()
    years = [str(y) for y in range(2020, 2026)]
    by_year = defaultdict(Counter)
    serious = defaultdict(Counter)
    for row in data:
        by_year[row["year"]][row["classified_outcome"]] += 1
        serious[row["year"]][row["authority_serious_misconduct_finding"] or "not_reviewed"] += 1

    bar_chart(
        "ERA corpus rows by year",
        years,
        {
            "included": [
                sum(by_year[y][k] for k in ("employee_win", "employer_win", "mixed_unclear"))
                for y in years
            ],
            "excluded": [by_year[y]["excluded"] for y in years],
        },
        OUT / "corpus_by_year.png",
    )
    bar_chart(
        "Outcome classification by year",
        years,
        {
            k: [by_year[y][k] for y in years]
            for k in ("employee_win", "employer_win", "mixed_unclear", "excluded")
        },
        OUT / "outcomes_by_year.png",
        stacked=True,
    )
    bar_chart(
        "Serious-misconduct status by year",
        years,
        {
            k: [serious[y][k] for y in years]
            for k in (
                "confirmed_yes",
                "confirmed_no",
                "authority_not_determined",
                "not_alleged",
                "not_reviewed",
            )
        },
        OUT / "serious_status_by_year.png",
        stacked=True,
    )

    reviewed = baseline_rows()
    labels = ["serious alleged", "not alleged"]
    bar_chart(
        "2024 wins by serious-misconduct allegation",
        labels,
        {
            "employee_win": [
                sum(
                    r["serious_misconduct_alleged"] == "yes" and r["outcome"] == "employee_win"
                    for r in reviewed
                ),
                sum(
                    r["serious_misconduct_alleged"] == "no" and r["outcome"] == "employee_win"
                    for r in reviewed
                ),
            ],
            "employer_win": [
                sum(
                    r["serious_misconduct_alleged"] == "yes" and r["outcome"] == "employer_win"
                    for r in reviewed
                ),
                sum(
                    r["serious_misconduct_alleged"] == "no" and r["outcome"] == "employer_win"
                    for r in reviewed
                ),
            ],
        },
        OUT / "2024_serious_vs_not.png",
        stacked=True,
    )

    all_outcome_rates = []
    binary_rates = []
    for year in years:
        employee = by_year[year]["employee_win"]
        employer = by_year[year]["employer_win"]
        mixed = by_year[year]["mixed_unclear"]
        all_outcome_rates.append(
            100 * employee / (employee + employer + mixed) if employee + employer + mixed else 0
        )
        binary_rates.append(
            100 * employee / (employee + employer) if employee + employer else 0
        )

    line_chart(
        "Employee win rate by year",
        years,
        {
            "all classified outcomes": all_outcome_rates,
            "binary outcomes only": binary_rates,
        },
        OUT / "employee_win_rate_by_year.png",
    )
    pie_chart(
        "Overall outcome classification",
        Counter(r["classified_outcome"] for r in data),
        OUT / "outcome_overall_pie.png",
        COLORS,
    )
    pie_chart(
        "Overall serious-misconduct status",
        Counter(r["authority_serious_misconduct_finding"] or "not_reviewed" for r in data),
        OUT / "serious_status_overall_pie.png",
        COLORS,
    )

    enriched_path = ROOT / "output" / "combined_2020_2025_context_enriched.csv"
    if enriched_path.exists():
        with enriched_path.open(newline="") as f:
            enriched = list(csv.DictReader(f))
        pie_chart(
            "Occupation collar signal",
            Counter(r["occupation_collar_category"] for r in enriched),
            OUT / "collar_overall_pie.png",
            COLLAR_COLORS,
        )
        pie_chart(
            "Industry signal",
            Counter(r["industry_category"] for r in enriched),
            OUT / "industry_overall_pie.png",
            INDUSTRY_COLORS,
        )

    print(f"Wrote charts to {OUT}")


if __name__ == "__main__":
    main()
