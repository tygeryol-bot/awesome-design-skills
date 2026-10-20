# Building the portfolio in Webflow

This folder holds the complete, tested build: `index.html`, `css/tl-portfolio.css` and `js/tl-portfolio.js`. This guide explains how to recreate it in Webflow. You can do that by hand in the Designer, or I can build it through the Webflow connector once there is a site to build it in.

## 0. Current status

| | |
|---|---|
| Local build | Finished and tested: desktop, tablet and mobile; keyboard; no-JS; reduced motion; axe-core (0 violations). |
| Webflow | **Nothing has been created or changed.** Your Webflow account has one site, *RockingTheDasies27MemoriesThatStick*, which is your RTD campaign. The portfolio needs its own site. The Webflow API cannot create sites, so you create a blank one and I (or you) build into it. |
| Published | No. Nothing is published until you say so. |

## 1. Plan check

Webflow's free **Starter** site plan gives you 2 static pages, 50 CMS items, 1,000 visits/month and a `.webflow.io` address. It does **not** allow custom code: no head/footer code and no Code Embed elements. Sources: [Choose a Site plan](https://help.webflow.com/hc/en-us/articles/33961232582419-Choose-a-Site-plan), [Custom code in head and body tags](https://help.webflow.com/hc/en-us/articles/33961357265299-Custom-code-in-head-and-body-tags). Check [webflow.com/pricing](https://webflow.com/pricing) before you rely on these limits.

The build is therefore split into two layers:

| Feature | Native Webflow (any plan) | Needs custom code (paid plan) |
|---|---|---|
| One continuous page, section IDs, anchor links, smooth scroll | ✓ | |
| Fixed nav + current-section highlight | ✓ Webflow adds `w--current` to in-page links automatically | |
| Brand colours, fonts, spacing as Variables | ✓ | |
| Selection box with 8 handles | ✓ two divs with background layers (§5) | Shorter pseudo-element version in `webflow/head-code.html` |
| Scroll reveals, hero entrance, hover states, scroll progress bar | ✓ Webflow Interactions (§8) | JS version in `webflow/footer-code.html` |
| Case files (project pop-ups) | ✓ native **Modal** element | |
| Torn paper edges, grain, paper texture, FPO placeholders | ✓ images and background layers | |
| Headline sized to the exact width of the grid (measures the font) | ≈ vw font sizes per breakpoint | ✓ `cqi` + JS fit |
| Placeholder "⚑ TO ADD" flags | Use a small visible tag element instead | ✓ `attr()` flags |
| `prefers-reduced-motion` override | Keep Interactions short and subtle | ✓ in head code |
| Custom domain | Paid site plan | |

## 2. Site setup

