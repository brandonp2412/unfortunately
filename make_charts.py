#!/usr/bin/env python3
"""Create mobile-friendly PNG charts for the full ERA dataset."""
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
AXIS_FONT = font(20)
SMALL_FONT = font(19)
VALUE_FONT = font(22, bold=True)
LEGEND_FONT = font(21)


def pretty(label: str) -> str:
    return label.replace("_", " ")


def text_width(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.ImageFont) -> float:
    box = draw.textbbox((0, 0), text, font=text_font)
    return box[2] - box[0]


def recent_rows() -> list[dict[str, str]]:
    path = ROOT / "output" / "combined_2020_2025_full_classification.csv"
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def legacy_rows() -> list[dict[str, str]]:
    path = ROOT / "output" / "combined_2010_2019_strict_classification.csv"
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def outcome_rows() -> list[dict[str, str]]:
    rows = [
        {"year": row["year"], "classified_outcome": row["final_outcome"]}
        for row in legacy_rows()
    ]
    rows.extend(
        {"year": row["year"], "classified_outcome": row["classified_outcome"]}
        for row in recent_rows()
    )
    return rows


def baseline_rows() -> list[dict[str, str]]:
    with (ROOT / "output" / "baseline_substantive_claims.csv").open(newline="") as handle:
        return [row for row in csv.DictReader(handle) if row.get("included_in_baseline") == "yes"]


def horizontal_year_chart(
    title: str,
    labels: list[str],
    series: dict[str, list[int]],
    path: Path,
) -> None:
    """Draw stacked horizontal bars so 16 years stay readable on a phone."""
    width = 900
    top, bottom, left, right = 100, 155, 100, 80
    row_h = 56
    height = top + bottom + row_h * len(labels)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((left, 28), title, fill="#111111", font=TITLE_FONT)
    chart_w = width - left - right
    totals = [sum(series[key][i] for key in series) for i in range(len(labels))]
    max_value = max(totals) or 1

    for i, label in enumerate(labels):
        y = top + i * row_h + 8
        draw.text((18, y + 6), label, fill="#333333", font=LABEL_FONT)
        x = left
        for key, values in series.items():
            value = values[i]
            seg_w = chart_w * value / max_value
            draw.rounded_rectangle(
                (x, y, x + seg_w, y + 30),
                radius=5,
                fill=COLORS.get(key, "#607D8B"),
            )
            x += seg_w
        total_text = str(totals[i])
        draw.text((min(width - right + 10, x + 8), y + 4), total_text, fill="#333333", font=AXIS_FONT)

    legend_items = list(series)
    columns = 2
    legend_y = height - 105
    col_w = 390
    for idx, key in enumerate(legend_items):
        col = idx % columns
        row = idx // columns
        x = left + col * col_w
        y = legend_y + row * 38
        draw.rounded_rectangle((x, y, x + 20, y + 20), radius=4, fill=COLORS.get(key, "#607D8B"))
        draw.text((x + 30, y - 3), pretty(key), fill="#333333", font=LEGEND_FONT)

    image.save(path, optimize=True)


def vertical_bar_chart(
    title: str,
    labels: list[str],
    series: dict[str, list[int]],
    path: Path,
    *,
    stacked: bool = False,
) -> None:
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
        tick_text = str(round(max_value * j / 4))
        draw.text((left - text_width(draw, tick_text, SMALL_FONT) - 12, y - 12), tick_text, fill="#555555", font=SMALL_FONT)

    for i, label in enumerate(labels):
        x = left + (i + 0.5) * chart_w / len(labels)
        label_text = pretty(label)
        draw.text((x - text_width(draw, label_text, LABEL_FONT) / 2, height - bottom + 18), label_text, fill="#333333", font=LABEL_FONT)
        y_base = height - bottom
        running = 0
        for key, values in series.items():
            value = values[i]
            h = int(value / max_value * chart_h)
            y1 = y_base - running - h
            y2 = y_base - running
            draw.rectangle((x - bar_w / 2, y1, x + bar_w / 2, y2), fill=COLORS.get(key, "#607D8B"))
            if stacked:
                running += h
            else:
                y_base -= h
        total = sum(series[k][i] for k in series) if stacked else max(series[k][i] for k in series)
        value_text = str(total)
        top_y = height - bottom - int(total / max_value * chart_h)
        draw.text((x - text_width(draw, value_text, VALUE_FONT) / 2, max(top + 5, top_y - 30)), value_text, fill="#222222", font=VALUE_FONT)

    legend_y = height - 58
    item_width = chart_w / max(1, len(series))
    for idx, key in enumerate(series):
        x = left + idx * item_width
        draw.rounded_rectangle((x, legend_y, x + 20, legend_y + 20), radius=4, fill=COLORS.get(key, "#607D8B"))
        draw.text((x + 29, legend_y - 3), pretty(key), fill="#333333", font=LEGEND_FONT)
    image.save(path, optimize=True)


