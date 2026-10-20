# Analog Scrapbook × Webflow: build guide

This is the system behind `index.html`: torn paper, translucent tape, stickers and xeroxed type, organised so it can be rebuilt in Webflow class by class. Naming follows **Client-First** (Finsweet), so it also works with Relume components.

## 1. Files

| Path | What it is |
| --- | --- |
| `index.html` | The full festival page: nav, hero, about, line-up, schedule + map, tickets, FAQ, sign-up, footer |
| `css/scrapbook.css` | Tokens, Client-First utilities, surfaces, components, motion, breakpoints |
| `js/scrapbook.js` | Filters, tabs, favourites, tilt, sticker drops, tear-off stubs, form. No dependencies |
| `assets/stickers/*.webp` | Cut-outs from your two asset sheets (white background removed) |
| `assets/paper/*.webp` | Torn notebook sheets, blue lined paper, the two printed cards, gingham |
| `assets/texture/crumple-*.webp` | Your crumpled-paper texture (grey version is mirror-tiled so it repeats without seams) |
| `embeds/01–06` | Paste-ready Webflow Embed snippets: head code, SVG defs, tape, scribbles, starburst, tear masks |

## 2. Setting it up in Webflow

1. **Head code** (Site settings › Custom code › Head): paste `embeds/01-site-head.html`. Webflow's custom-code fields are capped in length, so **link** `scrapbook.css` rather than pasting it. Host it anywhere public; jsDelivr can serve it straight from this repo (`https://cdn.jsdelivr.net/gh/<owner>/<repo>@<branch>/templates/scrapbook-festival/css/scrapbook.css`).
2. **SVG defs**: drop an Embed as the first child of `Body` and paste `embeds/02-svg-defs.html` (the `#rough-ink` filter and the arrow, star, check and plus icons). Make it a Symbol/Component so every page gets it.
3. **Assets**: upload `assets/**`. If the CSS is hosted outside Webflow, either keep `/assets` next to `/css` on the same host, or change the two texture variables (`--tex-crumple`, `--tex-crumple-blue`) and the `surface-gingham` / `surface-blue-lined` / `note-paper_sheet` URLs to your Webflow asset URLs.
4. **Footer code**: paste `js/scrapbook.js` inside `<script>` (or link it). It only looks for `data-*` attributes, so renaming classes won't break it.
5. **Build sections** with the class trees in §5. Create the classes in the Designer with the same names. The visual rules come from the linked stylesheet, so Designer styling stays light (layout, spacing, text).

> Why a linked stylesheet? `clip-path` polygons, masks, `backdrop-filter`, multi-layer blended backgrounds and custom-property surfaces can't be set in the Designer's style panel. Keeping them in one file also means one source of truth for every page.

## 3. Class architecture

```
page-wrapper
└─ main-wrapper
   └─ section_[name]                 one per section: section_hero, section_lineup…
      └─ padding-global              side gutter (safe-area aware)
         └─ container-large          80rem max (container-medium 64rem, container-small 48rem)
            └─ padding-section-*     vertical rhythm (small / medium / large)
               └─ [component]        hero component, lineup_component, ticket_grid…
                  └─ [component]_[element]   scrapbook-hero_headline, lineup_card…
```

| Kind | Pattern | Examples |
| --- | --- | --- |
| Section wrapper | `section_[name]` | `section_hero`, `section_zine`, `section_tickets` |
| Component root | `[name]_component` or a named global | `hoard_component`, `scrapbook-hero`, `paper-card`, `tape-badge` |
| Child element | `[component]_[element]` | `lineup_poster`, `ticket_stub`, `zine_tab` |
| Variant (combo) | `is-[variant]` | `tape-badge is-acid is-corner is-tl`, `ticket_card is-featured` |
| Surface (combo) | `surface-[paper]` | `paper-bg_sheet surface-denim`, `lineup_poster surface-gingham` |
| Utility | Client-First | `heading-style-h2`, `text-size-small`, `margin-bottom margin-small`, `hide-mobile-landscape` |

### Surfaces only set variables

A `surface-*` class sets four custom properties: `--bg-color`, `--bg-image`, `--bg-size` and `--bg-blend`. The element that paints them reads the variables, so one class works on a flat block (`bg-surface surface-mustard`) and on the torn-paper pseudo layer inside `paper-bg_sheet`.

