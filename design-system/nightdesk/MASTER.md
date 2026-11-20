# Nightdesk design direction (provisional)

Light only. A working desk: information must be clear to the operator. Provisional prep for the
hackathon; expect changes on the day. Shared by the Streamlit app and the Google Slides deck.

Derived from ui-ux-pro-max (Data-Dense Dashboard style, Logistics palette), adjusted by hand.

## Colours

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
| Verified (green) | to pick, >= 4.5:1 on white | verified only, nothing else |

Status never relies on colour alone: every badge carries an icon and a text label.
Text contrast 4.5:1 or better.

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

Dark mode, landing-page patterns (hero, call-to-action), GSAP animation, green as brand colour.
