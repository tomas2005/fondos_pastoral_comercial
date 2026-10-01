// Auto-dismiss flash messages after 5 seconds
document.addEventListener("DOMContentLoaded", function () {
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity 0.5s";
      alert.style.opacity = "0";
      setTimeout(function () { alert.remove(); }, 500);
    }, 5000);
  });

  // Animate progress bars
  const bars = document.querySelectorAll(".progress-bar, .mini-fill, .rank-fill");
  bars.forEach(function (bar) {
    const target = bar.style.width;
    bar.style.width = "0%";
    setTimeout(function () { bar.style.width = target; }, 100);
  });

  // Animate ranking items on load
  const items = document.querySelectorAll(".ranking-item, .ranking-row");
  items.forEach(function (item, i) {
    item.style.opacity = "0";
    item.style.transform = "translateX(-20px)";
    item.style.transition = "opacity 0.3s, transform 0.3s";
    setTimeout(function () {
      item.style.opacity = "1";
      item.style.transform = "translateX(0)";
    }, 80 * i);
  });

  // Confirm on destructive actions (extra safety)
  document.querySelectorAll("a[href*='eliminar']").forEach(function (link) {
    if (!link.getAttribute("onclick")) {
      link.addEventListener("click", function (e) {
        if (!confirm("¿Estás seguro de que querés eliminar este elemento?")) {
          e.preventDefault();
        }
      });
    }
  });

  // Set today's date on date inputs that are empty
  const dateInputs = document.querySelectorAll("input[type='date']");
  dateInputs.forEach(function (input) {
    if (!input.value && input.name === "fecha") {
      const today = new Date();
      const yyyy = today.getFullYear();
      const mm = String(today.getMonth() + 1).padStart(2, "0");
      const dd = String(today.getDate()).padStart(2, "0");
      input.value = `${yyyy}-${mm}-${dd}`;
    }
  });
});
