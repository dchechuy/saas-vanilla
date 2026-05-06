document.addEventListener("DOMContentLoaded", () => {
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
      const defaultModelsLink = document.querySelector('[data-ds-nav-hash$="#llm-models"]');
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
});
