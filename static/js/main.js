// Trending Update — Main JS

// Track post views
document.addEventListener('DOMContentLoaded', function () {

  // Auto-hide alerts after 4 seconds
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(a => {
    setTimeout(() => {
      a.style.opacity = '0';
      a.style.transition = 'opacity 0.5s';
      setTimeout(() => a.remove(), 500);
    }, 4000);
  });

  // Mobile nav toggle
  const catNav = document.querySelector('.cat-nav');
  if (catNav) {
    catNav.addEventListener('wheel', function (e) {
      e.preventDefault();
      catNav.scrollLeft += e.deltaY;
    });
  }

});
