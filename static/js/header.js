/* Header interactions:
 *  - sticky scroll class (.is-scrolled)
 *  - mobile nav drawer with iOS body-scroll-lock
 *  - desktop dropdown keyboard navigation
 *  - mobile submenu accordions
 *  - search button event
 */
(() => {
  "use strict";

  // ── Sticky header ──────────────────────────────────────────────────────────
  const header = document.querySelector("[data-sticky-header]");
  if (header) {
    const THRESHOLD = 8;
    const onScroll = () =>
      header.classList.toggle("is-scrolled", window.scrollY > THRESHOLD);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // ── Панель пріоритетів — зникає перед футером ─────────────────────────────
  //
  // Коли футер наближається до нижнього краю вʼюпорту, панель плавно
  // зникає через opacity. Позиція (bottom) не змінюється — жодного
  // "стрибка" чи відставання під час скролу.
  //
  const panel = document.querySelector(".priorities-panel");
  const siteFooter = document.querySelector(".site-footer");

  if (panel && siteFooter) {
    const GAP = 12;
    const DEFAULT_BOTTOM = 12;
    let rafId = 0;
    let logCount = 0;

    function adjustPanel() {
      const footerTop = siteFooter.getBoundingClientRect().top;
      const overlap = window.innerHeight - footerTop; // >0 = футер у viewport
      const bottom = overlap > 0 ? overlap + GAP : DEFAULT_BOTTOM;

      panel.style.bottom = bottom + "px";
      panel.style.opacity = "";
      panel.style.pointerEvents = "";

      // #region agent log
      if (logCount < 20 && overlap > -200) {
        logCount++;
        fetch('http://127.0.0.1:7778/ingest/03b07a46-570b-42cd-8355-5306c5988ab0',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'ef1f56'},body:JSON.stringify({sessionId:'ef1f56',runId:'run2',hypothesisId:'H2',location:'header.js:adjustPanel',message:'panel collapse',data:{footerTop:Math.round(footerTop),vh:window.innerHeight,overlap:Math.round(overlap),bottom,panelRect:{top:Math.round(panel.getBoundingClientRect().top),bottom:Math.round(panel.getBoundingClientRect().bottom),height:Math.round(panel.getBoundingClientRect().height)}},timestamp:Date.now()})}).catch(()=>{});
      }
      // #endregion
    }

    const onScroll = () => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(adjustPanel);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    adjustPanel();
  }

  // ── Mobile nav ─────────────────────────────────────────────────────────────
  const toggleBtn = document.querySelector("[data-action='toggle-nav']");
  const mobileNav = document.getElementById("mobile-nav");

  let savedScrollY = 0;

  function openNav() {
    savedScrollY = window.scrollY;
    toggleBtn.setAttribute("aria-expanded", "true");
    mobileNav.removeAttribute("hidden");
    // iOS Safari: position:fixed + top stop scroll-through
    document.body.style.top = `-${savedScrollY}px`;
    document.body.classList.add("nav-open");
    // Перший елемент меню отримує фокус для доступності
    const firstLink = mobileNav.querySelector("a, button");
    if (firstLink) firstLink.focus();
  }

  function closeNav() {
    toggleBtn.setAttribute("aria-expanded", "false");
    mobileNav.setAttribute("hidden", "");
    document.body.classList.remove("nav-open");
    document.body.style.top = "";
    // Відновлюємо позицію скролу після position:fixed
    window.scrollTo({ top: savedScrollY, behavior: "auto" });
    toggleBtn.focus();
  }

  if (toggleBtn && mobileNav) {
    toggleBtn.addEventListener("click", () => {
      const isOpen = toggleBtn.getAttribute("aria-expanded") === "true";
      isOpen ? closeNav() : openNav();
    });

    // Закрити при кліку на посилання
    mobileNav.addEventListener("click", (e) => {
      if (e.target.closest("a")) closeNav();
    });

    // Закрити при Escape
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && toggleBtn.getAttribute("aria-expanded") === "true") {
        closeNav();
      }
    });
  }

  // ── Desktop dropdown: click to toggle, close on outside click ─────────────
  const dropdownItems = [...document.querySelectorAll(".has-dropdown")];

  function setDropdownOpen(item, open) {
    const trigger = item.querySelector(".primary-nav__link");
    item.classList.toggle("is-open", open);
    if (trigger) {
      trigger.setAttribute("aria-expanded", open ? "true" : "false");
    }
  }

  function closeAllDropdowns(except = null) {
    dropdownItems.forEach((item) => {
      if (item !== except) setDropdownOpen(item, false);
    });
  }

  dropdownItems.forEach((item) => {
    const trigger = item.querySelector(".primary-nav__link");
    const dropdown = item.querySelector(".dropdown");
    if (!trigger || !dropdown) return;

    trigger.addEventListener("click", (e) => {
      e.preventDefault();
      const willOpen = !item.classList.contains("is-open");
      closeAllDropdowns(willOpen ? item : null);
      setDropdownOpen(item, willOpen);
    });

    item.addEventListener("focusout", (e) => {
      if (!item.contains(e.relatedTarget)) {
        setDropdownOpen(item, false);
      }
    });

    trigger.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault();
        closeAllDropdowns(item);
        setDropdownOpen(item, true);
        const first = dropdown.querySelector(".dropdown__link");
        if (first) first.focus();
      }
    });

    dropdown.addEventListener("keydown", (e) => {
      const links = [...dropdown.querySelectorAll(".dropdown__link")];
      const idx = links.indexOf(document.activeElement);
      if (e.key === "ArrowDown") {
        e.preventDefault();
        links[(idx + 1) % links.length]?.focus();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        links[(idx - 1 + links.length) % links.length]?.focus();
      } else if (e.key === "Escape") {
        e.preventDefault();
        setDropdownOpen(item, false);
        trigger.focus();
      }
    });
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".has-dropdown")) {
      closeAllDropdowns();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAllDropdowns();
  });

  // ── Mobile submenu accordions ──────────────────────────────────────────────
  document.querySelectorAll(".mobile-nav__toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = btn.closest(".mobile-nav__item");
      const sub = item?.querySelector(".mobile-nav__sub");
      if (!sub) return;
      const expanded = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!expanded));
      if (expanded) {
        sub.setAttribute("hidden", "");
      } else {
        sub.removeAttribute("hidden");
      }
    });
  });

  // ── Share: copy URL button ─────────────────────────────────────────────────
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-copy-url]");
    if (!btn) return;
    const url = btn.dataset.copyUrl;
    const original = btn.textContent.trim();

    const fallback = () => {
      const ta = document.createElement("textarea");
      ta.value = url;
      ta.style.cssText = "position:fixed;top:-9999px;left:-9999px;opacity:0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try { document.execCommand("copy"); } catch (_) { return; }
      document.body.removeChild(ta);
    };

    const onSuccess = () => {
      btn.textContent = "✓ Скопійовано";
      setTimeout(() => { btn.textContent = original; }, 2500);
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(onSuccess).catch(fallback);
    } else {
      fallback();
      onSuccess();
    }
  });

  // ── Search button ──────────────────────────────────────────────────────────
  const searchBtn = document.querySelector("[data-action='open-search']");
  if (searchBtn) {
    searchBtn.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("fpu:open-search"));
      // Якщо є форма пошуку на сторінці — перейти до неї
      const searchInput = document.querySelector(".search-form__input");
      if (searchInput) {
        searchInput.focus();
        searchInput.scrollIntoView({ behavior: "smooth", block: "center" });
      } else {
        window.location.href = "/search/";
      }
    });
  }
})();
