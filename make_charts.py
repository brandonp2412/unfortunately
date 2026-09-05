#!/usr/bin/env python3
"""Create mobile-friendly PNG charts for the full ERA dataset."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "charts"
BACKGROUND = "#0B0F14"
SURFACE = "#111821"
SURFACE_RAISED = "#18212C"
GRID = "#263341"
BORDER = "#202B36"
TEXT_PRIMARY = "#F4F7FA"
TEXT_SECONDARY = "#C4CDD6"
TEXT_MUTED = "#8E9AA7"

COLORS = {
    "employee_win": "#39D173",
    "employer_win": "#FF6B6B",
    "excluded": "#647180",
    "included": "#4CC9AE",
    "confirmed_yes": "#FF6B6B",
    "confirmed_no": "#39D173",
    "authority_not_determined": "#75A9C6",
    "not_alleged": "#8AC7A3",
    "not_reviewed": "#4F5C69",
}
COLLAR_COLORS = {
    "white_collar": "#6C8EE8",
    "blue_collar": "#4DB6E8",
    "pink_collar": "#F28AB8",
    "not_stated": "#647180",
}
INDUSTRY_COLORS = {
    "healthcare": "#35C6B2",
    "education": "#A77BE8",
    "hospitality": "#F4A24B",
    "construction": "#C47B66",
    "retail": "#5E9FE8",
    "transport": "#E0BE54",
    "public_sector": "#7BC96F",
    "not_stated": "#647180",
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


TITLE_FONT = font(36, bold=True)
LABEL_FONT = font(27)
AXIS_FONT = font(22)
SMALL_FONT = font(21)
VALUE_FONT = font(24, bold=True)
LEGEND_FONT = font(23)
EDGE_PADDING = 56


def pretty(label: str) -> str:
    return label.replace("_", " ")


def text_width(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.ImageFont) -> float:
    box = draw.textbbox((0, 0), text, font=text_font)
    return box[2] - box[0]


def inset_text_x(
    draw: ImageDraw.ImageDraw,
    text: str,
    text_font: ImageFont.ImageFont,
    desired_x: float,
    image_width: int,
    *,
    padding: int = EDGE_PADDING,
) -> float:
    """Clamp text horizontally so labels always retain a visible outer gutter."""
    width = text_width(draw, text, text_font)
    return min(max(desired_x, padding), image_width - padding - width)


def text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    text_font: ImageFont.ImageFont,
) -> tuple[float, float]:
    box = draw.textbbox((0, 0), text, font=text_font)
    return box[2] - box[0], box[3] - box[1]


def boxes_overlap(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
    *,
    gap: float = 0,
) -> bool:
    return not (
        first[2] + gap <= second[0]
        or second[2] + gap <= first[0]
        or first[3] + gap <= second[1]
        or second[3] + gap <= first[1]
    )


def segment_box(
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    padding: float = 8,
) -> tuple[float, float, float, float]:
    """Return a padded segment envelope used to keep annotations off trend lines."""
    return (
        min(start[0], end[0]) - padding,
        min(start[1], end[1]) - padding,
        max(start[0], end[0]) + padding,
        max(start[1], end[1]) + padding,
    )


def place_line_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    point: tuple[float, float],
    plot_bounds: tuple[float, float, float, float],
    occupied: list[tuple[float, float, float, float]],
    line_boxes: list[tuple[float, float, float, float]],
    *,
    prefer_above: bool,
) -> tuple[float, float, float, float]:
    """Choose a readable annotation position away from lines and other labels."""
    x, y = point
    text_w, text_h = text_size(draw, text, SMALL_FONT)
    pad_x, pad_y = 5, 3
    left, top, right, bottom = plot_bounds
    directions = (-1, 1) if prefer_above else (1, -1)
    candidates: list[tuple[float, float]] = []
    for direction in directions:
        for gap in (18, 40, 62):
            candidate_y = y - text_h - gap if direction < 0 else y + gap
            candidates.extend([
                (x - text_w / 2, candidate_y),
                (x + 14, candidate_y),
                (x - text_w - 14, candidate_y),
            ])

    def clamp(candidate: tuple[float, float]) -> tuple[float, float, float, float]:
        candidate_x, candidate_y = candidate
        candidate_x = min(max(candidate_x, left + 4), right - text_w - 4)
        candidate_y = min(max(candidate_y, top + 4), bottom - text_h - 4)
        return (
            candidate_x - pad_x,
            candidate_y - pad_y,
            candidate_x + text_w + pad_x,
            candidate_y + text_h + pad_y,
        )

    boxes: list[tuple[float, float, float, float]] = []
    for candidate in candidates:
        box = clamp(candidate)
        if box not in boxes:
            boxes.append(box)

    for box in boxes:
        if any(boxes_overlap(box, used, gap=4) for used in occupied):
            continue
        if any(boxes_overlap(box, line_box) for line_box in line_boxes):
            continue
        return box

    def overlap_area(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> float:
        width = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
        height = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
        return width * height

    # If the plot is too dense for a completely clear position, never sacrifice
    # label-to-label readability: line overlap is cheaper because the text halo
    # masks the line underneath it.
    return min(
        boxes,
        key=lambda box: (
            sum(overlap_area(box, used) for used in occupied) * 1000
            + sum(overlap_area(box, line_box) for line_box in line_boxes)
        ),
    )


def box_anchor_for_point(
    point: tuple[float, float],
    box: tuple[float, float, float, float],
) -> tuple[float, float]:
    """Return the nearest point on a label box for a short leader line."""
    x, y = point
    left, top, right, bottom = box
    anchor_x = min(max(x, left), right)
    anchor_y = min(max(y, top), bottom)

    if left < x < right and top < y < bottom:
        distances = {
            (left, y): x - left,
            (right, y): right - x,
            (x, top): y - top,
            (x, bottom): bottom - y,
        }
        return min(distances, key=distances.get)
    return anchor_x, anchor_y


def draw_title(draw: ImageDraw.ImageDraw, title: str, image_width: int) -> None:
    """Center a title and shrink it only as much as needed to preserve edge padding."""
    title_font = TITLE_FONT
    max_width = image_width - 2 * EDGE_PADDING
    if text_width(draw, title, title_font) > max_width:
        for size in range(35, 25, -1):
            candidate = font(size, bold=True)
            if text_width(draw, title, candidate) <= max_width:
                title_font = candidate
                break
    x = (image_width - text_width(draw, title, title_font)) / 2
    draw.text((x, 48), title, fill=TEXT_PRIMARY, font=title_font)


def recent_rows() -> list[dict[str, str]]:
    path = ROOT / "output" / "combined_2020_2025_binary_classification.csv"
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
        {"year": row["year"], "classified_outcome": row["binary_outcome"]}
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
    width = 920
    top, bottom, left, right = 120, 175, 148, 140
    row_h = 60
    height = top + bottom + row_h * len(labels)
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw_title(draw, title, width)
    chart_w = width - left - right
    totals = [sum(series[key][i] for key in series) for i in range(len(labels))]
    max_value = max(totals) or 1

    for i, label in enumerate(labels):
        y = top + i * row_h + 9
        label_x = left - 24 - text_width(draw, label, LABEL_FONT)
        draw.text((label_x, y + 5), label, fill=TEXT_SECONDARY, font=LABEL_FONT)
        draw.rounded_rectangle(
            (left, y, width - right, y + 33),
            radius=6,
            fill=SURFACE_RAISED,
        )
        x = left
        for key, values in series.items():
            value = values[i]
            seg_w = chart_w * value / max_value
            draw.rounded_rectangle(
                (x, y, x + seg_w, y + 33),
                radius=5,
                fill=COLORS.get(key, "#7A8795"),
            )
            x += seg_w
        total_text = str(totals[i])
        total_x = inset_text_x(draw, total_text, AXIS_FONT, x + 9, width)
        draw.text((total_x, y + 3), total_text, fill=TEXT_SECONDARY, font=AXIS_FONT)

    legend_items = list(series)
    columns = 2
    legend_y = height - 124
    col_w = 395
    for idx, key in enumerate(legend_items):
        col = idx % columns
        row = idx // columns
        x = left + col * col_w
        y = legend_y + row * 42
        draw.rounded_rectangle((x, y, x + 22, y + 22), radius=4, fill=COLORS.get(key, "#7A8795"))
        draw.text((x + 32, y - 3), pretty(key), fill=TEXT_SECONDARY, font=LEGEND_FONT)

    image.save(path, optimize=True)


def vertical_bar_chart(
    title: str,
    labels: list[str],
    series: dict[str, list[int]],
    path: Path,
    *,
    stacked: bool = False,
) -> None:
    many_legend_items = len(series) > 3
    width = 920
    height = 950 if many_legend_items else 870
    left, right, top = 118, 58, 120
    bottom = 280 if many_legend_items else 205
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw_title(draw, title, width)
    max_value = max(
        sum(series[k][i] for k in series) if stacked else max(series[k][i] for k in series)
        for i in range(len(labels))
    ) or 1
    chart_h, chart_w = height - bottom - top, width - left - right
    draw.rounded_rectangle(
        (left - 14, top - 12, width - right + 14, height - bottom + 12),
        radius=18,
        fill=SURFACE,
        outline=BORDER,
        width=2,
    )
    slot_w = chart_w / max(1, len(labels))
    bar_w = max(38, min(86, int(slot_w * 0.58)))

    for j in range(5):
        y = height - bottom - j * chart_h / 4
        draw.line((left, y, width - right, y), fill=GRID, width=2)
        tick_text = str(round(max_value * j / 4))
        draw.text(
            (left - text_width(draw, tick_text, SMALL_FONT) - 14, y - 13),
            tick_text,
            fill=TEXT_MUTED,
            font=SMALL_FONT,
        )

    for i, label in enumerate(labels):
        x = left + (i + 0.5) * chart_w / len(labels)
        label_text = pretty(label)
        label_x = inset_text_x(
            draw,
            label_text,
            LABEL_FONT,
            x - text_width(draw, label_text, LABEL_FONT) / 2,
            width,
        )
        draw.text(
            (label_x, height - bottom + 20),
            label_text,
            fill=TEXT_SECONDARY,
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
                fill=COLORS.get(key, "#7A8795"),
            )
            if stacked:
                running += h
            else:
                y_base -= h
        total = sum(series[k][i] for k in series) if stacked else max(series[k][i] for k in series)
        value_text = str(total)
        top_y = height - bottom - int(total / max_value * chart_h)
        draw.text(
            (x - text_width(draw, value_text, VALUE_FONT) / 2, max(top + 6, top_y - 32)),
            value_text,
            fill=TEXT_PRIMARY,
            font=VALUE_FONT,
        )

    legend_items = list(series)
    if many_legend_items:
        columns = 2
        col_w = 390
        legend_y = height - bottom + 88
        for idx, key in enumerate(legend_items):
            col = idx % columns
            row = idx // columns
            x = left + col * col_w
            y = legend_y + row * 47
            draw.rounded_rectangle(
                (x, y, x + 22, y + 22),
                radius=4,
                fill=COLORS.get(key, "#7A8795"),
            )
            draw.text((x + 32, y - 3), pretty(key), fill=TEXT_SECONDARY, font=LEGEND_FONT)
    else:
        legend_y = height - 82
        item_width = chart_w / max(1, len(legend_items))
        for idx, key in enumerate(legend_items):
            x = left + idx * item_width
            draw.rounded_rectangle(
                (x, legend_y, x + 22, legend_y + 22),
                radius=4,
                fill=COLORS.get(key, "#7A8795"),
            )
            draw.text((x + 32, legend_y - 3), pretty(key), fill=TEXT_SECONDARY, font=LEGEND_FONT)

    image.save(path, optimize=True)


def line_chart(title: str, labels: list[str], series: dict[str, list[float]], path: Path) -> None:
    width, height = 920, 870
    left, right, bottom, top = 130, 66, 190, 120
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw_title(draw, title, width)
    chart_w, chart_h = width - left - right, height - bottom - top
    plot_bounds = (left, top, width - right, height - bottom)
    draw.rounded_rectangle(
        (left - 14, top - 12, width - right + 14, height - bottom + 12),
        radius=18,
        fill=SURFACE,
        outline=BORDER,
        width=2,
    )

    for tick in range(0, 101, 20):
        y = height - bottom - tick / 100 * chart_h
        draw.line((left, y, width - right, y), fill=GRID, width=2)
        tick_text = f"{tick}%"
        draw.text(
            (left - text_width(draw, tick_text, SMALL_FONT) - 14, y - 13),
            tick_text,
            fill=TEXT_MUTED,
            font=SMALL_FONT,
        )

    colors = [COLORS["employee_win"], "#49B4D0"]
    rendered_series: list[tuple[int, str, list[float], list[tuple[float, float]]]] = []
    all_line_boxes: list[tuple[float, float, float, float]] = []

    for idx, (name, values) in enumerate(series.items()):
        points = [
            (
                left + i * chart_w / (len(labels) - 1),
                height - bottom - value / 100 * chart_h,
            )
            for i, value in enumerate(values)
        ]
        rendered_series.append((idx, name, values, points))
        for start, end in zip(points, points[1:]):
            all_line_boxes.append(segment_box(start, end))
        if len(points) > 1:
            draw.line(points, fill=colors[idx % len(colors)], width=6, joint="curve")
        for x, y in points:
            draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=SURFACE)
            draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=colors[idx % len(colors)])

    occupied_labels: list[tuple[float, float, float, float]] = []
    for idx, _name, values, points in rendered_series:
        color = colors[idx % len(colors)]
        for i, (value, point) in enumerate(zip(values, points)):
            if not (i % 2 == idx % 2 or i == len(labels) - 1):
                continue
            value_text = f"{value:.1f}%"
            label_box = place_line_label(
                draw,
                value_text,
                point,
                plot_bounds,
                occupied_labels,
                all_line_boxes,
                prefer_above=idx % 2 == 0,
            )
            occupied_labels.append(label_box)
            anchor = box_anchor_for_point(point, label_box)
            draw.line((point, anchor), fill=color, width=2)
            draw.ellipse(
                (point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3),
                fill=color,
            )
            draw.rounded_rectangle(
                label_box,
                radius=7,
                fill=SURFACE_RAISED,
                outline=color,
                width=2,
            )
            text_x = label_box[0] + 5
            text_y = label_box[1] + 3
            draw.text(
                (text_x, text_y),
                value_text,
                fill=color,
                font=SMALL_FONT,
            )

    for i, label in enumerate(labels):
        x = left + i * chart_w / (len(labels) - 1)
        short_label = label[2:] if len(labels) > 10 else label
        label_x = inset_text_x(
            draw,
            short_label,
            AXIS_FONT,
            x - text_width(draw, short_label, AXIS_FONT) / 2,
            width,
        )
        draw.text(
            (label_x, height - bottom + 20),
            short_label,
            fill=TEXT_SECONDARY,
            font=AXIS_FONT,
        )
    if len(labels) > 10:
        draw.text(
            (left, height - bottom + 60),
            "Years shown as 10–25 = 2010–2025",
            fill=TEXT_MUTED,
            font=SMALL_FONT,
        )

    legend_y = height - 84
    item_width = chart_w / max(1, len(series))
    for idx, name in enumerate(series):
        x = left + idx * item_width
        color = colors[idx % len(colors)]
        draw.line((x, legend_y + 11, x + 30, legend_y + 11), fill=color, width=6)
        draw.text((x + 40, legend_y - 3), pretty(name), fill=TEXT_SECONDARY, font=LEGEND_FONT)

    image.save(path, optimize=True)


def pie_chart(
    title: str,
    counts: Counter[str],
    path: Path,
    semantic_colors: dict[str, str] | None = None,
) -> None:
    # Extra outer and bottom whitespace prevents legends from touching image edges on mobile.
    width, height = 940, 1080
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw_title(draw, title, width)
    total = sum(counts.values()) or 1
    palette = [
        "#4CC9AE",
        "#49B4D0",
        "#78C091",
        "#6EAEB2",
        "#91B8A5",
        "#8497A8",
        "#647180",
        "#A2AFBA",
    ]
    box = (150, 125, 790, 765)
    start = 0.0
    ordered = counts.most_common()
    for index, (label, count) in enumerate(ordered):
        extent = 360 * count / total
        color = (semantic_colors or {}).get(label, palette[index % len(palette)])
        draw.pieslice(box, start=start, end=start + extent, fill=color, outline=BACKGROUND, width=4)
        start += extent

    draw.ellipse((325, 300, 615, 590), fill=BACKGROUND)
    total_text = f"{total:,}"
    draw.text(
        ((width - text_width(draw, total_text, TITLE_FONT)) / 2, 405),
        total_text,
        fill=TEXT_PRIMARY,
        font=TITLE_FONT,
    )
    draw.text(
        ((width - text_width(draw, "cases", LABEL_FONT)) / 2, 455),
        "cases",
        fill=TEXT_MUTED,
        font=LABEL_FONT,
    )

    legend_x, legend_y = 90, 835
    columns = 2 if len(ordered) > 4 else 1
    col_width = 430
    row_height = 48
    rows_per_col = (len(ordered) + columns - 1) // columns
    for index, (label, count) in enumerate(ordered):
        col = index // rows_per_col
        row = index % rows_per_col
        x = legend_x + col * col_width
        y = legend_y + row * row_height
        color = (semantic_colors or {}).get(label, palette[index % len(palette)])
        draw.rounded_rectangle((x, y, x + 24, y + 24), radius=4, fill=color)
        pct = 100 * count / total
        draw.text(
            (x + 36, y - 3),
            f"{pretty(label)}  {count} · {pct:.1f}%",
            fill=TEXT_SECONDARY,
            font=SMALL_FONT,
        )

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
            "included": [
                by_year[y]["employee_win"] + by_year[y]["employer_win"]
                for y in years
            ],
            "excluded": [by_year[y]["excluded"] for y in years],
        },
        OUT / "corpus_by_year.png",
    )
    horizontal_year_chart(
        "Outcome classification · 2010–2025",
        years,
        {
            key: [by_year[y][key] for y in years]
            for key in ("employee_win", "employer_win", "excluded")
        },
        OUT / "outcomes_by_year.png",
    )

    rates = []
    for year in years:
        employee = by_year[year]["employee_win"]
        employer = by_year[year]["employer_win"]
        rates.append(100 * employee / (employee + employer) if employee + employer else 0)
    line_chart(
        "Employee win rate · 2010–2025",
        years,
        {"employee win rate": rates},
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
        {
            key: [serious[y][key] for y in serious_years]
            for key in (
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
                sum(
                    row["serious_misconduct_alleged"] == "yes"
                    and row["outcome"] == "employee_win"
                    for row in reviewed
                ),
                sum(
                    row["serious_misconduct_alleged"] == "no"
                    and row["outcome"] == "employee_win"
                    for row in reviewed
                ),
            ],
            "employer_win": [
                sum(
                    row["serious_misconduct_alleged"] == "yes"
                    and row["outcome"] == "employer_win"
                    for row in reviewed
                ),
                sum(
                    row["serious_misconduct_alleged"] == "no"
                    and row["outcome"] == "employer_win"
                    for row in reviewed
                ),
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
