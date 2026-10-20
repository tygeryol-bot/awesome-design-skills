/* ==========================================================================
   DAISY TAPES '27 — interactions (vanilla, no dependencies)
   Every feature hooks onto data-attributes so it survives Webflow class
   renames. Paste into Site Settings › Custom Code › Footer, or keep as a file.
   ========================================================================== */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  const STICKERS = "assets/stickers/";

  // deterministic "random" so collage offsets don't jump between reloads
  const seeded = (seed) => () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };

  /* ---------------------------------------------------------------- toast */
  const toastEl = $("[data-toast]");
  let toastTimer;
  function toast(message) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toastEl.hidden = true), 3600);
  }

  /* ----------------------------------------------------- ransom headlines */
  $$("[data-ransom]").forEach((el, n) => {
    const text = el.textContent.trim();
    const rand = seeded(97 + n * 31 + text.length);
    const words = text.split(/\s+/).map((word) => {
      const tiles = Array.from(word).map((ch, i) => {
        const v = 1 + Math.floor(rand() * 8);
        const r = (rand() * 10 - 5).toFixed(1);
        const y = (rand() * 6 - 3).toFixed(1);
        const k = (0.88 + rand() * 0.24).toFixed(2);
        const taped = rand() < 0.16 ? " is-taped" : "";
        return `<span class="ransom_tile is-v${v}${taped}" style="--r:${r}deg;--y:${y}px;--k:${k}em">${ch}</span>`;
      });
      return `<span class="ransom_word">${tiles.join("")}</span>`;
    });
    el.innerHTML = `<span class="visually-hidden">${text}</span><span aria-hidden="true" style="display:contents">${words.join("")}</span>`;
  });

  /* ------------------------------------------------------------ countdown */
  const gates = new Date("2027-10-01T12:00:00+02:00");
  function tick() {
    const ms = gates - Date.now();
    const days = Math.max(0, Math.floor(ms / 86400000));
    const label = ms <= 0 ? "Gates are open" : days === 1 ? "1 day" : `${days} days`;
    $$("[data-countdown]").forEach((el) => (el.textContent = label));
  }
  tick();
  setInterval(tick, 60000);

  /* ------------------------------------------------------------------ nav */
  const nav = $("[data-nav]");
  const sheet = $("[data-nav-sheet]");
  const toggle = $("[data-nav-toggle]");
  let lastY = window.scrollY;

  window.addEventListener(
    "scroll",
    () => {
      const y = window.scrollY;
      if (nav && sheet && sheet.hidden) nav.classList.toggle("is-hidden", y > lastY && y > 320);
      lastY = y;
    },
    { passive: true }
  );

  function openSheet() {
    sheet.hidden = false;
    sheet.classList.add("is-open");
    toggle.setAttribute("aria-expanded", "true");
    document.documentElement.style.overflow = "hidden";
    $(".nav_sheet-link", sheet)?.focus();
  }

  function closeSheet(returnFocus = true) {
    sheet.hidden = true;
    sheet.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
    document.documentElement.style.overflow = "";
    if (returnFocus) toggle.focus();
  }

  if (sheet && toggle) {
    toggle.addEventListener("click", openSheet);
    $("[data-nav-close]", sheet)?.addEventListener("click", () => closeSheet());
    $$("a", sheet).forEach((a) => a.addEventListener("click", () => closeSheet(false)));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !sheet.hidden) closeSheet();
      if (e.key === "Tab" && !sheet.hidden) {
        const focusables = $$("a, button", sheet);
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    });
  }

  // highlight the label strip for the section in view
  const navLinks = $$(".nav_link");
  if ("IntersectionObserver" in window && navLinks.length) {
    const spy = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          navLinks.forEach((a) => a.setAttribute("aria-current", String(a.hash === `#${entry.target.id}`)));
        });
      },
      { rootMargin: "-45% 0px -50% 0px" }
    );
    navLinks.forEach((a) => {
      const target = document.getElementById(a.hash.slice(1));
      if (target) spy.observe(target);
    });
  }

  /* ------------------------------------------------- tilt toward cursor */
  function bindTilt(el) {
    let frame;
    el.addEventListener("pointermove", (e) => {
      if (!finePointer.matches || reduceMotion.matches) return;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const box = el.getBoundingClientRect();
        const x = (e.clientX - box.left) / box.width - 0.5;
        const y = (e.clientY - box.top) / box.height - 0.5;
        el.classList.add("is-tilting");
        el.style.setProperty("--tilt-x", `${(-y * 9).toFixed(2)}deg`);
        el.style.setProperty("--tilt-y", `${(x * 11).toFixed(2)}deg`);
      });
    });
    el.addEventListener("pointerleave", () => {
      cancelAnimationFrame(frame);
      el.classList.remove("is-tilting");
      el.style.removeProperty("--tilt-x");
      el.style.removeProperty("--tilt-y");
    });
  }
  $$("[data-tilt]").forEach(bindTilt);

  /* ------------------------------------------- hero: stick a sticker down */
  const hero = $("[data-hero]");
  const drops = $("[data-drops]");
  const dropSet = ["smiley", "star-clay", "sunflower", "button-heart", "star-denim-b", "fish", "button-round", "star-painted"];
  let dropCount = 0;
  if (hero && drops) {
    hero.addEventListener("click", (e) => {
      if (e.target.closest("a, button, .note-paper, .polaroid")) return;
      const box = hero.getBoundingClientRect();
      const img = document.createElement("img");
      img.className = "scrapbook-hero_drop";
      img.alt = "";
      img.src = `${STICKERS}${dropSet[dropCount % dropSet.length]}.webp`;
      img.style.left = `${e.clientX - box.left}px`;
      img.style.top = `${e.clientY - box.top}px`;
      img.style.setProperty("--r", `${Math.round(Math.random() * 50 - 25)}deg`);
      drops.appendChild(img);
      dropCount += 1;
      if (drops.children.length > 14) drops.firstElementChild.remove();
    });
  }

  /* ------------------------------------------------------ line-up filter */
  const grid = $("[data-lineup]");
  if (grid) {
    const items = $$(".lineup_item:not([data-more])", grid);
    const moreCard = $("[data-more]", grid);
    const countEl = $("[data-lineup-count]");
    const emptyEl = $("[data-lineup-empty]");
    const state = { day: "all", stage: "all" };
    const dayNames = { fri: "Friday", sat: "Saturday", sun: "Sunday" };
    const stageNames = { daisy: "Big Daisy", sun: "Sun Tent", lily: "Lily Garden", deck: "Tape Deck" };

    function apply() {
      const first = new Map(items.map((li) => [li, li.getBoundingClientRect()]));
      let shown = 0;
      items.forEach((li) => {
        const match = (state.day === "all" || li.dataset.day === state.day) && (state.stage === "all" || li.dataset.stage === state.stage);
        li.hidden = !match;
        if (match) shown += 1;
      });
      emptyEl.hidden = shown > 0;
      if (moreCard) moreCard.hidden = state.day !== "all" || state.stage !== "all";
      const where = [state.day !== "all" ? `on ${dayNames[state.day]}` : "", state.stage !== "all" ? `at ${stageNames[state.stage]}` : ""].filter(Boolean).join(" ");
      countEl.textContent = state.day === "all" && state.stage === "all" ? `Showing all ${items.length} acts` : `Showing ${shown} ${shown === 1 ? "act" : "acts"} ${where}`;

      // FLIP: cards slide to their new slots like paper being shuffled
      if (reduceMotion.matches) return;
      items.forEach((li, i) => {
        if (li.hidden) return;
        const a = first.get(li);
        const b = li.getBoundingClientRect();
        if (!a.width) {
          li.animate([{ transform: "scale(1.15) rotate(6deg)", opacity: 0 }, { transform: "none", opacity: 1 }], { duration: 420, delay: i * 18, easing: "cubic-bezier(.34,1.56,.64,1)", fill: "backwards" });
          return;
        }
        const dx = a.left - b.left;
        const dy = a.top - b.top;
        if (dx || dy) li.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], { duration: 460, easing: "cubic-bezier(.2,.8,.2,1)" });
      });
    }

    $$("[data-filter-day], [data-filter-stage]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.filterDay ? "day" : "stage";
        state[key] = btn.dataset.filterDay || btn.dataset.filterStage;
        $$(key === "day" ? "[data-filter-day]" : "[data-filter-stage]").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
        apply();
      });
    });
  }

  /* ------------------------------------------------- favourites ("my picks") */
  const STORE = "daisytapes:picks";
  let picks = new Set();
  try {
    picks = new Set(JSON.parse(localStorage.getItem(STORE) || "[]"));
  } catch (_) {
    /* storage blocked: picks just won't persist */
  }

  const picksCount = $("[data-picks-count]");
  function renderPicks() {
    $$("[data-fav]").forEach((btn) => btn.setAttribute("aria-pressed", String(picks.has(btn.dataset.fav))));
    $$("[data-fav-row]").forEach((row) => row.classList.toggle("is-saved", picks.has(row.dataset.favRow)));
    if (picksCount) picksCount.textContent = picks.size ? `${picks.size} ${picks.size === 1 ? "set" : "sets"} saved` : "No sets saved yet";
    $$(".zine_panel").forEach((panel) => {
      const empty = $(".zine_picks-empty", panel);
      if (empty) empty.hidden = !zine?.classList.contains("is-picks-only") || $$(".zine_slot.is-saved", panel).length > 0;
    });
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-fav]");
    if (!btn) return;
    const id = btn.dataset.fav;
    const name = btn.getAttribute("aria-label").replace(/^Save | to my plan$/g, "");
    if (picks.has(id)) {
      picks.delete(id);
      toast(`Removed ${name} from your picks`);
    } else {
      picks.add(id);
      toast(`Saved ${name} to your picks`);
    }
    try {
      localStorage.setItem(STORE, JSON.stringify([...picks]));
    } catch (_) {
      /* ignore */
    }
    renderPicks();
  });

  /* ---------------------------------------------------- zine tabs (ARIA) */
  const zine = $("[data-zine]");
  if (zine) {
    const tabs = $$('[role="tab"]', zine);
    function select(tab, focus = true) {
      tabs.forEach((t) => {
        const on = t === tab;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        const panel = document.getElementById(t.getAttribute("aria-controls"));
        panel.hidden = !on;
        if (on && !reduceMotion.matches) {
          panel.classList.remove("is-turning");
          void panel.offsetWidth;
          panel.classList.add("is-turning");
        }
      });
      zine.style.setProperty("--tab-color", getComputedStyle(tab).backgroundColor);
      if (focus) tab.focus();
      renderPicks();
    }
    tabs.forEach((tab, i) => {
      tab.addEventListener("click", () => select(tab, false));
      tab.addEventListener("keydown", (e) => {
        const map = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 };
        if (!(e.key in map)) return;
        e.preventDefault();
        select(tabs[(map[e.key] + tabs.length) % tabs.length]);
      });
    });
    zine.style.setProperty("--tab-color", getComputedStyle(tabs[0]).backgroundColor);

    const mapTab = $("#tab-map");
    $$("[data-open-map]").forEach((a) => a.addEventListener("click", () => select(mapTab, false)));
    if (location.hash === "#map") select(mapTab, false);

    $("[data-picks-only]")?.addEventListener("change", (e) => {
      zine.classList.toggle("is-picks-only", e.target.checked);
      renderPicks();
    });
  }
  renderPicks();

  /* ---------------------------------------------------------- map pins */
  const mapTitle = $("[data-map-title]");
  const mapText = $("[data-map-text]");
  $$("[data-pin]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.pin;
      $$("[data-pin]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.pin === id)));
      mapTitle.textContent = btn.dataset.title;
      mapText.textContent = btn.dataset.text;
    });
  });

  /* ------------------------------------------------ ticket tear-off stubs */
  $$("[data-tear]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const stub = btn.closest(".ticket_card")?.querySelector(".ticket_stub");
      toast(`${btn.dataset.tear} added. Checkout opens here on the live site.`);
      if (!stub || reduceMotion.matches || stub.classList.contains("is-torn")) return;
      stub.classList.add("is-torn");
      setTimeout(() => {
        stub.classList.remove("is-torn");
        stub.classList.add("is-back");
        setTimeout(() => stub.classList.remove("is-back"), 600);
      }, 2200);
    });
  });

  /* ------------------------------------------------------ postcard form */
  const postcard = $("[data-postcard]");
  if (postcard) {
    const email = $("#pc-email", postcard);
    const status = $("[data-postcard-status]", postcard);
    const mark = $("[data-postmark]", postcard);
    postcard.addEventListener("submit", (e) => {
      e.preventDefault();
      const value = email.value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) {
        email.setAttribute("aria-invalid", "true");
        status.classList.add("is-error");
        status.textContent = value ? "That email is missing something. Check the bit after the @." : "Add your email so we know where to send it.";
        email.focus();
        return;
      }
      email.removeAttribute("aria-invalid");
      status.classList.remove("is-error");
      status.textContent = "Posted. Line-up drop 02 goes to your inbox first.";
      mark.classList.remove("is-stamped");
      void mark.getBoundingClientRect();
      mark.classList.add("is-stamped");
      toast("You're on the list. See you at the gate.");
      postcard.reset();
    });
    email.addEventListener("input", () => {
      if (email.getAttribute("aria-invalid")) {
        email.removeAttribute("aria-invalid");
        status.textContent = "";
        status.classList.remove("is-error");
      }
    });
  }

  /* ------------------------------------------- mobile sticky ticket CTA */
  const mobileCta = $("[data-mobile-cta]");
  const heroSection = $(".section_hero");
  const ticketsSection = $("#tickets");
  const footer = $(".footer_component");
  if (mobileCta && "IntersectionObserver" in window) {
    const seen = new Map();
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => seen.set(entry.target, entry.isIntersecting));
      const show = !seen.get(heroSection) && !seen.get(ticketsSection) && !seen.get(footer);
      mobileCta.classList.toggle("is-visible", show);
    });
    [heroSection, ticketsSection, footer].forEach((el) => el && io.observe(el));
  }

  /* --------------------------------------------- reveal: stick it down
     Transform-only, so every block is fully visible before and after. */
  if (!reduceMotion.matches && "IntersectionObserver" in window) {
    const slap = (el, delay = 0) =>
      el.animate(
        [
          { transform: `${getComputedStyle(el).transform === "none" ? "" : getComputedStyle(el).transform} translateY(18px) scale(1.06) rotate(2deg)` },
          { transform: getComputedStyle(el).transform }
        ],
        { duration: 620, delay, easing: "cubic-bezier(.34,1.56,.64,1)" }
      );

    const reveal = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          reveal.unobserve(entry.target);
          slap(entry.target);
        });
      },
      { threshold: 0.15 }
    );
    $$("[data-reveal], .ticket_card, .faq_note, .polaroid, .hoard_quote").forEach((el) => {
      const box = el.getBoundingClientRect();
      if (box.top > window.innerHeight) reveal.observe(el);
    });

    // hero opening: the stickers get slapped onto the poster one by one
    $$(".scrapbook-hero .sticker, .scrapbook-hero .stamp, .hero-ticket").forEach((el, i) => {
      el.animate(
        [{ scale: "1.35", translate: "0 -10px" }, { scale: "0.96", offset: 0.7 }, { scale: "1", translate: "0 0" }],
        { duration: 520, delay: 180 + i * 90, easing: "cubic-bezier(.2,.8,.2,1)" }
      );
    });

    // scribbles draw themselves on when they scroll in
    const draw = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        draw.unobserve(entry.target);
        $$("path", entry.target).forEach((p) => {
          p.style.strokeDasharray = "1";
          p.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: 1100, easing: "cubic-bezier(.6,0,.3,1)" });
        });
      });
    });
    $$("[data-draw]").forEach((el) => draw.observe(el));
  }
})();