| Surface | Looks like |
| --- | --- |
| `surface-denim` | Poster blue, white graph grid, your crumple texture multiplied in (hero, schedule band) |
| `surface-mustard` | "Hoard the feelings" mustard with a darker grid |
| `surface-graph` | White graph paper (line-up binder page) |
| `surface-lined` | Cream notebook paper with the faded red-brown ruling from your sheets (zine pages) |
| `surface-night` | Black construction paper (tickets, footer) |
| `surface-pulp` / `surface-white` | Page cream / fresh sheet |
| `surface-butter`, `surface-lemon`, `surface-acid`, `surface-orange`, `surface-denim-plain` | Flat coloured stock with grain + crumple |
| `surface-gingham`, `surface-blue-lined` | Your gingham square and blue lined sheet as tiles |

### Tokens

| Token | Value | Role |
| --- | --- | --- |
| `--pulp` | `#f1eadb` | Page background (raw pulp) |
| `--paper-white` | `#fffdf6` | Fresh sheets, torn-fibre cores, stickers' die-cut border |
| `--paper-cream` / `--paper-line` | `#ebe3cc` / `#d8ab9c` | Notebook paper + ruling, sampled from your torn sheets |
| `--ink` | `#16130f` | Carbon print text |
| `--ink-soft` | `#5b5546` | Secondary text on pulp (6.2 : 1) |
| `--ink-navy` | `#22346e` | Binder-clip navy: serif headings, handwriting |
| `--denim` | `#6f87b8` | Poster blue. White display text on it is 3.5 : 1, so it's for large type only |
| `--butter` / `--lemon` / `--mustard` | `#ffe58a` / `#ffd92e` / `#d29a22` | Yellows from the sticker sheet |
| `--acid` | `#e6ff2e` | Fluorescent tape, active states, highlighter |
| `--neon-orange` | `#ff6a1f` | Second tape, highlighter swipe, alerts |
| `--font-display` | Londrina Solid 900 | Brush-poster headlines (always uppercase, skewed −7°, `#rough-ink`) |
| `--font-sketch` | Cabin Sketch 700 | Short handwritten display lines only |
| `--font-marker` | Permanent Marker | Captions, signatures, form input |
| `--font-serif` | Fraunces (SOFT 100) | Body copy, dictionary, schedule acts, soft serif headings |
| `--font-mono` | Space Mono | Metadata, label strips, buttons, prices' small print |
| `--drop-1/2/3` | stacked `drop-shadow()` | Paper resting → lifted → held up |
| `--ease-back` | `cubic-bezier(.34,1.56,.64,1)` | Sticky "slap" overshoot for anything paper |

## 4. The three key components (exact CSS)

### a) `.tape-badge`: translucent tape with torn ends

Text-bearing or decorative. `--r` sets the rotation offset (default `-2.5deg`); vary it per instance with a custom attribute `style="--r:3deg"` or the `is-tl / is-tr / is-bl / is-br / is-top` placements. The long edges of the clip polygon reach past the box (`-6px` / `100% + 16px`), so the `box-shadow` survives the torn-end `clip-path`.