**Fonts** (Site settings → Fonts)
- Google Fonts: **Space Grotesk** 300, 400, 500, 600, 700.
- Custom fonts: **Akira Expanded** (Super Bold) and **Holidays Homework**. Upload these only once you have files whose licence covers web embedding. Neither is bundled in this repo.
- Until then, add the fallbacks from Google Fonts: **Archivo** 800/900 (set at its widest width, 125, for an expanded look; if the width axis isn't offered, Archivo Black is the nearest static option) and **Gochi Hand**.

**Variables** (collection "TL Brand")

| Variable | Value |
|---|---|
| `tl/red` | `#F90001` |
| `tl/black` | `#231F20` |
| `tl/grey` | `#A7A9AC` |
| `tl/white` | `#FFFFFF` |
| `tl/font-display` | Akira Expanded → Archivo → Arial Black |
| `tl/font-body` | Space Grotesk → system-ui |
| `tl/font-hand` | Holidays Homework → Gochi Hand |
| `tl/gutter` | `clamp(16px, 3.4vw, 48px)` |
| `tl/gap` | `clamp(12px, 1.7vw, 24px)` |
| `tl/section-y` | `clamp(96px, 11vw, 176px)` |
| `tl/nav-h` | `56px` (52px ≤ 767) |
| `tl/fs-body` | `17px` (16px ≤ 767, 18px ≥ 1440) |
| `tl/fs-lead` | `clamp(19px, 1.5vw, 24px)` |
| `tl/fs-h2` | `clamp(46px, 10.2vw, 168px)` |
| `tl/fs-h3` | `clamp(40px, 7.2vw, 116px)` |

Rules carried over from the brand guide:
- **Red** is only for large type (24px+, or 19px+ bold), rules, borders and the selection box. Small text in red fails WCAG contrast on both white and black.
- **Silver grey** text only goes on black (6.9:1). On white it is for rules and borders only.
- **On the red Contact section**, every piece of text is large.

**Breakpoints:** base = desktop, 991px tablet, 767px mobile landscape and 479px mobile portrait. The CSS uses exactly these, so every `@media` block maps to a Webflow breakpoint.

**Body:** background `tl/black`, colour `tl/white`, font `tl/font-body`, size `tl/fs-body`, line-height 1.55.

## 3. Assets to upload

| File (assets/img/) | Used for | Alt text |
|---|---|---|
| `paper-grid.webp` | Hero, About and case-file background (from your brand guide) | decorative |
| `grain.png` | Top background layer on every section (repeat) | decorative |
| `portrait-sticker-1000.webp`, `-560.webp` | Hero portrait | "Portrait of Tyger Lee, cut out with a rough vivid-red outline like a sticker." |
| `portrait-halftone.webp` | About portrait | "Tyger Lee's portrait, reprinted as a coarse black halftone like a photocopy." |
| `torn-edge-black.svg`, `torn-edge-red.svg` | Section edges | decorative (empty alt) |
| `handle.svg`, `handle-dark.svg` | Selection-box handles | background only |
| `cursor.svg` | Hover cursor on project frames | background only |
| `favicon.svg`, `og-image.jpg` | Site settings → favicon / Open Graph image | — |

## 4. Page structure (Navigator)

Use the same class names as the local build. Webflow combo classes are the `is-*` classes, for example `tl-project` + `is-feature`.

```
Body
├─ Link tl-skip → #main
├─ Div tl-nav (fixed, top 0, z 50)
│  ├─ Link tl-nav-brand → #top            "Tyger Lee" / "TL" (≤479)
│  ├─ Text tl-nav-now                      (hidden ≤991)
│  ├─ Nav tl-nav-menu > List tl-nav-list > Link tl-nav-link ×3 → #work #about #contact
│  └─ Div tl-progress > Div tl-progress-bar
├─ Main #main
│  ├─ Section tl-hero #top
│  │  ├─ List tl-hero-meta (4 items)
│  │  ├─ Div tl-hero-stage
│  │  │  ├─ Div tl-hero-name-wrap > H1 tl-hero-title tl-select ("Tyger" / "Lee") + Text tl-hero-readout
│  │  │  └─ Div tl-hero-figure > Image tl-hero-portrait + Text tl-hand tl-hero-note
│  │  ├─ Div tl-hero-foot > Paragraph tl-hero-statement + Link tl-scroll-cue → #work
│  │  └─ Image tl-torn is-bottom (torn-edge-black)
│  ├─ Section tl-section is-ink tl-work #work
│  │  ├─ Div tl-work-head > eyebrow, H2 tl-h2, Paragraph tl-lede tl-work-lede, Nav tl-index
│  │  └─ Div tl-projects > 6 × Article tl-project (variants below)
│  ├─ Section tl-section is-paper tl-about #about
│  ├─ Section tl-section is-ink tl-skills #skills
│  └─ Section tl-section is-red tl-contact #contact
├─ Footer tl-footer
└─ 6 × Modal tl-case  (#case-inform, #case-cradle, …)
```

**Hero name size.** The local build measures the font and fills the grid exactly. Native equivalent with Archivo: `font-size: 20.6vw` on desktop, `20.4vw` at 991 and `20vw` at 767. On short desktop screens (preview 1280×720) check that the two lines stay under roughly 38% of the viewport height. When Akira Expanded is installed, re-tune this one value; Akira is wider than Archivo, so it will be smaller.

## 5. The selection box, natively

The brand guide's signature device is a thin red frame with 8 square handles around a heading.

1. Give the parent (heading or image wrapper) `position: relative`.
2. Inside it, add a Div **`tl-sel-frame`**: absolute, inset `-10px` (headings: `-0.07em`), border 2px `tl/red`, pointer-events none.
3. Add a Div **`tl-sel-handles`**: absolute, inset `-15px`, with **8 background-image layers** of `handle.svg`. Each layer is 12×12px, no-repeat, at these positions: `0 0`, `50% 0`, `100% 0`, `0 50%`, `100% 50%`, `0 100%`, `50% 100%`, `100% 100%`.
4. Save both as a component, **TL / Selection box**, and drop it into the hero name, case-file titles, About portrait, "loud." and nav links. For nav links, set opacity 0 and show it on the `w--current` state.

## 6. Components

| Component | Contents | Props |
|---|---|---|
| TL / Nav | §4 nav | none |
| TL / Eyebrow | number box + label + rule | number, label |
| TL / Button | `tl-btn` link with ↗ | text, link (Modal show) |
| TL / Frame | `tl-frame` + image or FPO placeholder + cursor tag | image, alt, ratio combo (`is-16x9`, `is-4x5`, …), placeholder title/spec |
| TL / Project | number, title, category, description, skills tags, button | title, number, category, description, skills, case modal; **variants:** Feature, Split, Split reverse, Pair, Banner (red), Trio |
| TL / Case file | Modal: bar, title + selection box, facts list, 3 frames, prev/next | per project |
| TL / Footer | wordmark, nav, copyright | none |

The six layout variants are what make the gallery feel art-directed rather than templated. Keep them: Feature (Inform), Split (Cradle), Split reverse with layered cover (No Signal), Staggered pair (Lebombo), Red banner (RTD), Trio (Fridge Habit).

## 7. CMS (optional)

With 6 projects and 6 bespoke layouts, static components with variants are easier to art-direct. Move to the CMS when you pass about 10 projects. Starter allows 50 items, which is plenty.

Collection **Projects**:

| Field | Type |
|---|---|
| Name, Slug | default |
| Number | Plain text ("01") |
| Discipline | Plain text |
| Summary | Plain text |
| Skills | Plain text (comma separated) |
| Layout | Option: Feature / Split / Split reverse / Pair / Banner / Trio |
| Image 1–3 | Image (+ alt text field each) |
| Creative direction | Rich text |
| Live link | Link |
| Order | Number (sort ascending) |

Use one Collection List and put all six layouts inside the item template, each with **conditional visibility** `Layout = …`. Case files can stay as Modals in the item template, or become a Collection template page (`/work/[slug]`) if you want shareable project URLs.

## 8. Interactions map

| Effect | Local build | Webflow Interaction |
|---|---|---|
| Hero entrance | CSS keyframes | Page load: name lines move Y 0.22em→0 + fade, 0.9s; selection box width 0→100% at 0.35s; portrait Y 48px + rotate 3°→-1.5° at 0.45s |
| Section text reveal | IntersectionObserver adds `.is-in` | Scroll into view on each `[data-tl-reveal]` block: opacity 0→1, Y 28px→0, 0.8s, ease out |
| Big heading wipe | `clip-path` | Scroll into view: wrap the heading in an overflow-hidden div and move it Y 100%→0 |
| Nav current section | JS adds `.is-current` | Automatic `w--current` on in-page links |
| Scroll progress bar | JS scaleX | While page is scrolling: `tl-progress-bar` scale X 0→1 across the page |
| Frame hover | CSS `:hover` | Mouse hover on `tl-frame`: selection-box divs opacity 0→1; cursor tag opacity 0→1, move 14px→0 |
| Case files | `<dialog>` + JS | Native Modal; set each button's link to *Modal → show* and the close button to *Modal → hide* |
| Back to top | `#top` link | Same link |

## 9. Custom code (paid plans only)

- `webflow/head-code.html` → Site settings → Custom code → **Head code**. It contains the pseudo-element selection boxes, `cqi` sizing, reveal classes, placeholder flags, keyframes and the reduced-motion override. Replace the two `PASTE-…-ASSET-URL` values with the uploaded `handle.svg` / `handle-dark.svg` URLs.
- `webflow/footer-code.html` → **Footer code**. This is the same script as `js/tl-portfolio.js`. It needs these custom attributes on the elements (Element settings → Custom attributes):
  - `data-tl-progress`, `data-tl-now`, `data-tl-nav`
  - `data-tl-section`, `data-tl-label`, `data-tl-reveal`
  - `data-tl-fit`, `data-tl-fit-word`, `data-tl-case`, `data-tl-close`
- If you use native Modals, delete section 5 ("Case files") of the script.

## 10. Before publishing

- [ ] Real project images in every frame. Remove `aria-hidden` from a frame link once it holds a real image, and write descriptive alt text.
- [ ] Email and social links filled in, placeholder flags removed.
- [ ] Akira Expanded and Holidays Homework uploaded (licensed), fallback sizes re-checked.
- [ ] Page title, meta description and Open Graph image set in Page settings.
- [ ] Preview at 1440, 1280×720, 991, 767, 390 and 360.
- [ ] Publish to the `.webflow.io` staging address first.
