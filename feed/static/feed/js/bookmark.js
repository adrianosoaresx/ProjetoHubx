const getCsrfToken = () => document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || '';

async function handleBookmark(event) {
  const btn = event.target.closest('.bookmark-btn');
  if (!btn) {
    return;
  }

  event.preventDefault();
  event.stopPropagation();

  const postId = btn.dataset.postId;
  if (!postId) {
    return;
  }

  try {
    const res = await fetch(`/api/feed/posts/${postId}/bookmark/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken()
      }
    });

    if (!res.ok) {
      throw new Error('bookmark failed');
    }

    const data = await res.json();
    const isBookmarked = Boolean(data.bookmarked);

    btn.classList.toggle('text-[var(--warning)]', isBookmarked);
    btn.setAttribute('aria-pressed', isBookmarked ? 'true' : 'false');
  } catch (error) {
    const message = btn.dataset.bookmarkError || 'Erro ao salvar';
    window.alert(message);
    console.error('Erro ao salvar favorito', error);
  }
}

document.addEventListener('click', handleBookmark);

export { handleBookmark };
