import Sortable from 'sortablejs';

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('dashboard-cards');
  if (!container) return;
  const url = container.dataset.saveUrl;
  Sortable.create(container, {
    animation: 150,
    handle: '.card-handle',
    onEnd() {
      const order = Array.from(container.children).map(el => el.id);
      htmx.ajax('POST', url, {values: {layout_json: JSON.stringify(order)}});
    }
  });
  container.addEventListener('keydown', (e) => {
    const item = document.activeElement.closest('.card');
    if (!item) return;
    if (['ArrowLeft','ArrowUp'].includes(e.key)) {
      e.preventDefault();
      const prev = item.previousElementSibling;
      if (prev) container.insertBefore(item, prev);
    }
    if (['ArrowRight','ArrowDown'].includes(e.key)) {
      e.preventDefault();
      const next = item.nextElementSibling;
      if (next) {
        next.parentNode.insertBefore(next, item);
        const order = Array.from(container.children).map(el => el.id);
        htmx.ajax('POST', url, {values: {layout_json: JSON.stringify(order)}});
      }
    }
  });
});
