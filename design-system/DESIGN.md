# Presentation design: European Sleeper look

For the hackathon deck (Google Slides) and anything printed or shown around it. Not for the desk
app: the desk keeps its own light, operator-first look, described in
`design-system/nightdesk/MASTER.md`.

**Source and status.** Read from the public website (europeansleeper.eu: homepage markup and main
stylesheet) on 2026-11-20. It is not an official brand guide. Replace anything here with ES's real
guidelines or template if the organiser or their team supplies one. Check before use that ES is
happy for us to wear their look; the IP of what we build goes to them, so it should be fine.

## The feel

Warm, friendly, a little playful: "The Good Night Train", "A unique way to travel through Europe
while you sleep". Deep plum as the anchor, soft pastel bands, rounded shapes, one hot orange for
the single thing you want people to act on. Not corporate-blue, not techy-dark.

For us: the story is operational ("same train, three countries, three files"), so keep the warmth
but let the evidence carry the slides.

## Colours

Names are the site's own class names where they exist (`dark-aubergine`, `lavender`, `light-blue`).

| Name | Hex | Use on slides |
| --- | --- | --- |
| Dark aubergine | `#40002c` | Text, title bands, title slide background. The anchor colour. |
| Lavender | `#cdc4e1` | Section bands, cards, selected states |
| Light blue | `#a6c1dd` | Second band colour, charts, route lines |
| Muted purple | `#866286` | Secondary text, captions, dividers |
| Yellow | `#fdd663` | Highlight: one number or one word per slide |
| Orange-red | `#ff3600` | The call-to-action colour. Use once per slide, at most. |
| Off-white | `#f5f7fb` | Slide background (white `#ffffff` also works) |

The site also uses `#ff3b30` and `#f23705` near the orange-red; treat them as the same colour.

**Proportions.** Mostly off-white or white with aubergine text. Pastel bands (lavender, light
blue) for sections. Orange-red and yellow are seasoning, not fills.

**Contrast** (computed from the hex values):
- Aubergine on white: about 16.7:1. Aubergine on lavender: about 10:1. Both fine for any size.
- White on orange-red: about 3.6:1. Passes only for large text (bold 24pt+). Never put small text
  on orange-red. On a projector, prefer aubergine text on yellow or lavender instead.

**Status colours in our own data visuals** (the desk's meaning, kept in slides so the story
matches): changed = orange `#EA580C`, rejected = red `#DC2626`, verified = a green to be picked.
Do not use the brand orange-red `#ff3600` for "rejected": it is too close to red.

## Type

- ES uses **GT Ultra** (sans) for headings and body and **Ambit** (serif) as a second face. Both
  are commercial fonts; we do not have licences, so do not use them.
- **Stand-ins in Google Slides:** pick a clean humanist sans for headings and body (Source Sans 3
  to match the desk) and a monospace for train numbers, times and hashes (Source Code Pro). Check
  both appear in the Slides font picker before building; if not, use the nearest ones it offers.
- Headings large and short, sentence case. Body no smaller than 18pt on slides.
- Numbers that identify things (train 452, 23:00, a hash) in the monospace.

## Shape language

From the site's styles:
- **Rounded corners.** Cards and buttons use about 0.75 to 1 rem radius (12 to 16px). Pill shapes
  for tags.
- **Curved band edges.** Coloured section bands end in a rounded bottom edge (the site's
  "radius-bottom" pattern). On a slide: a lavender or light-blue band across the top with a
  rounded lower edge.
- **Flat "pressed" buttons.** A solid colour with a hard offset shadow below (`0 4px 0` in
  aubergine), no blur. On a slide: a solid block with a plain offset underneath instead of a soft
  drop shadow.
- No gradients, no glow, no blurred shadows.

## Slide patterns

1. **Title.** Aubergine background, off-white title, a lavender band with a curved edge, the
   route-map image from `docs/img/route-map.png`.
2. **The problem in one picture.** Train 452, three countries, three files. Use the explainer's
   story (`docs/explainer-train-452.html`). One idea, one image.
3. **Desk screenshot.** On an off-white slide with a rounded frame and one yellow highlight on the
   changed time (23:00 to 23:01). Annotate with a single orange-red label at most.
4. **Evidence and trust.** Source, licence, capture time on every row; the audit check. Aimed at
   the cyber security prize.
5. **CO2.** The CO2 comparison, aimed at the sustainability prize.
6. **Coverage, honestly.** Which of the six networks we cover (BE, NL, DE, CH) and which we do not
   (CZ, FR).
7. **Who pays and why.** Business model slide.
8. **Close.** Aubergine background, one line, one orange-red call-to-action.

One idea per slide. Screenshots and the route map do the talking; text is a caption.

## Practicalities for Google Slides

- Set the theme colours once (Slide, Edit theme, Colors) to the seven values above so the picker
  offers them everywhere.
- Set theme fonts once, the same way.
- Keep images local to the deck (insert, do not link) so it works without network on the day.
- Export a PDF as the fallback copy.

## Not used

Dark backgrounds for content slides, the desk's green and cream, gradients, GT Ultra and Ambit
(not licensed), ES logos and photography (not ours to use until ES's team shares assets).