```css
/* 5a. TAPE BADGE — translucent masking tape, torn ends, rotation offsets ---- */
.tape-badge {
  --tape: var(--tape-kraft);
  --r: -2.5deg;
  position: relative;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5em;
  min-height: 2.1em;
  padding: 0.45em 1.35em;
  font-family: var(--font-mono);
  font-size: var(--text-tiny);
  font-weight: 700;
  letter-spacing: 0.1em;
  line-height: 1.1;
  text-transform: uppercase;
  color: var(--ink);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0) 45%, rgba(22, 19, 15, 0.06)),
    repeating-linear-gradient(97deg, rgba(255, 255, 255, 0.1) 0 1px, transparent 1px 4px),
    var(--tape);
  -webkit-backdrop-filter: blur(1.5px) saturate(1.15);
  backdrop-filter: blur(1.5px) saturate(1.15);
  box-shadow: var(--shadow-tape), inset 0 0 0 1px rgba(255, 255, 255, 0.16);
  clip-path: var(--tape-ends);
  transform: rotate(var(--r));
  transform-origin: 18% 50%;
  transition: transform var(--dur) var(--ease-back), box-shadow var(--dur) var(--ease-paper);
  pointer-events: none;
}

/* the lifted end catches light while it peels */
.tape-badge::after {
  content: "";
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 22%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.6) 62%, rgba(22, 19, 15, 0.1));
  opacity: 0;
  transition: opacity var(--dur);
}

.tape-badge.is-kraft { --tape: var(--tape-kraft); }
.tape-badge.is-acid { --tape: var(--tape-acid); }
.tape-badge.is-orange { --tape: var(--tape-orange); }
.tape-badge.is-clear { --tape: var(--tape-clear); }
.tape-badge.is-butter { --tape: var(--tape-butter); }
.tape-badge.is-alt { clip-path: var(--tape-ends-alt); }

/* decorative pieces stuck over corners / edges */
.tape-badge.is-corner,
.tape-badge.is-top {
  position: absolute;
  width: clamp(4.5rem, 3.5rem + 3vw, 7rem);
  min-height: 0;
  height: 1.9rem;
  padding: 0;
}
.tape-badge.is-tl { top: -0.7rem; left: -1.6rem; --r: -36deg; }
.tape-badge.is-tr { top: -0.7rem; right: -1.6rem; --r: 36deg; }
.tape-badge.is-bl { bottom: -0.7rem; left: -1.6rem; --r: 34deg; }
.tape-badge.is-br { bottom: -0.7rem; right: -1.6rem; --r: -34deg; }
.tape-badge.is-top { top: -0.95rem; left: 50%; translate: -50% 0; --r: -3deg; }

/* peel: hover the tape, or any card that carries it */
.tape-badge.is-peel:hover,
.paper-card:hover .tape-badge,
.polaroid:hover .tape-badge,
.lineup_card:hover .tape-badge,
.faq_note:hover .tape-badge {
  transform: rotate(calc(var(--r) - 7deg)) translate(3px, -4px) scaleX(0.97);
  box-shadow: 0 2px 2px rgba(22, 19, 15, 0.12), 0 14px 14px -8px rgba(22, 19, 15, 0.42), inset 0 0 0 1px rgba(255, 255, 255, 0.2);
}
.tape-badge.is-peel:hover::after,
.paper-card:hover .tape-badge::after,
.polaroid:hover .tape-badge::after,
.lineup_card:hover .tape-badge::after,
.faq_note:hover .tape-badge::after {
  opacity: 1;
}
```

### b) `.paper-card`: shadow wrapper, torn sheet, content

Always three layers: the **wrapper** holds `filter: drop-shadow()` and must never be clipped. The **sheet** (`paper-card_paper`) carries the torn `clip-path` and a surface. **Tape** sits on the wrapper so it can hang over the edge. `is-fiber` gives a torn sheet whose white core shows along the tear (two offset polygons). `paper-bg` is the same idea as a background layer for whole components, so content can overflow the paper.

```css
/* 5b. PAPER CARD — shadow wrapper + torn sheet + content ------------------ */
.paper-card {
  --r: 0deg;
  --lift: 0px;
  position: relative;
  filter: var(--drop-2);
  transform: translateY(var(--lift)) rotate(var(--r));
  transition: transform var(--dur-slow) var(--ease-back), filter var(--dur) var(--ease-paper);
}

.paper-card_paper {
  position: relative;
  isolation: isolate;
  padding: clamp(1.25rem, 0.9rem + 1.6vw, 2.25rem);
  clip-path: var(--tear-a);
}

/* faint fold crease + extra grain on every sheet */
.paper-card_paper::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background: linear-gradient(118deg, transparent 47%, rgba(255, 255, 255, 0.4) 49.4%, rgba(22, 19, 15, 0.07) 50%, transparent 53%);
}

.paper-card_paper.is-tear-b { clip-path: var(--tear-b); }
.paper-card_paper.is-tear-c { clip-path: var(--tear-c); }

/* white fibre edge: the sheet's white core shows where the coloured face tore */
.paper-card_paper.is-fiber {
  background: var(--paper-white);
  clip-path: var(--tear-fiber);
}
.paper-card_paper.is-fiber::before {
  content: "";
  position: absolute;
  inset: 5px;
  z-index: -2;
  clip-path: var(--tear-b);
  background-color: var(--bg-color, var(--pulp));
  background-image: var(--bg-image, none);
  background-size: var(--bg-size, auto);
  background-blend-mode: var(--bg-blend, normal);
}

.paper-card:hover,
.paper-card:focus-within {
  --lift: -6px;
  filter: var(--drop-3);
}
/* 5c. PAPER BG — torn sheet behind a whole component (content can overflow) */
.paper-bg {
  --r: 0deg;
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  filter: var(--drop-2);
  transform: rotate(var(--r));
}

.paper-bg_sheet {
  position: absolute;
  inset: 0;
  background: var(--paper-white);
  clip-path: var(--tear-fiber);
}

.paper-bg_sheet::before {
  content: "";
  position: absolute;
  inset: var(--fiber, 7px);
  clip-path: var(--tear-b);
}

/* full-bleed bands: torn top + bottom only */
.paper-bg.is-band { filter: var(--drop-1); }
.paper-bg.is-band .paper-bg_sheet { clip-path: var(--tear-band); }
.paper-bg.is-band .paper-bg_sheet::before { inset: 9px 0; clip-path: var(--tear-band-inner); }

.paper-bg.is-band-top .paper-bg_sheet { clip-path: var(--tear-top); }
.paper-bg.is-band-top .paper-bg_sheet::before { inset: 9px 0 0; clip-path: var(--tear-top-inner); }
```