def line_chart(title: str, labels: list[str], series: dict[str, list[float]], path: Path) -> None:
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
        draw.text((left - text_width(draw, tick_text, SMALL_FONT) - 12, y - 12), tick_text, fill="#555555", font=SMALL_FONT)

    colors = [COLORS["employee_win"], "#287C8E"]
    for idx, (name, values) in enumerate(series.items()):
        points = []
        for i, value in enumerate(values):
            x = left + i * chart_w / (len(labels) - 1)
            y = height - bottom - value / 100 * chart_h
            points.append((x, y))
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=colors[idx % len(colors)])
            if i % 2 == idx % 2 or i == len(labels) - 1:
                value_text = f"{value:.1f}%"
                y_offset = -32 if idx == 0 else 12
                draw.text((x - text_width(draw, value_text, SMALL_FONT) / 2, y + y_offset), value_text, fill=colors[idx % len(colors)], font=SMALL_FONT)
        if len(points) > 1:
            draw.line(points, fill=colors[idx % len(colors)], width=5)

    for i, label in enumerate(labels):
        x = left + i * chart_w / (len(labels) - 1)
        short_label = label[2:] if len(labels) > 10 else label
        draw.text((x - text_width(draw, short_label, AXIS_FONT) / 2, height - bottom + 18), short_label, fill="#333333", font=AXIS_FONT)
    if len(labels) > 10:
        draw.text((left, height - bottom + 55), "Years shown as 10–25 = 2010–2025", fill="#666666", font=SMALL_FONT)

    legend_y = height - 58
    item_width = chart_w / max(1, len(series))
    for idx, name in enumerate(series):
        x = left + idx * item_width
        color = colors[idx % len(colors)]
        draw.line((x, legend_y + 10, x + 28, legend_y + 10), fill=color, width=6)
        draw.text((x + 38, legend_y - 3), pretty(name), fill="#333333", font=LEGEND_FONT)
    image.save(path, optimize=True)


