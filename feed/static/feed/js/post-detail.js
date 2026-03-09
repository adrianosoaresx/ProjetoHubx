document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-post-detail-root]");
  if (!root) {
    return;
  }

  const csrfToken = root.dataset.csrfToken || "";
  const openViewUrl = root.dataset.openViewUrl;
  const closeViewUrl = root.dataset.closeViewUrl;

  if (openViewUrl) {
    fetch(openViewUrl, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
    });
  }

  if (closeViewUrl) {
    window.addEventListener("beforeunload", function () {
      fetch(closeViewUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
        keepalive: true,
      });
    });
  }

  document.querySelectorAll(".bookmark-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const postId = btn.dataset.postId;
      const res = await fetch(`/api/feed/posts/${postId}/bookmark/`, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
      });
      if (!res.ok) return;
      const data = await res.json();
      btn.classList.toggle("text-yellow-600", data.bookmarked);
    });
  });

  document.querySelectorAll(".flag-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const postId = btn.dataset.postId;
      const res = await fetch(`/api/feed/posts/${postId}/flag/`, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
      });
      if (res.ok) {
        btn.classList.add("text-red-600", "cursor-not-allowed");
        btn.setAttribute("disabled", "disabled");
      }
    });
  });

  window.setReplyTo = function setReplyTo(commentId) {
    const replyInput = document.getElementById("id_reply_to");
    const form = document.getElementById("comment-form");
    if (!replyInput || !form) {
      return;
    }

    if (commentId) {
      replyInput.value = commentId;
      form.setAttribute("hx-target", `#replies-${commentId}`);
    } else {
      replyInput.value = "";
      form.setAttribute("hx-target", "#comments");
    }

    document.getElementById("id_texto")?.focus();
  };
});