### c) `.scrapbook-hero`: offset collage grid

12-column grid on top of a torn denim poster (`paper-bg`). The headline, kicker and note stack in columns 1–7. The collage (polaroid, stickers) and the ticket CTA share columns 8–12, and decorative stars/stamp are absolutely placed so they can cross the poster edge. On tablet and mobile everything stacks: headline → kicker → collage → note → ticket → "book your ticket".

```css
/* 8. SCRAPBOOK HERO ======================================================== */
.section_hero {
  position: relative;
  padding-block: clamp(1rem, 0.5rem + 2vw, 2rem) clamp(2.5rem, 2rem + 3vw, 4rem);
}

.scrapbook-hero {
  position: relative;
  isolation: isolate;
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  column-gap: clamp(0.75rem, 1.6vw, 1.5rem);
  row-gap: clamp(1.75rem, 3vw, 2.5rem);
  padding: clamp(1.75rem, 1rem + 3.4vw, 4rem) clamp(1.25rem, 0.5rem + 3.6vw, 4rem) clamp(1.75rem, 1rem + 3vw, 3.25rem);
}

.scrapbook-hero .paper-bg { --r: -0.6deg; }

.scrapbook-hero_headline {
  position: relative;
  z-index: 3;
  grid-column: 1 / span 9;
  grid-row: 1;
  font-family: var(--font-display);
  font-weight: 900;
  font-size: var(--text-display);
  line-height: 0.84;
  letter-spacing: 0.005em;
  text-transform: uppercase;
  color: var(--paper-white);
  filter: url(#rough-ink);
}

.scrapbook-hero_line {
  display: block;
  transform: skewX(-7deg);
  transform-origin: 0 100%;
}

.scrapbook-hero_line:nth-child(2) { margin-left: 0.18em; }

.scrapbook-hero_kicker {
  position: relative;
  z-index: 3;
  grid-column: 1 / span 7;
  grid-row: 2;
  align-self: start;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem 0.9rem;
}

.scrapbook-hero_note {
  position: relative;
  z-index: 2;
  grid-column: 1 / span 7;
  grid-row: 3;
  margin-top: clamp(2rem, 4vw, 3rem);
  margin-left: clamp(0rem, 3vw, 2.5rem);
}

.scrapbook-hero_meta {
  font-family: var(--font-mono);
  font-size: clamp(0.72rem, 0.65rem + 0.3vw, 0.85rem);
  line-height: 1.5;
  letter-spacing: 0.04em;
  color: var(--ink-soft);
}

.scrapbook-hero_collage {
  position: relative;
  z-index: 1;
  grid-column: 8 / span 5;
  grid-row: 1 / span 3;
  align-self: stretch;
  min-height: 34rem;
}

.scrapbook-hero_polaroid {
  position: absolute;
  top: 12%;
  right: 4%;
  width: min(86%, 22rem);
  --r: 5deg;
}

.scrapbook-hero_cta {
  position: relative;
  z-index: 4;
  grid-column: 8 / span 5;
  grid-row: 3;
  align-self: end;
  justify-self: end;
  width: 100%;
  max-width: 25rem;
  margin-bottom: 0.5rem;
}

.scrapbook-hero_star { --w: clamp(4.5rem, 9vw, 8.5rem); }
.scrapbook-hero_star.is-a { --r: -10deg; left: -3%; top: 49%; }
.scrapbook-hero_star.is-b { --w: clamp(4rem, 8vw, 7.5rem); --r: 12deg; left: 3.5%; top: 58%; }
.scrapbook-hero_star.is-c { --w: clamp(4rem, 7vw, 6.5rem); --r: 8deg; right: -2.5%; bottom: 7%; }

.scrapbook-hero_sticker.is-sunflower { --w: clamp(6rem, 11vw, 9.5rem); --r: -8deg; top: 2%; right: -3%; z-index: 1; }
.scrapbook-hero_sticker.is-smiley { --w: clamp(4.5rem, 7vw, 6.5rem); --r: -12deg; top: 57%; left: -2%; }
.scrapbook-hero_sticker.is-heart { --w: clamp(3.5rem, 5vw, 5rem); --r: 16deg; top: 64%; right: 8%; }

.scrapbook-hero_stamp {
  position: absolute;
  z-index: 3;
  left: -1.25rem;
  bottom: -2.75rem;
  --r: -6deg;
}

.scrapbook-hero_book {
  position: relative;
  z-index: 3;
  grid-column: 1 / -1;
  grid-row: 4;
  align-self: end;
  margin-top: 2.25rem;
  display: inline-flex;
  align-items: baseline;
  gap: 0.4em;
  width: fit-content;
  font-family: var(--font-display);
  font-weight: 900;
  font-size: clamp(1.4rem, 0.9rem + 2vw, 2.6rem);
  line-height: 1;
  text-transform: uppercase;
  text-decoration: none;
  color: var(--paper-white);
  transform: skewX(-7deg);
  filter: url(#rough-ink);
}

.scrapbook-hero_book span { color: var(--acid); }
.scrapbook-hero_book:hover { color: var(--acid); }
```

