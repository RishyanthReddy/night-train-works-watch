# Nightdesk design direction (provisional)

Light only. A working desk: information must be clear to the operator. Provisional prep for the
hackathon; expect changes on the day. Shared by the Streamlit app and the Google Slides deck.

Derived from ui-ux-pro-max (Data-Dense Dashboard style, Logistics palette), adjusted by hand.

## Colours

### What the desk uses today

The shipped desk (`src/nightdesk/ui/review_desk.py`) is a green-and-cream proof sheet. These are
the values in the code, not a proposal:

| Role | Hex | Where |
| --- | --- | --- |
| Ink | `#202c25` | body text (13:1 on the panel surface) |
| Quiet text | `#4f6055` | labels, sources (6.0:1 on the panel surface) |
| Green | `#235b3e` | brand mark, selected tab, the later ("after") time |
| Surface | `#f2f4ee` | brand strip, queue panel |
| Times panel | `#f5f8ee` to `#edf4e7` | the app's one gradient |
| Border | `#dce1d8`, `#d7e3d0` | panel and times-panel edges |

Colour marks one thing today: the later value, in green. Everything else is a word. Change
`review_desk.py` first and this table after, never the reverse.

### Proposal, not yet applied

Kept as an option; none of it is in the app yet:

| Role | Hex | Use |
| --- | --- | --- |
| Background | `#F8FAFC` | page |
| Card | `#FFFFFF` | panels, tables |
| Border | `#BFDBFE` | dividers |
| Text | `#0F172A` | body |
| Muted text | `#475569` | labels, sources |
| Primary blue | `#2563EB` | headings, links, selected row |
| Changed (orange) | `#EA580C` | something changed |
| Rejected (red) | `#DC2626` | rejected / error |
| Verified (green) | `#235b3e` (already in the app, 7.2:1 on the panel surface) | verified only, nothing else |

Status never relies on colour alone: every badge carries an icon and a text label.
Text contrast 4.5:1 or better. Green already marks the later time, so "verified" needs its own
mark (icon or label) as well as the colour.

## Type

- Body and headings: Source Sans (Streamlit built-in, works offline)
- Train numbers, times, hashes: Source Code Pro (Streamlit built-in)
- Optional later: Fira Code / Fira Sans, but needs a Google Fonts link (internet) or self-hosted files.
  Slides can use Source Sans 3 and Source Code Pro, both in Google Slides' font list.

## Layout

- Dense: 8-12px gaps, 12-14px table text, sticky table headers, tables scroll rather than wrap.
- Motion minimal; respect reduced motion.
- Evidence rule is part of the design: source, licence and capture time visible on every row.

## Not used

Dark mode, landing-page patterns (hero, call-to-action), GSAP animation, blue as brand colour.
