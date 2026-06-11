/* Hero sidebar slider + optional video widget rotation */
(() => {
  "use strict";

  const AUTOPLAY_MS = 4000;
  const TRANSITION_MS = 400;

  function initHeroSlider(root) {
    const track = root.querySelector("[data-hero-slider-track]");
    const slides = Array.from(root.querySelectorAll("[data-hero-slider-slide]"));
    const dots = Array.from(root.querySelectorAll("[data-hero-slider-dot]"));
    if (!track || slides.length < 2) return;

    const count = slides.length;
    let current = 0;
    let timer = null;

    track.style.setProperty("--hero-slider-count", String(count));
    track.style.setProperty("--hero-slider-transition-ms", `${TRANSITION_MS}ms`);
    root.style.setProperty("--hero-slider-count", String(count));

    const live = root.querySelector("[data-hero-slider-live]");

    function goTo(idx) {
      current = (idx + count) % count;
      track.style.transform = `translateX(calc(-${current} * (100% / ${count})))`;
      dots.forEach((dot, i) => {
        const active = i === current;
        dot.classList.toggle("hero-mosaic__dot--active", active);
        dot.setAttribute("aria-selected", active ? "true" : "false");
      });
      slides.forEach((slide, i) => {
        slide.setAttribute("aria-hidden", i !== current ? "true" : "false");
      });
      if (live) live.textContent = `Новина ${current + 1} з ${count}`;
    }

    function startAuto() {
      clearInterval(timer);
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      timer = setInterval(() => goTo(current + 1), AUTOPLAY_MS);
    }

    dots.forEach((dot, i) => {
      dot.addEventListener("click", () => {
        goTo(i);
        startAuto();
      });
    });

    root.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") { goTo(current - 1); startAuto(); }
      if (e.key === "ArrowRight") { goTo(current + 1); startAuto(); }
    });

    root.addEventListener("mouseenter", () => clearInterval(timer));
    root.addEventListener("mouseleave", startAuto);

    goTo(0);
    startAuto();
  }

  function buildEmbedSrc(videoId) {
    return `https://www.youtube.com/embed/${encodeURIComponent(videoId)}?rel=0`;
  }

  function updateVideoMeta(root, item) {
    const caption = root.querySelector("[data-hero-video-caption]");
    const youtubeLink = root.querySelector("[data-hero-video-youtube]");
    const title = item.dataset.title || "";
    const articleUrl = item.dataset.url || "";
    const watchUrl = item.dataset.youtubeWatch || "";

    if (caption) {
      caption.replaceChildren();
      if (articleUrl) {
        const link = document.createElement("a");
        link.className = "hero-mosaic__video-link";
        link.href = articleUrl;
        link.textContent = title;
        caption.appendChild(link);
      } else {
        caption.textContent = title;
      }
    }

    if (youtubeLink && watchUrl) {
      youtubeLink.href = watchUrl;
    }
  }

  function initVideoWidget(root) {
    const prev = root.querySelector("[data-hero-video-prev]");
    const next = root.querySelector("[data-hero-video-next]");
    const embed = root.querySelector("[data-hero-video-embed]");
    if (!embed) return;

    const items = Array.from(root.querySelectorAll("[data-hero-video-item]"));
    if (items.length < 2) return;

    let idx = 0;

    function render(i) {
      idx = (i + items.length) % items.length;
      const item = items[idx];
      const videoId = item.dataset.youtubeId;
      if (!videoId) return;

      embed.src = buildEmbedSrc(videoId);
      embed.title = item.dataset.title || "";
      updateVideoMeta(root, item);
    }

    prev?.addEventListener("click", (e) => { e.preventDefault(); render(idx - 1); });
    next?.addEventListener("click", (e) => { e.preventDefault(); render(idx + 1); });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-hero-slider]").forEach(initHeroSlider);
    document.querySelectorAll("[data-hero-video]").forEach(initVideoWidget);
  });
})();