Hover states in the hero: the polaroid and note tilt toward the cursor (`data-tilt`), stickers spin and lift (`sticker is-hover`), the binder clip loosens, the stamp rocks, the ticket stub starts to tear. Clicking empty poster space sticks one of your stickers where you clicked (`data-hero`, max 14).

## 5. Section trees (Navigator)

**Hero**
```
section_hero
└─ padding-global > container-large
   └─ scrapbook-hero                         [data-hero]
      ├─ paper-bg > paper-bg_sheet.surface-denim
      ├─ scrapbook-hero_headline (H1) > scrapbook-hero_line ×3
      ├─ scrapbook-hero_kicker > label-strip.is-dymo [data-countdown] + label-strip + scrapbook-hero_hint
      ├─ scrapbook-hero_collage
      │  ├─ sticker.scrapbook-hero_sticker.is-sunflower / is-smiley / is-heart
      │  └─ polaroid.scrapbook-hero_polaroid [data-tilt] > sticker(tape-stars) + polaroid_photo > img + polaroid_caption
      ├─ scrapbook-hero_note > note-paper [data-tilt] > note-paper_clip + note-paper_sheet > note-paper_text ×2 + scrapbook-hero_meta
      │  └─ stamp.scrapbook-hero_stamp > stamp_inner
      ├─ sticker.scrapbook-hero_star.is-a / is-b / is-c
      ├─ scrapbook-hero_book (link)
      ├─ scrapbook-hero_cta > hero-ticket (link) > tape-badge.is-top + hero-ticket_main + hero-ticket_stub
      └─ scrapbook-hero_drops [data-drops]
```

**Line-up** (bind `lineup_grid` to a CMS Collection List)
```
section_lineup > padding-global > container-large > lineup_component
├─ paper-bg > paper-bg_sheet.surface-graph            (binder holes are its ::after)
├─ lineup_header > lineup_kicker + H2.ransom [data-ransom]
├─ lineup_filters [data-filters]
│  ├─ lineup_filter-group (role=group) > lineup_chip.is-day   [data-filter-day="all|fri|sat|sun"]
│  └─ lineup_filter-group (role=group) > lineup_chip.is-stage [data-filter-stage="all|daisy|sun|lily|deck"]
├─ lineup_status > lineup_count [data-lineup-count] (aria-live)
├─ lineup_grid [data-lineup]
│  └─ lineup_item (.is-headliner) [data-day][data-stage]
│     └─ lineup_card [data-tilt] > tape-badge.is-corner + lineup_poster.surface-* > lineup_meta + lineup_art + lineup_text + lineup_save [data-fav]
└─ lineup_empty [data-lineup-empty]
```
CMS "Acts" fields: Name, Genre, Day (option: fri/sat/sun), Stage (option: daisy/sun/lily/deck), Set time, Sticker (image), Surface (option → combo class), Name style (option: is-serif/is-sketch/is-marker), Headliner (switch → `is-headliner`). Bind Day/Stage to the `data-day` / `data-stage` custom attributes and the slug to `data-fav`.

