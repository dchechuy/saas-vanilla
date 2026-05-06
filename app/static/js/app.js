document.addEventListener("DOMContentLoaded", () => {
  const userMenuWrap = document.getElementById("user-menu-wrap");
  const userMenuDropdown = document.getElementById("user-menu-dropdown");

  window.toggleUserMenu = (event) => {
    event.stopPropagation();
    if (!userMenuDropdown) {
      return;
    }
    userMenuDropdown.classList.toggle("open");
  };

  const closeUserMenu = () => {
    if (userMenuDropdown) {
      userMenuDropdown.classList.remove("open");
    }
  };

  document.addEventListener("click", (event) => {
    if (userMenuWrap && !userMenuWrap.contains(event.target)) {
      closeUserMenu();
    }
  });

  const themeToggle = document.getElementById("theme-toggle");
  const themeIcon = themeToggle ? themeToggle.querySelector("i") : null;
  const applyTheme = (theme) => {
    document.documentElement.setAttribute("data-bs-theme", theme);
    localStorage.setItem("saas-vanilla-theme", theme);
    if (themeIcon) {
      themeIcon.className = theme === "dark" ? "fa-solid fa-sun" : "fa-solid fa-moon";
    }
    if (themeToggle) {
      themeToggle.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
      themeToggle.setAttribute("title", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
    }
    const themeLabel = document.querySelector(".ds-theme-toggle-label");
    if (themeLabel) {
      themeLabel.textContent = theme === "dark" ? "Light mode" : "Dark mode";
    }
  };

  const currentTheme = document.documentElement.getAttribute("data-bs-theme") || "light";
  applyTheme(currentTheme);

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const nextTheme = document.documentElement.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
    });
  }

  const navLinks = document.querySelectorAll("[data-ds-hash-tabs] .nav-link");
  const navHashLinks = document.querySelectorAll("[data-ds-nav-hash]");

  const syncSidebarHashNav = () => {
    if (!navHashLinks.length) {
      return;
    }
    const current = `${window.location.pathname}${window.location.hash}`;
    navHashLinks.forEach((link) => {
      const matches = link.dataset.dsNavHash === current;
      link.classList.toggle("active", matches);
    });
  };

  if (navLinks.length && window.bootstrap) {
    const activateHashTab = () => {
      const hash = window.location.hash;
      if (!hash) {
        syncSidebarHashNav();
        return;
      }
      const target = document.querySelector(`[data-ds-hash-tabs] .nav-link[href="${hash}"]`);
      if (target) {
        bootstrap.Tab.getOrCreateInstance(target).show();
      }
      syncSidebarHashNav();
    };

    navLinks.forEach((link) => {
      link.addEventListener("shown.bs.tab", (event) => {
        const href = event.target.getAttribute("href");
        if (href && href.startsWith("#")) {
          history.replaceState(null, "", href);
          syncSidebarHashNav();
        }
      });
    });

    activateHashTab();
    window.addEventListener("hashchange", activateHashTab);
  } else {
    syncSidebarHashNav();
    window.addEventListener("hashchange", syncSidebarHashNav);
  }

  if (!window.location.hash) {
    const pathname = window.location.pathname;
    if (pathname === "/models/") {
      const defaultModelsLink = document.querySelector('[data-ds-nav-hash$="#integrations"]')
        || document.querySelector('[data-ds-nav-hash$="#attributes"]');
      if (defaultModelsLink) {
        navHashLinks.forEach((link) => link.classList.remove("active"));
        defaultModelsLink.classList.add("active");
      }
    }
    if (pathname === "/users/") {
      navHashLinks.forEach((link) => link.classList.remove("active"));
      const usersLink = document.querySelector('a[href="/users/"]:not([data-ds-nav-hash])');
      if (usersLink) {
        usersLink.classList.add("active");
      }
    }
  };

  // UTC → local time conversion for elements with class "local-time" and data-utc attribute.
  // Matches the skunkBOX convention. Server always stores UTC; browser renders in user's timezone.
  document.querySelectorAll(".local-time[data-utc]").forEach((el) => {
    const utc = el.dataset.utc;
    if (!utc) return;
    const dt = new Date(utc.endsWith("Z") ? utc : utc + "Z");
    if (isNaN(dt.getTime())) return;
    el.textContent = dt.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    el.title = dt.toLocaleString();
  });
});
