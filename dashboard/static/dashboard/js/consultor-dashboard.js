    document.addEventListener("DOMContentLoaded", () => {
      const chartsRegistry = new Map();

      function cloneFigure(figure) {
        if (typeof structuredClone === "function") {
          return structuredClone(figure);
        }
        try {
          return JSON.parse(JSON.stringify(figure));
        } catch (error) {
          console.error("Não foi possível clonar a figura do gráfico.", error);
          return null;
        }
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
        const cloned = cloneFigure(figure);
        if (!cloned) {
          return null;
        }

        const { surface, border, textPrimary, textMuted } = readThemeTokens();
        const layout = cloned.layout ?? {};

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

        cloned.layout = layout;
        return cloned;
      }

      function parseFigure(scriptId) {
        const script = document.getElementById(scriptId);
        if (!script) {
          return null;
        }

        try {
          return JSON.parse(script.textContent || "{}");
        } catch (error) {
          console.error(`Não foi possível interpretar os dados do gráfico "${scriptId}".`, error);
          return null;
        }
      }

      function renderPlotlyChart(containerId, dataScriptId) {
        const container = document.getElementById(containerId);
        const figure = parseFigure(dataScriptId);

        if (!container || !figure) {
          return;
        }

        if (typeof Plotly === "undefined") {
          console.warn("Plotly não está disponível para renderizar o gráfico", containerId);
          return;
        }

        const themedFigure = applyThemeToFigure(figure);
        if (!themedFigure) {
          return;
        }

        const config = {
          responsive: true,
          displayModeBar: false,
        };

        Plotly.newPlot(container, themedFigure.data ?? [], themedFigure.layout ?? {}, config).then(() => {
          const baseFigure = cloneFigure(figure);
          if (baseFigure) {
            chartsRegistry.set(containerId, { container, baseFigure, config });
          }
        });
      }

      function refreshChartsTheme() {
        chartsRegistry.forEach(({ container, baseFigure, config }) => {
          const themedFigure = applyThemeToFigure(baseFigure);
          if (!themedFigure) {
            return;
          }
          Plotly.react(container, themedFigure.data ?? [], themedFigure.layout ?? {}, config ?? {});
        });
      }

      const chartsToRender = [
        ["consultor-eventos-inscricoes-chart", "consultor-eventos-inscricoes-chart-data"],
        ["consultor-nucleados-chart", "consultor-nucleados-chart-data"],
        ["consultor-receita-chart", "consultor-receita-chart-data"],
      ];

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

      chartsToRender.forEach(([containerId, dataScriptId]) => {
        renderPlotlyChart(containerId, dataScriptId);
      });
    });
  
