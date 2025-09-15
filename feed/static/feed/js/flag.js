const csrfToken = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || '';

export async function handleFlag(event) {
  const btn = event.target.closest('.flag-btn');
  if (!btn) return;

  event.preventDefault();
  event.stopPropagation();

  if (btn.hasAttribute('disabled') || btn.classList.contains('disabled')) {
    return;
  }

  const postId = btn.dataset.postId;
  if (!postId) return;

  try {
    const res = await fetch(`/api/feed/posts/${postId}/flag/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken
      }
    });

    if (!res.ok) {
      throw new Error('flag failed');
    }

    btn.classList.add('text-[var(--error)]', 'cursor-not-allowed', 'disabled');
    btn.setAttribute('disabled', 'disabled');
    btn.setAttribute('aria-pressed', 'true');
  } catch (error) {
    const message = btn.dataset.flagErrorMessage || 'Erro ao denunciar';
    if (message) {
      alert(message);
    }
    console.error('Erro ao denunciar', error);
  }
}

document.addEventListener('click', handleFlag);
