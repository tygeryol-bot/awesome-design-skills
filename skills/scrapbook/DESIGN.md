---
name: Scrapbook
colors:
  primary: "#16130F"
  secondary: "#6F87B8"
  accent: "#E6FF2E"
  accent-alt: "#FF6A1F"
  warning: "#D29A22"
  surface: "#F1EADB"
  text: "#16130F"
  neutral: "#FFFDF6"
typography:
  display:
    fontFamily: "Londrina Solid"
    fontSize: 9.75rem
  h1:
    fontFamily: "Londrina Solid"
    fontSize: 6.5rem
  hand:
    fontFamily: "Cabin Sketch"
    fontSize: 2.6rem
  body-md:
    fontFamily: "Fraunces"
    fontSize: 1rem
  label-caps:
    fontFamily: "Space Mono"
    fontSize: 0.75rem
  sourceScale: "12/14/16/18/26/42/76/104/156"
  weights: "400, 700, 800, 900"
rounded:
  paper: 0px
  sticker: 9.6px
  chip: 999px
spacing:
  sm: 8px
  md: 16px
  lg: 32px
  sourceScale: "4/8/12/16/24/32/48/72/112"
---

## Overview

Analog Scrapbook turns a web page into a desk covered in paper. Graph and notebook sheets are torn from their pads with a white fibre edge along the tear. Masking tape in kraft, acid yellow and neon orange holds them down, die-cut stickers sit on top, and white brush-poster headlines run across crumpled denim and mustard stock. It was built for a music-festival site (`templates/scrapbook-festival`) from two supplied asset sheets, a crumpled-paper texture and four campaign posters.

## Style Foundations

- **Visual style:** tactile collage, DIY editorial, brutal-hybrid type, layered depth
- **Typography:** Londrina Solid 900 for posters, Cabin Sketch for handwritten display lines, Permanent Marker for captions, Fraunces (SOFT 100) for reading, Space Mono for metadata
- **Texture:** grain (inline SVG noise) on every surface; the supplied crumple texture mirror-tiled and multiplied into each paper colour
- **Depth:** stacked `drop-shadow()` filters in three steps (resting, card, lifted)
- **Rotation:** everything sits between −3° and 3° via `--r`; hover adds to it

## Colors

- **Pulp (#F1EADB):** the desk and default page.
- **Paper white (#FFFDF6):** fresh sheets, the white core along every tear, sticker borders.
- **Carbon ink (#16130F):** all body text and print. 15:1 on pulp.
- **Denim (#6F87B8):** poster blue for the hero and schedule band. White display type only (3.5:1).
- **Mustard / butter / lemon (#D29A22 / #FFE58A / #FFD92E):** the yellows of the sticker sheet. Mustard carries white headlines with an ink offset shadow.
- **Acid (#E6FF2E) and neon orange (#FF6A1F):** fluorescent tape, active filters, highlighter swipes. Ink text on both (16.5:1 and 6.5:1).
- **Ink navy (#22346E):** binder-clip navy for soft serif headings and handwriting.
- **Night (#1B1815):** black construction paper for tickets and the footer.

## Typography

Headlines are uppercase Londrina Solid at 0.84 line-height, skewed −7° and run through an `feDisplacementMap` filter (`#rough-ink`) so the edges look dry-brushed. Ransom-note headings mix eight tile styles, keep the real text in a visually hidden span and mark the tiles `aria-hidden`. Long reading stays in Fraunces at 1rem/1.55; metadata, prices' small print and buttons use Space Mono in uppercase with 0.08–0.16em tracking.

## Components

- **Tape badge:** translucent strip with torn ends, backdrop blur, a shadow that survives its clip-path, and a peel on hover.
- **Paper card / paper bg:** a shadow wrapper, a torn sheet (optionally with a white fibre edge) and content. The bg version lets content overflow the paper.
- **Scrapbook hero:** a 12-column collage on a torn denim poster, with the headline, notebook note with binder clip, polaroid, stickers, perforated stamp and ticket-stub CTA.
- **Line-up flyers:** taped posters on graph paper, filterable by day and stage, with a halftone xerox hover and favourites.
- **Schedule zine:** index tabs over a stapled two-page spread whose rows sit on the notebook ruling, plus a sticker map.
- **Wristband tickets:** woven band with clasp, notched body, dashed perforation and a stub that tears off.
- **Sticky-note FAQ, postcard sign-up, label strips, dymo labels, stamps, starburst callouts, scribbles.**

## Motion

Paper motion overshoots (`cubic-bezier(.34,1.56,.64,1)`) like something being slapped down. Hover states are CSS (peel, lift, tilt via custom properties). Scroll reveals animate transform only, so nothing is ever hidden at rest. `prefers-reduced-motion` stops the marquee, jitter, tilt and reveals.

## Rationale and references

- The four campaign posters set the vocabulary: dusty-blue grid poster with a torn white edge, mustard grid collage with a dictionary clipping and polaroid, binder-page spreads with ransom letters and stickers, Y2K sticker sheets on black.
- Supplied cut-outs are used for every pictorial element. CSS and SVG only draw what stretches with content: tape, tears, stamps, tickets, grids and scribbles.
- Client-First naming keeps the system portable to Webflow and Relume. Surfaces are variable-only classes so the same class paints a block or a torn pseudo-layer.

## Maintenance notes

- Add a paper colour by adding one `surface-*` class (four variables). Never hard-code a background on a component.
- New torn shapes: generate a polygon with px-based tear depth (`calc(100% - Npx)`) so tears stay crisp at any size; keep tape polygons extending past the box.
- When swapping in photos, put them in the existing image slots (`polaroid_photo`, `lineup_art`) rather than adding new frame styles.