**Schedule + map zine**
```
section_zine
├─ paper-bg.is-band > paper-bg_sheet.surface-denim
└─ padding-global > container-large
   ├─ zine_header > zine_title + zine_lede
   └─ zine_component [data-zine]
      ├─ zine_tabs (role=tablist) > zine_tab (role=tab, aria-controls) ×4
      ├─ zine_book > zine_panel (role=tabpanel) ×4
      │  └─ zine_spread > zine_staple ×2 + zine_page.surface-lined ×2
      │     └─ zine_stage > zine_stage-name + zine_slots > zine_slot [data-fav-row] > zine_time + zine_act + zine_star [data-fav]
      │  (map panel) zine_spread.map_layout > map_side (map_legend + map_info) + map_canvas > map_paths + map_pin ×10
      └─ zine_toolbar > switch [data-picks-only] + zine_picks-count
```
Use Webflow's native Tabs only if you're happy to lose the zine tab styling. The custom tabs here are full ARIA tabs (arrow keys, Home/End) driven by `scrapbook.js`.

**Tickets**
```
section_tickets
├─ paper-bg.is-band > paper-bg_sheet.surface-night
└─ padding-global > container-large
   ├─ ticket_header > ticket_title + ticket_phase
   └─ ticket_grid
      └─ ticket_card (.is-featured) style="--band:…"
         ├─ ticket_band > ticket_band-text + ticket_clasp          (the wristband)
         ├─ callout-burst / sticker                                 (optional)
         └─ ticket_body.surface-* > ticket_admit, ticket_name, ticket_tagline, ticket_price, ticket_features, button [data-tear]
            ticket_stub.surface-* > ticket_stub-type + ticket_barcode + ticket_serial   (tear-off stub)
```

## 6. Motion and micro-interactions

Hover states are pure CSS, so they work in Webflow with no Interactions set up. Keep IX2 for scroll and page-load moments. `prefers-reduced-motion` turns off the marquee, tilt, jitter and reveals.

| Effect | Where | How it's built | IX2 equivalent |
| --- | --- | --- | --- |
| **Tape peel** | any `tape-badge` on a hovered card | `rotate(calc(var(--r) - 7deg)) translate(3px,-4px) scaleX(.97)`, deeper shadow, `::after` highlight on the lifted end, `transform-origin: 18% 50%` | Mouse hover on card → affect *Children* `.tape-badge`: Rotate Z −7°, Move X 3px / Y −4px, 300 ms, ease Out Back |
| **Poster tilt** | `[data-tilt]` (line-up cards, polaroid, note) | JS writes `--tilt-x/--tilt-y` from pointer position (±9° / ±11°), only on fine pointers | Mouse move in viewport on element → Rotate X/Y −9…9°, smoothing 85% |
| **Paper lift** | `paper-card`, `lineup_card`, `ticket_card` | `--lift: -6/-8px` + `filter` from `--drop-2` to `--drop-3` (same shadow count, so it interpolates) | Hover → Move Y −8px, 450 ms Out Back (shadow stays in CSS) |
| **Xerox grunge** | line-up card hover | halftone + grain `::after` fades to .6, name gets orange/denim misregistration + `steps(2)` jitter | CSS only |
| **Ticket stub tear** | `ticket_card` hover / `[data-tear]` click | hover: stub rotates −3° from its top-right corner. Click: `stub-fall` keyframes, stub returns after 2.2 s, toast confirms | Hover → `.ticket_stub` Rotate Z −3°, Move 5px; Click → Move Y 260px, Rotate 26°, Opacity 0 |
| **Sticker slap** | hero stickers on load, stickers you click onto the poster | WAAPI `scale 1.35 → .96 → 1`, 520 ms, 90 ms stagger | Page load → each sticker: Scale 135% → 100%, stagger 90 ms |
| **Scroll reveal** | `[data-reveal]`, tickets, FAQ notes, polaroids | transform-only "stick down" (no opacity), so nothing is hidden before it animates | Scroll into view → Move Y 18px→0, Rotate 2°→0 |
| **Page turn** | zine tab change | `page-turn` keyframes: `perspective(1400px) rotateY(-10deg)` → flat | CSS only |
| **Scribble draw** | `[data-draw]` svgs | `pathLength="1"` + dashoffset 1 → 0 | Scroll into view → animate `stroke-dashoffset` (GSAP) |
| **Marquee tape** | `marquee_track` | duplicated group, `translateX(-50%)` loop, pauses on hover | Loop: Move X −50%, linear |

