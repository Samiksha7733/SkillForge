document.addEventListener('DOMContentLoaded', () => {
    // Like button AJAX handler
    const likeButtons = document.querySelectorAll('.btn-like-ajax');
    likeButtons.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const projectId = btn.getAttribute('data-project-id');
            if (!projectId) return;

            try {
                const response = await fetch(`/projects/like/${projectId}`, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    const countSpan = btn.querySelector('.like-count');
                    if (countSpan) {
                        countSpan.textContent = data.likes;
                    }
                    // Visual pulse animation
                    btn.classList.add('animate-pulse');
                    setTimeout(() => btn.classList.remove('animate-pulse'), 300);
                }
            } catch (err) {
                console.error('Error toggling like:', err);
            }
        });
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });
});
