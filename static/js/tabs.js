document.addEventListener('DOMContentLoaded', () => {
  const tabLists = document.querySelectorAll('[role="tablist"]');
  tabLists.forEach(tabList => {
    const tabs = tabList.querySelectorAll('[role="tab"]');
    tabs.forEach(tab => {
      tab.addEventListener('click', event => {
        if (tab.tagName === 'A') {
          event.preventDefault();
        }
        const active = (tab.dataset.activeClass || '').split(' ').filter(Boolean);
        const inactive = (tab.dataset.inactiveClass || '').split(' ').filter(Boolean);
        tabs.forEach(t => {
          t.setAttribute('aria-selected', 'false');
          const tActive = (t.dataset.activeClass || '').split(' ').filter(Boolean);
          const tInactive = (t.dataset.inactiveClass || '').split(' ').filter(Boolean);
          if (tActive.length) t.classList.remove(...tActive);
          if (tInactive.length) t.classList.add(...tInactive);
        });
        tab.setAttribute('aria-selected', 'true');
        if (active.length) tab.classList.add(...active);
        if (inactive.length) tab.classList.remove(...inactive);

        const targetId = tab.dataset.tabTarget || (tab.getAttribute('href') || '').replace(/^#/, '') || tab.getAttribute('aria-controls');
        if (!targetId) {
          return;
        }
        const target = document.getElementById(targetId);
        if (!target) {
          return;
        }
        tabs.forEach(t => {
          const id = t.dataset.tabTarget || (t.getAttribute('href') || '').replace(/^#/, '') || t.getAttribute('aria-controls');
          if (!id) return;
          const section = document.getElementById(id);
          if (section) {
            section.hidden = id !== targetId;
          }
        });
        if (typeof htmx !== 'undefined' && tab.hasAttribute('hx-get') && !target.dataset.loaded) {
          htmx.ajax('GET', tab.getAttribute('hx-get'), { target: target });
          target.dataset.loaded = 'true';
        }
      });
    });
  });
});
