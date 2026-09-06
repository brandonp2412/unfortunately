(() => {
  "use strict";

  const PAGE_SIZE = 24;
  const state = { summary: null, cases: [], filtered: [], page: 1, selectedYear: null };
  const $ = (selector) => document.querySelector(selector);
  const svgNS = "http://www.w3.org/2000/svg";

  const pct = (value) => value == null ? "—" : `${Number(value).toFixed(1)}%`;
  const number = (value) => Number(value || 0).toLocaleString("en-NZ");
  const outcomeLabel = (value) => value === "employee_win" ? "Employee win" : value === "employer_win" ? "Employer win" : "—";
  const outcomeClass = (value, kind) => value === "employee_win" ? `${kind}-win` : value === "employer_win" ? "employer-win" : "unknown";

  function setHeadlineStats() {
    const manifest = state.summary.manifest;
    const totals = manifest.totals;
    $("#legal-rate").textContent = pct(totals.legal.employee_win_rate);
    $("#legal-meta").textContent = `${number(totals.legal.employee_wins)} employee wins · ${number(totals.legal.cases)} classified`;
    $("#money-rate").textContent = pct(totals.monetary.employee_win_rate);
    $("#money-meta").textContent = `${number(totals.monetary.employee_wins)} employee wins · ${number(totals.monetary.cases)} determinations`;
    $("#disagreement-rate").textContent = pct(totals.paired.disagreement_rate);
    $("#paired-meta").textContent = `${number(totals.paired.disagreements)} of ${number(totals.paired.paired_cases)} paired cases`;
    $("#case-count").textContent = number(totals.paired.paired_cases);
    $("#legal-definition").textContent = `${manifest.measures.legal_merits.employee_win}.`;
    $("#money-definition").textContent = `${manifest.measures.monetary_outcome.employee_win}.`;
    $("#corpus-definition").textContent = `${manifest.corpus.description}. The source is search-derived and is not presented as a proven complete population.`;
  }

  function svgEl(name, attrs = {}) {
    const node = document.createElementNS(svgNS, name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    return node;
  }

  function updateChartSelection() {
    const svg = $("#rate-chart");
    svg.querySelectorAll(".chart-selection").forEach((node) => node.remove());
    const rows = state.summary.yearly;
    const index = rows.findIndex((row) => row.year === state.selectedYear);
    if (index < 0) return;
    const x = 58 + index * (960 - 58 - 28) / (rows.length - 1);
    const line = svgEl("line", { x1: x, y1: 28, x2: x, y2: 430 - 58, class: "chart-selection generated" });
    svg.insertBefore(line, svg.querySelector(".chart-path"));
  }

  function selectYear(year) {
    state.selectedYear = Number(year);
    $("#year-select").value = String(year);
    const row = state.summary.yearly.find((item) => item.year === state.selectedYear);
    if (!row) return;
    $("#detail-year").textContent = row.year;
    $("#detail-legal").textContent = pct(row.legal?.employee_win_rate);
    $("#detail-legal-cases").textContent = row.legal ? `${number(row.legal.cases)} classified cases` : "No legal data";
    $("#detail-money").textContent = pct(row.monetary?.employee_win_rate);
    $("#detail-money-cases").textContent = row.monetary ? `${number(row.monetary.cases)} determinations` : "No monetary data";
    $("#detail-disagreement").textContent = pct(row.comparison?.disagreement_rate);
    $("#detail-paired").textContent = row.comparison ? `${number(row.comparison.disagreements)} of ${number(row.comparison.paired_cases)} paired cases` : "No paired data";
    updateChartSelection();
  }

  function drawRateChart() {
    const svg = $("#rate-chart");
    const rows = state.summary.yearly;
    const W = 960, H = 430, left = 58, right = 28, top = 28, bottom = 58;
    const innerW = W - left - right, innerH = H - top - bottom;
    const x = (i) => left + i * innerW / (rows.length - 1);
    const y = (rate) => top + innerH - Number(rate) / 100 * innerH;

    for (let tick = 0; tick <= 100; tick += 20) {
      const py = y(tick);
      const line = svgEl("line", { x1: left, y1: py, x2: W - right, y2: py, class: "chart-grid generated" });
      const label = svgEl("text", { x: left - 12, y: py + 4, "text-anchor": "end", class: "chart-axis-label generated" });
      label.textContent = `${tick}%`;
      svg.append(line, label);
    }
    rows.forEach((row, i) => {
      const label = svgEl("text", { x: x(i), y: H - 22, "text-anchor": "middle", class: "chart-year-label generated" });
      label.textContent = String(row.year).slice(2);
      svg.appendChild(label);
    });

    const legalPoints = rows.map((row, i) => row.legal ? `${x(i)},${y(row.legal.employee_win_rate)}` : null).filter(Boolean).join(" ");
    const moneyPoints = rows.map((row, i) => row.monetary ? `${x(i)},${y(row.monetary.employee_win_rate)}` : null).filter(Boolean).join(" ");
    svg.append(
      svgEl("polyline", { points: legalPoints, class: "chart-path legal generated" }),
      svgEl("polyline", { points: moneyPoints, class: "chart-path money generated" }),
    );

    rows.forEach((row, i) => {
      [["legal", row.legal?.employee_win_rate], ["money", row.monetary?.employee_win_rate]].forEach(([kind, rate]) => {
        if (rate == null) return;
        const point = svgEl("circle", {
          cx: x(i), cy: y(rate), r: 5, class: `chart-point ${kind} generated`, tabindex: "0", role: "button",
          "aria-label": `${row.year} ${kind === "legal" ? "legal merits" : "monetary outcome"} employee win rate ${pct(rate)}`,
        });
        point.addEventListener("click", () => selectYear(row.year));
        point.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectYear(row.year); }
        });
        svg.appendChild(point);
      });
    });
    updateChartSelection();
  }

  function buildDisagreementBars() {
    const root = $("#disagreement-bars");
    state.summary.yearly.forEach((row) => {
      const rate = row.comparison?.disagreement_rate ?? 0;
      const item = document.createElement("div"); item.className = "bar-item"; item.title = `${row.year}: ${pct(rate)} disagreement`;
      const track = document.createElement("div"); track.className = "bar-track";
      const fill = document.createElement("div"); fill.className = "bar-fill"; fill.style.height = `${Math.max(1, Math.min(100, rate))}%`;
      const label = document.createElement("span"); label.className = "bar-label"; label.textContent = row.year;
      track.appendChild(fill); item.append(track, label); root.appendChild(item);
    });
  }

  function populateYears() {
    const chart = $("#year-select"), filter = $("#year-filter");
    for (const { year } of state.summary.yearly) {
      const a = document.createElement("option"); a.value = year; a.textContent = year; chart.appendChild(a);
      const b = document.createElement("option"); b.value = year; b.textContent = year; filter.appendChild(b);
    }
    chart.addEventListener("change", () => selectYear(chart.value));
    selectYear(state.summary.meta.year_end);
  }

  function caseCard(item) {
    const card = document.createElement("article"); card.className = "case-card";
    if (item.disagrees === "yes") card.classList.add("disagrees");

    const year = document.createElement("div"); year.className = "case-year"; year.textContent = item.year;
    const name = document.createElement("div"); name.className = "case-name";
    const strong = document.createElement("strong"); strong.textContent = item.case_name || "Unnamed determination";
    const citation = document.createElement("span"); citation.textContent = item.era_citation || "Citation unavailable"; name.append(strong, citation);

    const makeOutcome = (kind, value) => {
      const box = document.createElement("div"); box.className = `outcome ${kind}-outcome`;
      const label = document.createElement("span"); label.className = "outcome-label"; label.textContent = kind === "legal" ? "Legal merits" : "Monetary";
      const pill = document.createElement("span"); pill.className = `pill ${outcomeClass(value, kind)}`; pill.textContent = outcomeLabel(value);
      box.append(label, pill); return box;
    };

    const link = document.createElement("a"); link.className = "case-link"; link.href = item.pdf_url; link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = "↗";
    link.setAttribute("aria-label", `Open ERA determination for ${item.case_name || item.era_citation}`);
    card.append(year, name, makeOutcome("legal", item.legal_outcome), makeOutcome("money", item.monetary_outcome), link);
    return card;
  }

  function renderCases() {
    const list = $("#case-list"); list.replaceChildren();
    const total = state.filtered.length; $("#case-total").textContent = number(total);
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (!total) {
      const empty = document.createElement("div"); empty.className = "empty-state"; empty.textContent = "No cases match those filters."; list.appendChild(empty);
    } else {
      const start = (state.page - 1) * PAGE_SIZE;
      state.filtered.slice(start, start + PAGE_SIZE).forEach((item) => list.appendChild(caseCard(item)));
    }
    $("#page-status").textContent = total ? `Page ${state.page} of ${pages}` : "No results";
    $("#prev-page").disabled = state.page <= 1;
    $("#next-page").disabled = state.page >= pages;
  }

  function applyFilters() {
    const query = $("#search").value.trim().toLowerCase();
    const year = $("#year-filter").value, legal = $("#legal-filter").value, money = $("#money-filter").value;
    const disagreement = $("#disagreement-filter").checked, sort = $("#sort-filter").value;
    state.filtered = state.cases.filter((item) => {
      const haystack = `${item.case_name || ""} ${item.era_citation || ""}`.toLowerCase();
      if (query && !haystack.includes(query)) return false;
      if (year && String(item.year) !== year) return false;
      if (legal && item.legal_outcome !== legal) return false;
      if (money && item.monetary_outcome !== money) return false;
      if (disagreement && item.disagrees !== "yes") return false;
      return true;
    });
    state.filtered.sort((a, b) => sort === "oldest"
      ? Number(a.year) - Number(b.year) || (a.case_name || "").localeCompare(b.case_name || "")
      : sort === "name"
        ? (a.case_name || "").localeCompare(b.case_name || "") || Number(b.year) - Number(a.year)
        : Number(b.year) - Number(a.year) || (a.case_name || "").localeCompare(b.case_name || ""));
    state.page = 1; renderCases();
  }

  function bindExplorer() {
    ["year-filter", "legal-filter", "money-filter", "sort-filter", "disagreement-filter"].forEach((id) => $("#" + id).addEventListener("change", applyFilters));
    $("#search").addEventListener("input", applyFilters);
    $("#reset-filters").addEventListener("click", () => { $("#filters").reset(); applyFilters(); $("#search").focus(); });
    $("#prev-page").addEventListener("click", () => { if (state.page > 1) { state.page--; renderCases(); $("#cases").scrollIntoView({ block: "start" }); } });
    $("#next-page").addEventListener("click", () => { const pages = Math.ceil(state.filtered.length / PAGE_SIZE); if (state.page < pages) { state.page++; renderCases(); $("#cases").scrollIntoView({ block: "start" }); } });
    applyFilters();
  }

  async function init() {
    try {
      const [summaryResponse, casesResponse] = await Promise.all([fetch("./data/summary.json"), fetch("./data/cases.json")]);
      if (!summaryResponse.ok || !casesResponse.ok) throw new Error("Data request failed");
      state.summary = await summaryResponse.json(); state.cases = await casesResponse.json();
      setHeadlineStats(); populateYears(); drawRateChart(); buildDisagreementBars(); bindExplorer();
    } catch (error) {
      console.error(error);
      $("#case-list").textContent = "The interactive data could not be loaded. CSV downloads remain available in the Method section.";
    }
  }

  init();
})();
