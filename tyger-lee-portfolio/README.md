# Tyger Lee — Graphic Design Portfolio

This is a one-page, continuous-scroll portfolio built from `MINIBRANDSTYLEGUIDE.pdf`. It uses the guide's exact palette (`#F90001`, `#231F20`, `#A7A9AC`, `#FFFFFF`), oversized type, crumpled grid paper, grain, torn edges and the red selection-box device.

**Status:** this is a finished local build. It is **not in Webflow yet**; see [WEBFLOW.md](WEBFLOW.md) for the transfer plan.

## Preview it

It's plain HTML/CSS/JS with no build step. Serve the folder, don't double-click the file, so fonts and images load:

```bash
cd tyger-lee-portfolio
python3 -m http.server 8000      # then open http://localhost:8000
```

## What's on the page

| # | Section | Notes |
|---|---|---|
| 00 | Hero | "TYGER LEE" sized to fill the grid, inside the brand-guide selection box. Includes the sticker portrait from your guide's cover, a statement and a scroll cue. |
| 01 | Selected work | Index of six projects, then six deliberately different layouts. Each opens a case file (native `<dialog>`, with Esc/backdrop close and prev/next). |
| 02 | About | Halftone "photocopy" portrait, first-person bio (2nd-year, Inscape; Table View High School), spec sheet with the brand palette. |
| 03 | Skills & approach | Five disciplines, each linked to the project that proves it, plus four working principles taken from the brand guide. |
| 04 | Contact | Red section with "Let's make something loud.", an email button, socials and back to top. |
| — | Footer | Full-width wordmark, nav, © 2026. |

Interactions:
- Smooth anchor scrolling.
- Fixed nav that marks the current section with a selection box, plus a "Viewing —" label.
- Red scroll-progress bar.
- Scroll reveals.
- Hover selection boxes with a Figma-style cursor tag on project frames.
- Deep links such as `/#case-cradle`.

Everything works without JavaScript and respects `prefers-reduced-motion`.

## Files

```
index.html               page markup (semantic, one h1, h2 per section)
css/tl-portfolio.css     all styles; tokens at the top; Webflow breakpoints
js/tl-portfolio.js       ~7 KB vanilla JS, no dependencies
assets/img/              portrait + paper (from your PDF), grain, torn edges, handles, OG image
assets/fonts/            OFL fallback fonts + licences (Archivo, Space Grotesk, Gochi Hand)
webflow/                 optional head/footer custom code for a paid Webflow plan
WEBFLOW.md               how to build it in Webflow
```

## Fonts: what's real and what's a stand-in

| Brand font | Status | Shown now |
|---|---|---|
| Space Grotesk | Real font (Google Fonts, OFL), self-hosted | Space Grotesk |
| Akira Expanded | **Not bundled.** It's a commercial font and no file was supplied. | **Archivo, widest setting, weight 900**: closest free match, slightly lighter and narrower |
| Holidays Homework | **Not bundled.** No file was supplied. | **Gochi Hand** |

If either font is installed on a viewer's computer, the page uses it automatically. To ship it to everyone, add the licensed `.woff2` file to `assets/fonts/` and uncomment the `src: url(...)` line in the matching `@font-face` at the top of `css/tl-portfolio.css`.

## Adding your real project images

Each frame currently holds a clearly labelled **FPO ("for placement only") placeholder** with the size it expects. To swap one, replace the `<span class="tl-fpo">…</span>` inside the frame with an image:

```html
<a class="tl-frame is-16x9" href="#case-inform" data-tl-case="case-inform" tabindex="-1">
  <img src="assets/img/work/inform-hero.webp" width="2400" height="1350"
       loading="lazy" decoding="async"
       alt="Three Inform app screens in phone mockups: home, lesson and data-saver settings.">
  <span class="tl-frame-cursor"><span class="tl-frame-cursor-tag">Open case file</span></span>
</a>
```

- Keep the frame's ratio class (`is-16x9`, `is-4x5`, …) in step with the image.
- Remove `aria-hidden="true"` once the frame holds a real image.
- Write the alt text about what the image actually shows. The one above is an example only.

## Assets and info still needed

**Images** (WebP or JPG; sizes are the minimum for sharp display)

| Project | Gallery | Case file |
|---|---|---|
| Inform | Key app screens in phone mockups, 16:9, 2400×1350 | Process (research, flows, wireframes), 4:3 · UI detail, 4:3 |
| Cradle | Packaging mockup, 4:5, 1600×2000 | Logo/identity system, 4:3 · Label/typography detail, 4:3 |
| No Signal | Open spread, 3:2, 2400×1600 · Cover, 3:4 | Layout grid / process, 4:3 |
| Lebombo Growers | Packaging, 1:1, 1800×1800 · Identity before/after, 4:3 | Brand applications, 4:3 |
| Rocking the Daisies '27 | Campaign website homepage screenshot, 16:10 · Key visual/poster, 4:5 | Scrapbook elements and applications, 4:3 |
| The Fridge Habit | 3 × 4:5 (key visual, social post, poster) | Poster/outdoor, 3:4 |

**Text and links**
- **Contact email.** Currently `hello@example.com`, appearing twice in `index.html`.
- **Instagram / Behance / LinkedIn URLs.** Contact uses placeholders; the footer has a commented-out block ready to switch on.
- **The Fridge Habit.** One line on what the habit is and who the campaign speaks to.
- **Creative direction.** 2–3 sentences per project, inside each case file.
- **Rocking the Daisies live site URL**, once the Webflow site is published.
- **A logo**, if you want one. The brand guide's "Logo" page is empty, so the nav uses your name set in the display font.

**Fonts:** licensed Akira Expanded and Holidays Homework web-font files.

Everything I wrote about the projects comes from your brief or from your RTD Webflow site. No awards, clients, results or images were invented. The six skills descriptions describe disciplines, not claims. Motion design is left out because none of the listed projects shows it; add it when you have a project that does.

## Checked

- Chromium at 1920×1080, 1440×900, 1280×720, 1024×768, 834×1112, 768×1024, 390×844 and 360×740: no horizontal overflow, no console errors, no failed requests.
- Nav, index, skill-proof and back-to-top anchors all land correctly under the fixed nav.
- Case files: open from button or image, prev/next, Esc, backdrop click, focus returns to the button, deep link.
- Keyboard: skip link → nav → index → buttons. Visible red focus ring (black on red sections).
- No-JS: all content visible, case files open inline.
- Reduced motion: reveals shown immediately, smooth scroll off.
- axe-core 4.10 (WCAG 2.1 AA + best practice) at desktop, tablet and mobile: 0 violations. Contrast over textured backgrounds was checked by hand: small text is only black on paper or white/grey on black, and red is only behind large text.
- Page weight is about 360 KB before compression, fonts and images included.
