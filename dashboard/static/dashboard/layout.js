import Sortable from 'sortablejs';

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('dashboard-cards');
  if (!container) return;
  const url = container.dataset.saveUrl;
  const input = document.getElementById('layout_json');
  const saveOrder = (order) => {
    if (input) input.value = JSON.stringify(order);
    if (url && url !== '#') {
      htmx.ajax('POST', url, {values: {layout_json: JSON.stringify(order)}});
    }
  };
  const initial = Array.from(container.children).map(el => el.id);
  saveOrder(initial);
  Sortable.create(container, {
    animation: 150,
    handle: '.card-handle',
    onEnd() {
      const order = Array.from(container.children).map(el => el.id);
      saveOrder(order);
    }
  });
  container.addEventListener('keydown', (e) => {
    const item = document.activeElement.closest('.card');
    if (!item) return;
    if (['ArrowLeft','ArrowUp'].includes(e.key)) {
      e.preventDefault();
      const prev = item.previousElementSibling;
      if (prev) {
        container.insertBefore(item, prev);
        const order = Array.from(container.children).map(el => el.id);
        saveOrder(order);
      }
    }
    if (['ArrowRight','ArrowDown'].includes(e.key)) {
      e.preventDefault();
      const next = item.nextElementSibling;
      if (next) {
        next.parentNode.insertBefore(next, item);
        const order = Array.from(container.children).map(el => el.id);
        saveOrder(order);
      }
    }
  });
});
