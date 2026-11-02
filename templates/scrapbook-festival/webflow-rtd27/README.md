# Rocking the Daisies 2027 · Memories That Stick: Webflow v2 sections

These are the files pasted into the Webflow page (site `6ace5c0da0bb66017f9854b5`) to apply the decisions from the process document. The existing scrapbook design stays as it is.

| File | Where it went in Webflow |
| --- | --- |
| `sections/hero_shortcuts.*` | After the hero collage: Get tickets / Stay / Line-up / Map / Plan |
| `sections/lineup_*` | Line-up: "Who's coming home with you.", stage key, Friday / Saturday / Sunday blocks (RTD 2025 artists) |
| `sections/zine.html` | The full schedule (map tab removed) |
| `sections/tickets.*` | Keepsake + Golden Hour wristbands and the Early Bird / Regular / Final Release strip |
| `sections/stay.*` | Your Own Patch, Slow Mornings, The Polaroid, The Contact Sheet |
| `sections/build.*` | Build Your Weekend: pass, people, sleeping, extras, receipt total, Computicket hand-off |
| `sections/festmap.*` | Map placeholder frame (drop the illustrated map into `.festmap_slot`) |
| `sections/plan.*` | Plan your trip: Getting there, What to bring, Camping + rules, Accessibility |
| `embed-styles.html` | Style-only HTML embed (states, torn edges, sticker sizes) |
| `embed-script.html` | Script embed (filters, picks, builder logic, mobile CTA) |
| `content.py` | Line-up, prices and FAQ copy in one place |
| `components.css` | Source CSS for the new components |

## Things to confirm before launch

- **Weekdays:** 2–4 October 2027 is a Saturday to Monday, but the document uses Friday / Saturday / Sunday. The site shows day names without dates in the line-up and the dates without day names elsewhere.
- **Placeholder prices:** Slow Mornings (R890 pp) and The Contact Sheet (R14,400 per tent) are not given in the document.
- **Line-up:** the artists played Rocking the Daisies 2025, the last edition that went ahead (2026 was cancelled). The days, stages and set times for 2027 are proposals.
- **Links:** "Continue to Computicket" goes to the Computicket home page. The footer "Contact" link goes to the sign-up postcard until there is a real contact address.
