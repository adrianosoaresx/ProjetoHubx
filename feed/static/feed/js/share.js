export async function handleShare(event) {
  const btn = event.target.closest('.share-btn');
  if (!btn) return;

  event.preventDefault();
  event.stopPropagation();
  const postId = btn.dataset.postId;
  if (!postId) return;

  const countSpan = btn.querySelector('.share-count');
  const csrfToken = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || '';

  const readCount = () => {
    const fromDataset = Number.parseInt(btn.dataset.shareCount || '', 10);
    if (!Number.isNaN(fromDataset)) {
      return fromDataset;
    }
    if (!countSpan) {
      return 0;
    }
    const parsed = Number.parseInt((countSpan.textContent || '').trim(), 10);
    return Number.isNaN(parsed) ? 0 : parsed;
  };

  const updateCount = (value) => {
    const safeValue = Math.max(0, Number.isNaN(value) ? 0 : value);
    btn.dataset.shareCount = String(safeValue);
    if (countSpan) {
      countSpan.textContent = String(safeValue);
    }
    const label = btn.querySelector('[data-share-label]');
    if (label) {
      const formatter =
        typeof window !== 'undefined' && typeof window.ngettext === 'function'
          ? window.ngettext
          : null;
      const template = formatter
        ? formatter('%(count)s compartilhamento', '%(count)s compartilhamentos', safeValue)
        : safeValue === 1
          ? '%(count)s compartilhamento'
          : '%(count)s compartilhamentos';
      const interpolator =
        typeof window !== 'undefined' && typeof window.interpolate === 'function'
          ? window.interpolate
          : null;
      label.textContent = interpolator
        ? interpolator(template, { count: safeValue }, true)
        : template.replace('%(count)s', safeValue);
    }
  };

  try {
    const res = await fetch(`/api/feed/posts/${postId}/reacoes/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ vote: 'share' })
    });

    if (res.status === 201) {
      btn.classList.add('text-[var(--primary)]');
      btn.setAttribute('aria-pressed', 'true');
      updateCount(readCount() + 1);
    } else if (res.status === 204) {
      btn.classList.remove('text-[var(--primary)]');
      btn.setAttribute('aria-pressed', 'false');
      updateCount(readCount() - 1);
    }
  } catch (err) {
    console.error('Erro ao compartilhar', err);
  }
}

document.addEventListener('click', handleShare);
