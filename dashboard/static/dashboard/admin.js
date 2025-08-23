document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('toggle-comparativo');
  const canvas = document.getElementById('comparativoChart');
  if (toggle && canvas) {
    const url = canvas.dataset.comparativoUrl;
    const labelAtual = canvas.dataset.labelAtual;
    const labelMedia = canvas.dataset.labelMedia;
    const labelUsuarios = canvas.dataset.labelUsuarios;
    let chart;
    toggle.addEventListener('change', async () => {
      if (toggle.checked) {
        const resp = await fetch(`${url}?metricas=num_users`);
        const data = await resp.json();
        const ctx = canvas.getContext('2d');
        chart = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: [labelAtual, labelMedia],
            datasets: [{
              label: labelUsuarios,
              data: [data.atual.num_users.total, data.media.num_users],
              backgroundColor: ['#4e79a7', '#f28e2b']
            }]
          }
        });
        canvas.hidden = false;
      } else {
        if (chart) chart.destroy();
        canvas.hidden = true;
      }
    });
  }

  const feedSection = document.getElementById('feed-metrics');
  if (feedSection) {
    const feedUrl = feedSection.dataset.feedMetricsUrl;
    fetch(feedUrl)
      .then(r => r.json())
      .then(data => {
        const tipoCtx = document.getElementById('feed-type-chart');
        new Chart(tipoCtx, {
          type: 'bar',
          data: { labels: Object.keys(data.counts.posts_by_type), datasets: [{ data: Object.values(data.counts.posts_by_type) }] }
        });
        const tagCtx = document.getElementById('feed-tag-chart');
        new Chart(tagCtx, {
          type: 'bar',
          data: { labels: data.top_tags.map(t => t.tag), datasets: [{ data: data.top_tags.map(t => t.total) }] }
        });
        const authorCtx = document.getElementById('feed-author-chart');
        new Chart(authorCtx, {
          type: 'bar',
          data: { labels: data.top_authors.map(a => a.autor), datasets: [{ data: data.top_authors.map(a => a.total) }] }
        });
      });
  }
});