def pie_chart(title: str, counts: Counter[str], path: Path, semantic_colors: dict[str, str] | None = None) -> None:
    width, height = 900, 940
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((55, 28), title, fill="#111111", font=TITLE_FONT)
    total = sum(counts.values()) or 1
    palette = ["#4E8B73", "#6C9FB3", "#84A98C", "#78A6A8", "#9BB7A5", "#A7B8C2", "#B8C2CC", "#C7D3D9"]
    box = (130, 105, 770, 745)
    start = 0.0
    ordered = counts.most_common()
    for index, (label, count) in enumerate(ordered):
        extent = 360 * count / total
        color = (semantic_colors or {}).get(label, palette[index % len(palette)])
        draw.pieslice(box, start=start, end=start + extent, fill=color, outline="white", width=3)
        start += extent
    draw.ellipse((320, 295, 580, 555), fill="white")
    total_text = f"{total:,}"
    draw.text(((width - text_width(draw, total_text, TITLE_FONT)) / 2, 385), total_text, fill="#111111", font=TITLE_FONT)
    draw.text(((width - text_width(draw, "cases", LABEL_FONT)) / 2, 430), "cases", fill="#666666", font=LABEL_FONT)

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
        draw.text((x + 34, y - 3), f"{pretty(label)}  {count} · {pct:.1f}%", fill="#333333", font=SMALL_FONT)
    image.save(path, optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    data = outcome_rows()
    years = [str(year) for year in range(2010, 2026)]
    by_year: dict[str, Counter[str]] = defaultdict(Counter)
    for row in data:
        by_year[row["year"]][row["classified_outcome"]] += 1

    horizontal_year_chart(
        "ERA corpus rows · 2010–2025",
        years,
        {
            "included": [sum(by_year[y][k] for k in ("employee_win", "employer_win", "mixed_unclear")) for y in years],
            "excluded": [by_year[y]["excluded"] for y in years],
        },
        OUT / "corpus_by_year.png",
    )
    horizontal_year_chart(
        "Outcome classification · 2010–2025",
        years,
        {key: [by_year[y][key] for y in years] for key in ("employee_win", "employer_win", "mixed_unclear", "excluded")},
        OUT / "outcomes_by_year.png",
    )

    all_outcome_rates = []
    binary_rates = []
    for year in years:
        employee = by_year[year]["employee_win"]
        employer = by_year[year]["employer_win"]
        mixed = by_year[year]["mixed_unclear"]
        all_outcome_rates.append(100 * employee / (employee + employer + mixed) if employee + employer + mixed else 0)
        binary_rates.append(100 * employee / (employee + employer) if employee + employer else 0)
    line_chart(
        "Employee win rate · 2010–2025",
        years,
        {"all classified outcomes": all_outcome_rates, "binary outcomes only": binary_rates},
        OUT / "employee_win_rate_by_year.png",
    )
    pie_chart(
        "Overall outcomes · 2010–2025",
        Counter(row["classified_outcome"] for row in data),
        OUT / "outcome_overall_pie.png",
        COLORS,
    )

    recent = recent_rows()
    serious_years = [str(year) for year in range(2020, 2026)]
    serious: dict[str, Counter[str]] = defaultdict(Counter)
    for row in recent:
        serious[row["year"]][row["authority_serious_misconduct_finding"] or "not_reviewed"] += 1
    vertical_bar_chart(
        "Serious-misconduct status · 2020–2025",
        serious_years,
        {key: [serious[y][key] for y in serious_years] for key in ("confirmed_yes", "confirmed_no", "authority_not_determined", "not_alleged", "not_reviewed")},
        OUT / "serious_status_by_year.png",
        stacked=True,
    )
    pie_chart(
        "Serious-misconduct status · 2020–2025",
        Counter(row["authority_serious_misconduct_finding"] or "not_reviewed" for row in recent),
        OUT / "serious_status_overall_pie.png",
        COLORS,
    )

    reviewed = baseline_rows()
    labels = ["serious alleged", "not alleged"]
    vertical_bar_chart(
        "2024 wins by serious-misconduct allegation",
        labels,
        {
            "employee_win": [
                sum(row["serious_misconduct_alleged"] == "yes" and row["outcome"] == "employee_win" for row in reviewed),
                sum(row["serious_misconduct_alleged"] == "no" and row["outcome"] == "employee_win" for row in reviewed),
            ],
            "employer_win": [
                sum(row["serious_misconduct_alleged"] == "yes" and row["outcome"] == "employer_win" for row in reviewed),
                sum(row["serious_misconduct_alleged"] == "no" and row["outcome"] == "employer_win" for row in reviewed),
            ],
        },
        OUT / "2024_serious_vs_not.png",
        stacked=True,
    )

    enriched_path = ROOT / "output" / "combined_2020_2025_context_enriched.csv"
    if enriched_path.exists():
        with enriched_path.open(newline="") as handle:
            enriched = list(csv.DictReader(handle))
        pie_chart(
            "Occupation collar signal · 2020–2025",
            Counter(row["occupation_collar_category"] for row in enriched),
            OUT / "collar_overall_pie.png",
            COLLAR_COLORS,
        )
        pie_chart(
            "Industry signal · 2020–2025",
            Counter(row["industry_category"] for row in enriched),
            OUT / "industry_overall_pie.png",
            INDUSTRY_COLORS,
        )

    print(f"Wrote full-span charts to {OUT}")


if __name__ == "__main__":
    main()
