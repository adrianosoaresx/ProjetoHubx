    document.addEventListener("DOMContentLoaded", () => {
      const chartsRegistry = new Map();

      function cloneFigure(figure) {
        if (typeof structuredClone === "function") {
          return structuredClone(figure);
        }
        return JSON.parse(JSON.stringify(figure));
      }

      function readThemeTokens() {
        const styles = getComputedStyle(document.documentElement);
        const pick = (variable, fallback) => {
          const value = styles.getPropertyValue(variable) || "";
          return value.trim() || fallback;
        };

        return {
          surface: pick("--bg-primary", "#ffffff"),
          border: pick("--border", "rgba(148, 163, 184, 0.4)"),
          textPrimary: pick("--text-primary", "#0f172a"),
          textMuted: pick("--text-secondary", "#475569"),
        };
      }

      function applyThemeToFigure(figure) {
        const themedFigure = cloneFigure(figure);
        const { surface, border, textPrimary, textMuted } = readThemeTokens();
        const layout = themedFigure.layout ?? {};

        layout.paper_bgcolor = "rgba(0,0,0,0)";
        layout.plot_bgcolor = layout.plot_bgcolor || surface;
        layout.font = Object.assign({}, layout.font || {}, { color: textPrimary });

        const baseLegend = {
          orientation: "h",
          x: 0.5,
          y: -0.18,
          xanchor: "center",
          yanchor: "top",
          bgcolor: surface,
          bordercolor: border,
          borderwidth: 1,
          font: { size: 12 },
        };
        layout.legend = Object.assign({}, baseLegend, layout.legend || {});
        layout.legend.bgcolor = layout.legend.bgcolor ?? surface;
        layout.legend.bordercolor = layout.legend.bordercolor ?? border;
        layout.legend.borderwidth = layout.legend.borderwidth ?? 1;
        layout.legend.font = Object.assign({}, layout.legend.font || {}, { color: textPrimary });

        const baseHoverlabel = {
          bgcolor: surface,
          bordercolor: border,
          font: {},
        };
        const mergedHoverlabel = Object.assign({}, layout.hoverlabel || {});
        const hoverlabel = Object.assign({}, baseHoverlabel, mergedHoverlabel);
        hoverlabel.bgcolor = surface;
        hoverlabel.bordercolor = border;
        hoverlabel.font = Object.assign({}, hoverlabel.font || {}, { color: textPrimary });
        layout.hoverlabel = hoverlabel;

        const axisKeys = Object.keys(layout).filter((key) => /^(x|y)axis/.test(key));
        axisKeys.forEach((axisKey) => {
          const axis = Object.assign({}, layout[axisKey]);
          axis.tickfont = Object.assign({}, axis.tickfont || {}, { color: textPrimary });
          axis.title = Object.assign({}, axis.title || {});
          if (axis.title.font || axis.title.text) {
            axis.title.font = Object.assign({}, axis.title.font || {}, { color: textPrimary });
          }
          axis.gridcolor = axis.gridcolor || border;
          axis.zerolinecolor = axis.zerolinecolor || border;
          layout[axisKey] = axis;
        });

        if (Array.isArray(layout.annotations)) {
          layout.annotations = layout.annotations.map((annotation) => {
            const mapped = Object.assign({}, annotation);
            const baseColor = String(mapped.font?.color || "").toLowerCase();
            const wantsMuted = baseColor.includes("6b7280") || baseColor.includes("var(--text-muted");
            const targetColor = wantsMuted ? textMuted : textPrimary;
            mapped.font = Object.assign({}, mapped.font || {}, { color: targetColor });
            return mapped;
          });
        }

        themedFigure.layout = layout;
        return themedFigure;
      }

      function renderPlotlyChart(containerId, dataScriptId) {
        const container = document.getElementById(containerId);
        const script = document.getElementById(dataScriptId);
        if (!container || !script) {
          return;
        }

        let figure;
        try {
          figure = JSON.parse(script.textContent);
        } catch (error) {
          console.error("Não foi possível interpretar os dados do gráfico", error);
          return;
        }

        if (typeof Plotly === "undefined") {
          console.warn("Plotly não está disponível para renderizar o gráfico", containerId);
          return;
        }

        const themedFigure = applyThemeToFigure(figure);
        const config = {
          responsive: true,
          displayModeBar: false,
        };

        Plotly.newPlot(container, themedFigure.data ?? [], themedFigure.layout ?? {}, config).then(() => {
          chartsRegistry.set(containerId, { container, baseFigure: cloneFigure(figure), config });
        });
      }

      function refreshChartsTheme() {
        chartsRegistry.forEach(({ container, baseFigure, config }) => {
          const themedFigure = applyThemeToFigure(baseFigure);
          Plotly.react(container, themedFigure.data ?? [], themedFigure.layout ?? {}, config ?? {});
        });
      }

      const themeObserver = new MutationObserver((mutations) => {
        if (mutations.some((mutation) => mutation.attributeName === "class")) {
          refreshChartsTheme();
        }
      });
      themeObserver.observe(document.documentElement, { attributes: true });
      window.addEventListener("storage", (event) => {
        if (event.key === "tema") {
          refreshChartsTheme();
        }
      });

      renderPlotlyChart("membros-chart", "membros-chart-data");
      renderPlotlyChart("eventos-nucleo-chart", "eventos-nucleo-chart-data");
      renderPlotlyChart("membros-periodo-chart", "membros-periodo-chart-data");
      renderPlotlyChart("valores-inscricoes-periodo-chart", "valores-inscricoes-periodo-chart-data");
      renderPlotlyChart("inscricoes-periodo-chart", "inscricoes-periodo-chart-data");
      renderPlotlyChart("nucleados-periodo-chart", "nucleados-periodo-chart-data");
    });
  
