export async function handleShare(event) {
  const btn = event.target.closest('.share-btn');
  if (!btn) return;

  event.preventDefault();
  const postId = btn.dataset.postId;
  if (!postId) return;

  const countSpan = btn.querySelector('.share-count');
  const csrfToken = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || '';

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
      if (countSpan) {
        countSpan.textContent = String(parseInt(countSpan.textContent || '0') + 1);
      }
    } else if (res.status === 204) {
      btn.classList.remove('text-[var(--primary)]');
      if (countSpan) {
        const newValue = Math.max(parseInt(countSpan.textContent || '0') - 1, 0);
        countSpan.textContent = String(newValue);
      }
    }
  } catch (err) {
    console.error('Erro ao compartilhar', err);
  }
}

document.addEventListener('click', handleShare);