GSAP version of the hover lift + peel, if you'd rather drive everything from Webflow's GSAP:

```js
gsap.utils.toArray(".lineup_card").forEach((card) => {
  const tape = card.querySelector(".tape-badge");
  const tl = gsap.timeline({ paused: true, defaults: { duration: 0.35, ease: "back.out(2)" } })
    .to(card, { y: -8 }, 0)
    .to(tape, { rotation: "-=7", x: 3, y: -4, scaleX: 0.97, transformOrigin: "18% 50%" }, 0);
  card.addEventListener("mouseenter", () => tl.play());
  card.addEventListener("mouseleave", () => tl.reverse());
});
```

## 7. Responsive behaviour

| Breakpoint | Changes |
| --- | --- |
| Desktop ≥ 992 | 12-col hero collage, 4-col line-up (headliners span 2), two-page zine spread, 3 tickets |
| Tablet ≤ 991 | Nav collapses to the label "Menu" sticker + full-screen lined-paper sheet. Hero stacks, line-up 3 cols, tickets 2 cols, FAQ 2 cols |
| Mobile landscape ≤ 767 | Line-up 2 cols with horizontally scrolling filter chips, zine becomes one page per side, tickets stack (max 26rem), postcard stacks, sticky "Tickets from R650" tape appears once the hero has scrolled away (hidden again over tickets and the footer) |
| Mobile portrait ≤ 479 | Headliners go full-width, smaller poster padding, card names keep scaling with their card (container-query units) |

Gutters use `max(var(--gutter), env(safe-area-inset-*))`, so content clears the notch and the home indicator. The nav is sticky at `env(safe-area-inset-top)`.

## 8. Accessibility checks

- Display type only appears at large sizes; body text is ink on pulp/cream/butter (≥ 6 : 1).
- Every tilt and peel is decorative. Content and controls are real buttons and links with visible `:focus-visible` (ink outline + acid halo; inset bar on tabs).
- Filters are `aria-pressed` toggle buttons in labelled groups; the result count is a polite live region.
- Tabs follow the ARIA tabs pattern; favourites are `aria-pressed` with the act name in the label.
- Ransom headings keep the real text in a visually hidden span; the letter tiles are `aria-hidden`.
- Reveals animate transform only, so a screenshot, a print or a reader with JS off sees every block.
- `prefers-reduced-motion: reduce` removes the marquee, jitter, tilt, reveals and the tear animation.

## 9. Assets and swaps

Every picture on the page comes from the sheets you supplied:

- **Paper / denim / clip sheet**: `paper-cream-a/b` (hero note, both torn notebook sheets), `paper-blue-lined` (Golden Daisy ticket, line-up card), `star-denim-a/b/c`, `clip-navy`
- **Yellow sticker sheet**: `lily`, `star-clay`, `button-heart`, `starburst-yellow`, `eye`, `smiley`, `star-painted`, `bow-clay`, `flower-orange`, `fish`, `button-round`, `tape-stars`, `sun-face`, `ribbon`, `sunflower`, `button-flower`, plus `card-everything-easy`, `card-lovely-yellow`, `gingham`
- **Crumpled blue paper**: `crumple-blue`, and `crumple-grey` derived from it for tinting every other paper colour

The sheets had no crowd or artist photos, so the hero polaroid holds the "how lovely yellow is" card (`data-slot="crowd-photo"`). Swap in a real photo there and on the line-up cards (`lineup_art`) when you have them. Photos look right with the existing `filter: contrast(1.05) saturate(1.08)` on the polaroid. On coloured flyers, try `filter: grayscale(1) contrast(1.4); mix-blend-mode: multiply;` for a photocopied look.

The crumpled texture preview carried a psdgraphics.com watermark, which was cropped off. Download the full file from psdgraphics.com for production and check its licence.
