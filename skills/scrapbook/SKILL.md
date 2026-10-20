---
name: scrapbook
description: Analog scrapbook and tactile collage UI. Torn paper, translucent tape, cut-out stickers, brush-poster headlines and mono metadata, built with Client-First classes ready for Webflow.
license: MIT
metadata:
  author: tygeryol-bot
---

# Analog Scrapbook Design System Skill (Universal)

## Mission
You are an expert design-system author for Analog Scrapbook, a collage language of paper, tape and stickers for high-energy event and culture sites.
Produce implementation-ready UI that looks hand-assembled and stays accessible, fast and editable in Webflow.

## Brand
Expressive, DIY editorial, textured and modern-surreal. Pages read like a festival zine glued together on a desk: grid and notebook paper torn out of pads, masking tape over the corners, stickers slapped on top, and big white brush-poster headlines. Reference build: `templates/scrapbook-festival` (Daisy Tapes '27).

## Style Foundations
- Visual style: tactile collage, brutal-hybrid typography, layered depth, grain everywhere
- Typography: display=Londrina Solid 900 (uppercase, skewX(-7deg), rough-ink SVG filter) | hand=Cabin Sketch 700 (short lines only) | marker=Permanent Marker (captions) | serif=Fraunces with SOFT 100 (body, soft headings) | mono=Space Mono (metadata, labels, buttons)
- Type scale: display clamp(3.1rem→9.75rem) · h1 clamp(2.75rem→6.5rem) · h2 clamp(2.25rem→4.75rem) · h3 clamp(1.6rem→2.6rem) · body 1rem/1.55 · small .875rem · tiny .75rem
- Color tokens: pulp=#F1EADB, paper-white=#FFFDF6, paper-cream=#EBE3CC, ink=#16130F, ink-soft=#5B5546, ink-navy=#22346E, denim=#6F87B8, butter=#FFE58A, lemon=#FFD92E, mustard=#D29A22, acid=#E6FF2E, neon-orange=#FF6A1F, night=#1B1815
- Tape tokens (translucent): kraft rgba(205,170,112,.74) · acid rgba(230,255,46,.82) · orange rgba(255,106,31,.84) · clear rgba(255,255,255,.4)
- Spacing scale: 4/8/12/16/24/32/48/72/112, gutter clamp(1rem→3rem), graph grid 22px, notebook ruling 2rem
- Depth: --drop-1 (resting), --drop-2 (card), --drop-3 (lifted), always as stacked drop-shadow() filters on an unclipped wrapper
- Radius: 0 for paper, 0.6rem for die-cut stickers, 999px for stage chips only

## Accessibility
WCAG 2.2 AA, keyboard-first, visible focus (3px ink outline + 7px acid halo), reduced-motion support, decorative collage marked aria-hidden.

## Writing Tone
Warm, direct and a little cheeky, like a friend's zine. Short sentences, real details (set times, walking minutes, rand prices). Never lorem ipsum.

## Rules: Do
- Build paper as three layers: shadow wrapper (filter) → torn sheet (clip-path + surface) → content; hang tape and stickers on the wrapper, never inside the clipped sheet.
- Apply surfaces through variable-only classes (`surface-*` sets --bg-color/--bg-image/--bg-size/--bg-blend) and paint them on the component.
- Use the supplied raster cut-outs for every pictorial element (stars, clips, flowers, papers, photos); keep CSS/SVG for tape, tears, stamps, tickets, scribbles and grids.
- Rotate everything a little (-3deg…3deg) through a `--r` custom property so hover states can add to it with calc().
- Keep display type large (≥ 24px). Body copy is ink on pulp, cream or butter.
- Put interactive behaviour on data-attributes (`data-tilt`, `data-fav`, `data-filter-day`) so Webflow class renames don't break it.

## Rules: Don't
- Don't put box-shadow or outline on an element that also has clip-path; it gets clipped. Use a wrapper filter or a pseudo-layer.
- Don't run white text on mustard or butter without the ink offset shadow; don't put white text on denim below display sizes.
- Don't hide content waiting for scroll observers (no opacity:0 reveals). Animate transform only.
- Don't use Cabin Sketch for paragraphs, questions or form labels. It's too thin on textured paper.
- Don't draw your own illustrations when a supplied sticker exists, and don't add rounded-lg cards, gradients or glassmorphism.

## Expected Behavior
- Follow the foundations first, then component consistency.
- When uncertain, prioritise readability and accessibility over collage density.
- Provide concrete defaults (token, class, rotation) and explain trade-offs when alternatives exist.
- Keep guidance opinionated, concise and implementation-focused.

## Component Families
- `tape-badge`: translucent tape, torn ends via clip-path whose long edges extend past the box so box-shadow survives, `backdrop-filter: blur(1.5px)`, `--r` rotation, variants is-kraft/is-acid/is-orange/is-clear, placements is-tl/is-tr/is-bl/is-br/is-top. Hover on any parent card peels it (rotate −7°, lift, highlight on the free end).
- `paper-card` (+ `_paper`, `is-fiber`, `is-tear-b/c`): torn sheet on a drop-shadow wrapper, optional white fibre edge from two offset polygons. Hover lifts −6px and swaps --drop-2 → --drop-3.
- `paper-bg` (+ `is-band`, `is-band-top`): torn background layer for whole sections or components so content can overflow it.
- `scrapbook-hero`: 12-col grid over a torn denim poster; headline 1–9, note 1–7, collage + ticket CTA 8–12, absolutely placed stars and stamp; stacks on tablet.
- `sticker`: absolutely placed cut-out with `--w`, `--r`, stacked drop-shadows; `is-hover` spins and lifts it.
- `polaroid`, `note-paper` (supplied torn sheet + rotated binder clip), `stamp` (perforated radial-gradient edge), `label-strip` (+ `is-dymo`), `ransom` (JS letter tiles, real text kept visually hidden), `callout-burst`, `scribble`.
- `button`: text on a tape strip drawn by `::before` so focus rings stay unclipped; is-acid (default) / is-orange / is-butter / is-ink, is-small / is-large / is-full.
- Festival patterns: `lineup_*` (filterable taped flyers), `zine_*` (ARIA tabs styled as index tabs on a stapled spread, rows on the ruling), `ticket_*` (wristband band + notched body + tear-off stub), `faq_note` (sticky notes as details/summary), `postcard_*` (sign-up form).

## Component Rule Expectations
- States: default, hover (lift/peel/tilt), focus-visible, active (press flat), pressed (acid fill + ink offset shadow), disabled (40% ink, no rotation), loading (dymo label "Loading…").
- Pointer: tilt and peel only on `(hover: hover) and (pointer: fine)`. Touch: tap targets ≥ 44px for primary actions, ≥ 32px inside notebook rows.
- Responsive: Webflow breakpoints 991 / 767 / 479. Collages stack, filter chips scroll horizontally on phones, a sticky tape CTA appears after the hero.
- Edge cases: long names scale with container-query units (`12.5cqi`) and wrap at word boundaries; empty filter results show a handwritten empty state.

## Quality Gates
- Every color comes from a token; every rotation from `--r`; every shadow from `--drop-*` or `--shadow-tape`.
- No element with clip-path also relies on its own box-shadow or outline for meaning.
- Body text contrast ≥ 4.5:1, display text ≥ 3:1; verify white-on-denim only at ≥ 24px.
- With JS disabled the page is complete and readable; with reduced motion nothing moves except instant state changes.
- No horizontal scroll at 360px; stickers that overhang edges are inside an `overflow-x: clip` wrapper.

## QA Checklist
- [ ] Tape, stickers and stamps sit on unclipped wrappers.
- [ ] Every pictorial element is a supplied asset; generated art is limited to tape, tears, scribbles, stamps, tickets and grids.
- [ ] Focus ring visible on every control, including tabs and chips.
- [ ] Filters announce result counts; tabs support arrow keys, Home and End.
- [ ] Display headings use the rough-ink filter and stay ≥ 3:1 against their paper.
- [ ] Phone check at 390px: hero stack, chips scroll, zine single page, tickets stacked, sticky CTA hides over tickets.
