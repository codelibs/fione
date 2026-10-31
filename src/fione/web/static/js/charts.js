// Charts under the strict CSP: each [data-chart] element names a JSON block (plain data, read
// with JSON.parse, never as markup) that is drawn with ECharts' canvas renderer; in fragments
// HTMX swaps in (which lose their script elements), [data-chart-spec] holds the JSON itself. Tooltips are
// drawn on the canvas too (renderMode "richText"), so no HTML or inline style is added to the
// page. Colours come from the design tokens (resolved through hidden probe elements), the
// chart is redrawn when the theme changes, sized when its container gets a size (charts in a
// hidden tab start at zero) and animated only when motion is welcome. Charts are found at
// start-up and in content HTMX adds (each element is set up once: data-chart-ready); charts
// whose element HTMX has taken out of the page are released then.
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
    var axis = function (name, horizontal) {
      return {
        type: "value",
        name: name,
        // the x name centred below the axis; the y name above it, unrotated
        nameLocation: horizontal ? "middle" : "end",
        nameGap: horizontal ? 32 : 14,
        nameTextStyle: { color: c.muted, align: horizontal ? "center" : "left" },
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
        step: spec.line.step === undefined ? "end" : spec.line.step,
        symbol: "none",
        lineStyle: { color: c.text, width: 2, type: "dashed" },
        itemStyle: { color: c.text },
      });
    }
    return {
      animation: !reduceMotion.matches,
      aria: { enabled: true, label: { description: spec.label } },
      textStyle: { color: c.text, fontFamily: window.getComputedStyle(document.body).fontFamily },
      // The legend below the plot, so a wrapped legend on a phone never covers it.
      legend: { bottom: 0, textStyle: { color: c.text } },
      grid: { left: 12, right: 24, top: 36, bottom: 96, containLabel: true },
      tooltip: {
        trigger: "item",
        renderMode: "richText",
        backgroundColor: c.surface,
        borderColor: c.axis,
        textStyle: { color: c.text },
      },
      xAxis: axis(spec.x_name, true),
      yAxis: axis(spec.y_name, false),
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

  // Curves (ROC, precision-recall, calibration, partial dependence): one line per series on a
  // value or category x axis (category points are [index, y], in the order of ``categories``).
  // Faint series (a reference diagonal, single-row curves) are thin and muted, dashed unless
  // ``solid``, left out of the legend and silent; short series show their points.
  function linesOption(spec, c) {
    var onCategories = spec.x_type === "category";
    var data = function (points) {
      return onCategories
        ? points.map(function (p) {
            return p[1];
          })
        : points;
    };
    var axis = function (horizontal) {
      var category = horizontal && onCategories;
      return {
        type: category ? "category" : "value",
        data: category ? spec.categories : undefined,
        name: horizontal ? spec.x_name : spec.y_name,
        nameLocation: horizontal ? "middle" : "end",
        nameGap: horizontal ? 32 : 14,
        nameTextStyle: { color: c.muted, align: horizontal ? "center" : "left" },
        min: horizontal ? spec.x_min : spec.y_min,
        max: horizontal ? spec.x_max : spec.y_max,
        scale: true,
        axisLine: { lineStyle: { color: c.axis } },
        axisLabel: { color: c.muted, hideOverlap: true },
        splitLine: { lineStyle: { color: c.grid } },
      };
    };
    var shown = 0;
    var series = spec.series.map(function (s) {
      if (s.faint) {
        return {
          type: "line",
          name: s.name,
          data: data(s.points),
          symbol: "none",
          silent: true,
          tooltip: { show: false },
          lineStyle: {
            color: c.muted,
            width: 1,
            type: s.solid ? "solid" : "dashed",
            opacity: s.solid ? 0.45 : 1,
          },
          itemStyle: { color: c.muted },
          z: 1,
        };
      }
      var colour = c.series[shown++ % c.series.length];
      return {
        type: "line",
        name: s.name,
        data: data(s.points),
        symbol: SYMBOLS[(shown - 1) % SYMBOLS.length],
        showSymbol: s.points.length <= 20,
        symbolSize: 7,
        lineStyle: { color: colour, width: 2 },
        itemStyle: { color: colour },
        z: 2,
      };
    });
    return {
      animation: !reduceMotion.matches,
      aria: { enabled: true, label: { description: spec.label } },
      textStyle: { color: c.text, fontFamily: window.getComputedStyle(document.body).fontFamily },
      legend: {
        bottom: 0,
        textStyle: { color: c.text },
        data: spec.series
          .filter(function (s) {
            return !s.faint;
          })
          .map(function (s) {
            return s.name;
          }),
      },
      grid: { left: 12, right: 24, top: 36, bottom: 72, containLabel: true },
      tooltip: {
        trigger: "item",
        renderMode: "richText",
        backgroundColor: c.surface,
        borderColor: c.axis,
        textStyle: { color: c.text },
      },
      xAxis: axis(true),
      yAxis: axis(false),
      series: series,
    };
  }

  function draw(entry) {
    var c = colours(entry.figure);
    var type = entry.spec.type;
    var built =
      type === "scatter"
        ? scatterOption(entry.spec, c)
        : type === "lines"
          ? linesOption(entry.spec, c)
          : option(entry.spec, c, entry.el.clientWidth);
    entry.chart.setOption(built, true);
  }

  function setUp(el) {
    if (el.hasAttribute("data-chart-ready")) return;
    var text = el.getAttribute("data-chart-spec");
    if (text === null) {
      var source = document.getElementById(el.getAttribute("data-chart"));
      if (!source) return;
      text = source.textContent;
    }
    el.setAttribute("data-chart-ready", "");
    var spec;
    try {
      spec = JSON.parse(text);
    } catch (error) {
      // One unreadable spec leaves its chart blank (the text alternative stays), never the rest.
      console.warn("a chart's data could not be read", error);
      return;
    }
    var entry = { el: el, spec: spec, figure: el.closest("figure"), chart: null, observer: null };
    charts.push(entry);
    // Started once the element has a size: a chart in a hidden tab waits until it is shown.
    entry.observer = new ResizeObserver(function () {
      if (!el.clientWidth || !el.clientHeight) return;
      if (!entry.chart) {
        entry.chart = window.echarts.init(el, null, { renderer: "canvas" });
        draw(entry);
      } else {
        entry.chart.resize();
        draw(entry); // the label width follows the chart's width
      }
    });
    entry.observer.observe(el);
  }

  // Charts whose element is no longer in the page (HTMX swapped it out): their ECharts
  // instance, observer and entry go, so swapped fragments do not pile up.
  function release() {
    charts = charts.filter(function (entry) {
      if (entry.el.isConnected) return true;
      entry.observer.disconnect();
      if (entry.chart) entry.chart.dispose();
      return false;
    });
  }

  // The charts in ``root`` (the element itself included) not set up yet.
  function scan(root) {
    var selector = "[data-chart], [data-chart-spec]";
    if (root.matches && root.matches(selector)) setUp(root);
    if (root.querySelectorAll) root.querySelectorAll(selector).forEach(setUp);
  }

  scan(document);
  document.addEventListener("htmx:load", function (event) {
    release();
    scan(event.target);
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
