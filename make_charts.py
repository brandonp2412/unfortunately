#!/usr/bin/env python3
"""Create lightweight PNG charts without external plotting dependencies."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "charts"
FONT = ImageFont.load_default()
COLORS = {
    # Green consistently denotes an employee-favourable result or signal.
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
    "white_collar": "#253B6E",   # navy
    "blue_collar": "#2F80B7",    # blue
    "pink_collar": "#E978A8",    # pink
    "not_stated": "#B8C2CC",     # grey
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


def rows() -> list[dict[str, str]]:
    with (ROOT / "output" / "combined_2020_2025_full_classification.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def baseline_rows() -> list[dict[str, str]]:
    """Load the manually reviewed 2024 baseline export for the focused chart."""
    with (ROOT / "output" / "baseline_substantive_claims.csv").open(newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("included_in_baseline") == "yes"]


def bar_chart(title: str, labels: list[str], series: dict[str, list[int]], path: Path, stacked: bool = False) -> None:
    width, height, left, bottom, top = 1100, 650, 100, 110, 70
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((left, 25), title, fill="#111111", font=FONT)
    max_value = max(sum(series[k][i] for k in series) if stacked else max(series[k][i] for k in series) for i in range(len(labels))) or 1
    chart_h, chart_w = height - bottom - top, width - left - 40
    bar_w = max(12, chart_w // (len(labels) * 2))
    for i, label in enumerate(labels):
        x = left + (i + 0.5) * chart_w / len(labels)
        draw.text((x - 12, height - bottom + 12), label, fill="#333333", font=FONT)
        y_base = height - bottom
        running = 0
        for key, values in series.items():
            value = values[i]
            h = int(value / max_value * chart_h)
            y1 = y_base - running - h
            y2 = y_base - running
            draw.rectangle((x - bar_w / 2, y1, x + bar_w / 2, y2), fill=COLORS.get(key, "#607D8B"))
            if not stacked:
                y_base -= h
            else:
                running += h
        draw.text((x - 10, max(40, y_base - 16)), str(sum(series[k][i] for k in series) if stacked else max(series[k][i] for k in series)), fill="#333333", font=FONT)
    for j in range(5):
        y = height - bottom - j * chart_h / 4
        draw.line((left, y, width - 40, y), fill="#DDDDDD")
    legend_x = left
    for key in series:
        draw.rectangle((legend_x, height - 35, legend_x + 12, height - 23), fill=COLORS.get(key, "#607D8B"))
        draw.text((legend_x + 18, height - 35), key, fill="#333333", font=FONT)
        legend_x += 145
    image.save(path)


def line_chart(title: str, labels: list[str], series: dict[str, list[float]], path: Path) -> None:
    """Draw a compact percentage line chart using only Pillow."""
    width, height, left, right, bottom, top = 1100, 650, 100, 55, 110, 70
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((left, 25), title, fill="#111111", font=FONT)
    chart_w, chart_h = width - left - right, height - bottom - top
    for tick in range(0, 101, 20):
        y = height - bottom - tick / 100 * chart_h
        draw.line((left, y, width - right, y), fill="#DDDDDD")
        draw.text((left - 30, y - 6), f"{tick}%", fill="#333333", font=FONT)
    colors = [COLORS["employee_win"], "#287C8E"]
    for idx, (name, values) in enumerate(series.items()):
        points = []
        for i, value in enumerate(values):
            x = left + i * chart_w / (len(labels) - 1)
            y = height - bottom - value / 100 * chart_h
            points.append((x, y))
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=colors[idx % len(colors)])
            draw.text((x - 14, y - 22), f"{value:.1f}", fill=colors[idx % len(colors)], font=FONT)
        if len(points) > 1:
            draw.line(points, fill=colors[idx % len(colors)], width=4)
    for i, label in enumerate(labels):
        x = left + i * chart_w / (len(labels) - 1)
        draw.text((x - 12, height - bottom + 12), label, fill="#333333", font=FONT)
    legend_x = left
    for idx, name in enumerate(series):
        color = colors[idx % len(colors)]
        draw.line((legend_x, height - 30, legend_x + 16, height - 30), fill=color, width=4)
        draw.text((legend_x + 22, height - 35), name, fill="#333333", font=FONT)
        legend_x += 260
    image.save(path)


def pie_chart(title: str, counts: Counter[str], path: Path, semantic_colors: dict[str, str] | None = None) -> None:
    """Draw a labelled pie chart for a categorical distribution."""
    width, height = 1000, 650
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 25), title, fill="#111111", font=FONT)
    total = sum(counts.values()) or 1
    palette = ["#4E8B73", "#6C9FB3", "#84A98C", "#78A6A8", "#9BB7A5", "#A7B8C2", "#B8C2CC", "#C7D3D9"]
    box = (90, 100, 540, 550)
    start = 0.0
    for index, (label, count) in enumerate(counts.most_common()):
        extent = 360 * count / total
        color = (semantic_colors or {}).get(label, palette[index % len(palette)])
        draw.pieslice(box, start=start, end=start + extent, fill=color, outline="white")
        start += extent
    legend_x, legend_y = 610, 115
    for index, (label, count) in enumerate(counts.most_common()):
        color = (semantic_colors or {}).get(label, palette[index % len(palette)])
        draw.rectangle((legend_x, legend_y, legend_x + 16, legend_y + 16), fill=color)
        pct = 100 * count / total
        draw.text((legend_x + 25, legend_y - 1), f"{label}: {count} ({pct:.1f}%)", fill="#333333", font=FONT)
        legend_y += 30
    image.save(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = rows()
    years = [str(y) for y in range(2020, 2026)]
    by_year = defaultdict(Counter)
    serious = defaultdict(Counter)
    for row in data:
        by_year[row["year"]][row["classified_outcome"]] += 1
        serious[row["year"]][row["authority_serious_misconduct_finding"] or "not_reviewed"] += 1
    bar_chart("ERA corpus rows by year", years, {"included": [sum(by_year[y][k] for k in ("employee_win", "employer_win", "mixed_unclear")) for y in years], "excluded": [by_year[y]["excluded"] for y in years]}, OUT / "corpus_by_year.png")
    bar_chart("Outcome classification by year", years, {k: [by_year[y][k] for y in years] for k in ("employee_win", "employer_win", "mixed_unclear", "excluded")}, OUT / "outcomes_by_year.png", stacked=True)
    bar_chart("Serious-misconduct status by year", years, {k: [serious[y][k] for y in years] for k in ("confirmed_yes", "confirmed_no", "authority_not_determined", "not_alleged", "not_reviewed")}, OUT / "serious_status_by_year.png", stacked=True)
    reviewed = baseline_rows()
    labels = ["serious alleged", "not alleged"]
    bar_chart("2024 wins by serious-misconduct allegation", labels, {"employee_win": [sum(r["serious_misconduct_alleged"] == "yes" and r["outcome"] == "employee_win" for r in reviewed), sum(r["serious_misconduct_alleged"] == "no" and r["outcome"] == "employee_win" for r in reviewed)], "employer_win": [sum(r["serious_misconduct_alleged"] == "yes" and r["outcome"] == "employer_win" for r in reviewed), sum(r["serious_misconduct_alleged"] == "no" and r["outcome"] == "employer_win" for r in reviewed)]}, OUT / "2024_serious_vs_not.png", stacked=True)
    all_outcome_rates = []
    binary_rates = []
    for year in years:
        employee = by_year[year]["employee_win"]
        employer = by_year[year]["employer_win"]
        mixed = by_year[year]["mixed_unclear"]
        all_outcome_rates.append(100 * employee / (employee + employer + mixed) if employee + employer + mixed else 0)
        binary_rates.append(100 * employee / (employee + employer) if employee + employer else 0)
    line_chart("Employee win rate by year", years, {"all classified outcomes": all_outcome_rates, "binary outcomes only": binary_rates}, OUT / "employee_win_rate_by_year.png")
    pie_chart("Overall outcome classification", Counter(r["classified_outcome"] for r in data), OUT / "outcome_overall_pie.png", COLORS)
    pie_chart("Overall serious-misconduct status", Counter(r["authority_serious_misconduct_finding"] or "not_reviewed" for r in data), OUT / "serious_status_overall_pie.png", COLORS)
    enriched_path = ROOT / "output" / "combined_2020_2025_context_enriched.csv"
    if enriched_path.exists():
        with enriched_path.open(newline="") as f:
            enriched = list(csv.DictReader(f))
        pie_chart("Occupation collar signal", Counter(r["occupation_collar_category"] for r in enriched), OUT / "collar_overall_pie.png", COLLAR_COLORS)
        pie_chart("Industry signal", Counter(r["industry_category"] for r in enriched), OUT / "industry_overall_pie.png", INDUSTRY_COLORS)
    print(f"Wrote charts to {OUT}")


if __name__ == "__main__":
    main()
