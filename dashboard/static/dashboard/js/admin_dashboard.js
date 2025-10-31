const translate = typeof window !== "undefined" && typeof window.gettext === "function"
  ? window.gettext
  : (value) => value;

const parseChartData = (elementId) => {
  const scriptElement = document.getElementById(elementId);
  if (!scriptElement) {
    return null;
  }

  try {
    return JSON.parse(scriptElement.textContent || "{}");
  } catch (error) {
    console.error(`Não foi possível interpretar os dados do gráfico "${elementId}".`, error);
    return null;
  }
};

const buildPalette = (length) => {
  const palette = [
    "rgb(59 130 246)", // azul
    "rgb(16 185 129)", // verde
    "rgb(249 115 22)", // laranja
    "rgb(236 72 153)", // rosa
    "rgb(139 92 246)", // roxo
    "rgb(14 165 233)", // ciano
    "rgb(245 158 11)", // âmbar
  ];

  return Array.from({ length }, (_, index) => palette[index % palette.length]);
};

const initMembersChart = (chartData) => {
  if (!chartData || !Array.isArray(chartData.labels) || !Array.isArray(chartData.series)) {
    return;
  }

  const canvas = document.getElementById("membros-chart");
  if (!canvas || typeof window.Chart !== "function") {
    return;
  }

  const backgroundColors = buildPalette(chartData.series.length);

  new window.Chart(canvas, {
    type: "pie",
    data: {
      labels: chartData.labels,
      datasets: [
        {
          label: translate("Total de membros"),
          data: chartData.series,
          backgroundColor: backgroundColors,
          borderWidth: 1,
          borderColor: "rgba(255, 255, 255, 0.9)",
          hoverOffset: 8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            boxWidth: 12,
            color: getComputedStyle(document.documentElement).getPropertyValue("--text-primary") || "#0f172a",
          },
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const value = context.parsed;
              const label = context.label || translate("Valor");
              return `${label}: ${value}`;
            },
          },
        },
      },
    },
  });
};

const initEventsByNucleoChart = (chartData) => {
  if (!chartData || !Array.isArray(chartData.labels) || !Array.isArray(chartData.series)) {
    return;
  }

  const canvas = document.getElementById("eventos-nucleo-chart");
  if (!canvas || typeof window.Chart !== "function") {
    return;
  }

  const backgroundColors = buildPalette(chartData.series.length);

  new window.Chart(canvas, {
    type: "bar",
    data: {
      labels: chartData.labels,
      datasets: [
        {
          label: translate("Eventos"),
          data: chartData.series,
          backgroundColor: backgroundColors,
          borderRadius: 6,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            title: (items) => (items?.[0]?.label ? items[0].label : translate("Núcleo")),
            label: (context) => `${translate("Eventos")}: ${context.parsed.y}`,
          },
        },
      },
      scales: {
        x: {
          ticks: {
            color: getComputedStyle(document.documentElement).getPropertyValue("--text-muted") || "#475569",
            maxRotation: 45,
            minRotation: 0,
            autoSkip: false,
          },
        },
        y: {
          beginAtZero: true,
          ticks: {
            color: getComputedStyle(document.documentElement).getPropertyValue("--text-muted") || "#475569",
            precision: 0,
            stepSize: 1,
          },
        },
      },
    },
  });
};

const membersChartData = parseChartData("membros-chart-data");
const eventsByNucleoData = parseChartData("eventos-por-nucleo-data");

initMembersChart(membersChartData);
initEventsByNucleoChart(eventsByNucleoData);
