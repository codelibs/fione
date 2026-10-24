// Charts under the strict CSP: each [data-chart] element names a JSON block (plain data, read
// with JSON.parse, never as markup) that is drawn with ECharts' canvas renderer. Tooltips are
// drawn on the canvas too (renderMode "richText"), so no HTML or inline style is added to the
// page. Colours come from the design tokens (resolved through hidden probe elements), the
// chart is redrawn when the theme changes, sized when its container gets a size (charts in a
// hidden tab start at zero) and animated only when motion is welcome.
(function () {
  "use strict";
  if (!window.echarts) return;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
  var charts = [];

  // A token's colour as the browser resolves it (custom properties holding light-dark()
  // read back unresolved, so a probe element styled by a class is read instead).
  function colours(figure) {
    function probe(name) {
      var el = figure.querySelector(".chart-probe-" + name);
      return el ? window.getComputedStyle(el).color : "#888";
    }
    return {
      text: probe("text"),
      muted: probe("muted"),
      primary: probe("primary"),
      grid: probe("grid"),
      axis: probe("axis"),
      surface: probe("surface"),
      series: [probe("primary"), probe("c2"), probe("c3"), probe("c4")],
    };
  }

  // Several point series (one per model family) and a line (the best score so far). Each
  // series has its own symbol as well as its own colour, and a legend names them.
  var SYMBOLS = ["circle", "rect", "triangle", "diamond", "pin", "arrow", "roundRect"];
  function scatterOption(spec, c) {
    var axis = function (name) {
      return {
        type: "value",
        name: name,
        nameLocation: "middle",
        nameGap: 32,
        nameTextStyle: { color: c.muted },
        scale: true,
        axisLine: { lineStyle: { color: c.axis } },
        axisLabel: { color: c.muted },
        splitLine: { lineStyle: { color: c.grid } },
      };
    };
    var series = spec.series.map(function (s, i) {
      return {
        type: "scatter",
        name: s.name,
        data: s.points,
        symbol: SYMBOLS[i % SYMBOLS.length],
        symbolSize: 8,
        itemStyle: { color: c.series[i % c.series.length] },
      };
    });
    if (spec.line) {
      series.push({
        type: "line",
        name: spec.line.name,
        data: spec.line.points,
        step: "end",
        symbol: "none",
        lineStyle: { color: c.text, width: 2, type: "dashed" },
        itemStyle: { color: c.text },
      });
    }
    return {
      animation: !reduceMotion.matches,
      aria: { enabled: true, label: { description: spec.label } },
      textStyle: { color: c.text, fontFamily: window.getComputedStyle(document.body).fontFamily },
      legend: { top: 0, textStyle: { color: c.text } },
      grid: { left: 12, right: 24, top: 40, bottom: 44, containLabel: true },
      tooltip: {
        trigger: "item",
        renderMode: "richText",
        backgroundColor: c.surface,
        borderColor: c.axis,
        textStyle: { color: c.text },
      },
      xAxis: axis(spec.x_name),
      yAxis: axis(spec.y_name),
      series: series,
    };
  }

  function option(spec, c, width) {
    var horizontal = spec.type === "hbar";
    var labelWidth = Math.max(80, Math.min(260, Math.round(width * 0.4)));
    var categoryAxis = {
      type: "category",
      data: spec.labels,
      inverse: horizontal, // the first (largest) on top
      axisLine: { lineStyle: { color: c.axis } },
      axisTick: { lineStyle: { color: c.axis } },
      axisLabel: { color: c.muted, width: labelWidth, overflow: "truncate", hideOverlap: true },
      name: horizontal ? "" : spec.x_name,
      nameLocation: "middle",
      nameGap: 28,
      nameTextStyle: { color: c.muted },
    };
    var valueAxis = {
      type: "value",
      min: spec.min,
      max: spec.max,
      axisLine: { lineStyle: { color: c.axis } },
      axisLabel: { color: c.muted },
      splitLine: { lineStyle: { color: c.grid } },
      name: horizontal ? spec.x_name : spec.y_name,
      nameLocation: "middle",
      nameGap: horizontal ? 28 : 44,
      nameTextStyle: { color: c.muted },
    };
    return {
      animation: !reduceMotion.matches,
      // ECharts writes its description into the element's aria-label, in English: keep ours.
      aria: { enabled: true, label: { description: spec.label } },
      textStyle: { color: c.text, fontFamily: window.getComputedStyle(document.body).fontFamily },
      // Horizontal bars: room for the labels set aside explicitly (they are truncated to it).
      grid: horizontal
        ? { left: labelWidth + 16, right: 24, top: 16, bottom: 44 }
        : { left: 8, right: 24, top: 16, bottom: 32, containLabel: true },
      tooltip: {
        trigger: "axis",
        renderMode: "richText",
        backgroundColor: c.surface,
        borderColor: c.axis,
        textStyle: { color: c.text },
        axisPointer: { type: "shadow" },
      },
      xAxis: horizontal ? valueAxis : categoryAxis,
      yAxis: horizontal ? categoryAxis : valueAxis,
      series: [
        {
          type: "bar",
          data: spec.values,
          itemStyle: { color: c.primary, borderRadius: horizontal ? [0, 3, 3, 0] : [3, 3, 0, 0] },
          barMaxWidth: 28,
        },
      ],
    };
  }

  function draw(entry) {
    var c = colours(entry.figure);
    var built =
      entry.spec.type === "scatter"
        ? scatterOption(entry.spec, c)
        : option(entry.spec, c, entry.el.clientWidth);
    entry.chart.setOption(built, true);
  }

  document.querySelectorAll("[data-chart]").forEach(function (el) {
    var source = document.getElementById(el.getAttribute("data-chart"));
    if (!source) return;
    var spec = JSON.parse(source.textContent);
    var entry = { el: el, spec: spec, figure: el.closest("figure"), chart: null };
    charts.push(entry);
    // Started once the element has a size: a chart in a hidden tab waits until it is shown.
    new ResizeObserver(function () {
      if (!el.clientWidth || !el.clientHeight) return;
      if (!entry.chart) {
        entry.chart = window.echarts.init(el, null, { renderer: "canvas" });
        draw(entry);
      } else {
        entry.chart.resize();
        draw(entry); // the label width follows the chart's width
      }
    }).observe(el);
  });

  function redraw() {
    charts.forEach(function (entry) {
      if (entry.chart) draw(entry);
    });
  }
  new MutationObserver(redraw).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  darkQuery.addEventListener("change", redraw);
  reduceMotion.addEventListener("change", redraw);
})();
