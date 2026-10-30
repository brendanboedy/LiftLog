// Draws the two progress charts (FR-32). The numbers come from the JSON block on the page.
(function () {
  if (typeof Chart === "undefined") return; // chart library didn't load; the table below still shows the numbers

  var points = JSON.parse(document.getElementById("progress-data").textContent);
  var css = getComputedStyle(document.documentElement);
  var accent = css.getPropertyValue("--accent").trim();
  var text = css.getPropertyValue("--text-muted").trim();
  var line = css.getPropertyValue("--line").trim();
  var font = css.getPropertyValue("--font").trim();

  Chart.defaults.color = text;
  Chart.defaults.font.family = font;

  function draw(canvasId, key, label) {
    new Chart(document.getElementById(canvasId), {
      type: "line",
      data: {
        labels: points.map(function (p) { return p.date; }),
        datasets: [{
          label: label,
          data: points.map(function (p) { return p[key]; }),
          borderColor: accent,
          backgroundColor: accent,
          pointRadius: 4,
          tension: 0, // straight lines: a curve can bend past the real numbers
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel: function (item) { return points[item.dataIndex].workout; },
            },
          },
        },
        scales: {
          x: { grid: { color: line }, ticks: { maxRotation: 0, autoSkipPadding: 16 } },
          y: { grid: { color: line }, beginAtZero: false, title: { display: true, text: label } },
        },
      },
    });
  }

  draw("weight-chart", "max_weight", "Weight (lb)");
  draw("volume-chart", "volume", "Volume");
})();
