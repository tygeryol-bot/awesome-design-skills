# RTD27 – where things stand (9 Nov 2026)

**Live (webflow.io only):** https://rockingthedasies27mts.webflow.io
**Designer:** https://rockingthedasies27mts.design.webflow.com/ (Tyger Lee's Workspace, site `6ae9b5983a11fb874e346b43`, home page `6ae9b5993a11fb874e346b46`)

Webflow holds the real site. This folder is a backup of the code and section markup used to build it.

## Done
- Full rebuild in the new workspace, white stamp logo (header, menu, hero note, postcard, footer), grain toned down.
- Hero: night stage photo in the polaroid ("main stage, after dark"), "click the poster" hint removed, bigger date, wristband ticket stacked and left-aligned.
- Yellow section: "everything is hard" note replaced by taped daytime stage polaroid.
- All headings Londrina Solid; line-up title is a plain heading.
- Tickets: price on one line, "per person" underneath; Golden Hour on plain crumpled blue paper; both cards straight, equal height, buttons and stubs level.
- Banners: continuous scroll (CSS) + Webflow scroll interaction "Marquee banners scroll"; text doubled so no gaps on wide screens.
- FAQ: black heading, no squiggle, click-to-open answers via Webflow interactions "FAQ 1–6 toggle" (answers use class `faq_answer` + combo `is-open`).
- Clips and postmark moved clear of text.
- Interactive map: the labels under the map (Stages, Camping, Entrances, Parking + transport, Toilets/water, First aid + info, Food + drink) drop pins on the map; "Accessible routes" and "Walking times" labels removed. Pin positions live in `embed-4-map.html` (SPOTS, % of map width/height).
- Festival map in the map section (`rtd-festival-map.webp`), tap/click opens it full size; "Tap the map" note on phones.
- Neon green → lemon yellow `#ffd92e` (Webflow variable `acid` + `embed-3-yellow.html`).

## Embeds on the page (in order)
1. `embed-1-base.html` – fonts, tokens, base styles
2. `embed-2-components.html` – component states, keyframes, stamp, photo
3. `embed-3-yellow.html` – yellow overrides, plain blue ticket, banner reduced-motion
4. `embed-4-map.html` – interactive map pins (style + script)
5. `embed-script.html` – stars/picks, schedule tabs, filters, builder, mobile CTA (runs only on the published site, not in Designer/Preview)

## Gotcha
Webflow's publish step compresses `rgba(...)0 1px` into an invalid colour like `#ffffff1a0`, which drops the whole background. Always put a space after `)` in gradient colour stops (fixed on marquee_tape, ticket_band, tape-badge).

## To check next
- Verified live (12 Nov): stars save and sync, picks-only filter, saves survive reload, day tabs, FAQ toggles, banners scroll (also with Reduce Motion), tape colours show.
- Still to confirm with the client: Fri–Sun vs 2–4 Oct 2027 (Sat–Mon), placeholder prices (Slow Mornings R890, Contact Sheet R14,400), proposed set times, Computicket + Contact links.
- Duplicate site "rockingthedasies27mts-f5c880" can be deleted.
