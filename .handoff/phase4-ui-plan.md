# Nightdesk UI plan

Proposed workflow for Phase 4. Agree on the content and navigation before choosing the visual design.

## The operator’s job

Compare two captures, find a changed train, inspect the evidence, and record a local review. The operator should be able to say what changed, what the data supports, and who needs to follow up.

**Review queue → Train details → Record review → Export**

Returning to the queue should preserve the selected captures and filters.

## What goes on each screen

| Screen | Show first | Open when needed |
| --- | --- | --- |
| **Review queue** | Before and after capture labels and dates, coverage limits, and one row per train and service date. Each row shows what changed, what needs checking, review status, and the follow-up owner if assigned. | Change the comparison or evidence selection. Open a row to see its train details. |
| **Train details** | Train and service date, changed values side by side, and the most important unresolved question. Then show works, boundary, and running-time evidence. Keep local review and export in the same screen. | Choose the source leg when several exist. Inspect the source records or the previous review. View exact reason codes and revision IDs in the details. |
| **Evidence** | Browse works or train running times independently of the queue. Show the selected source, capture date, coverage, and licence. | Compare works captures, inspect provider-specific values, or open the reviewed European Sleeper comparison when available. |
| **Data and audit** | Capture selection and import, rejected records with reasons, and audit history. Keep the active workspace visible across screens. | Mapping, aliases, text intake, consent, and audit verification. Apply the existing public demo and practice bundle rules. |

## How to explain the evidence

- **Changes.** Show the field and both values when known. Distinguish an empty queue after a valid comparison from a comparison the data cannot support. For a record absent from a partial capture, show “Missing from this capture. Operating status unknown.”
- **Works.** Summarize the place, validity and the evidence for a match. Keep any unresolved time or location visible. Show unlocated works separately. For rolling-window changes, use wording like “Left the capture window” or “Entered the capture window” and keep the reason in the details.
- **Boundary.** “Boundary times differ” leads to the two values at the checked point. “Boundary could not be checked” gives the reason and any source selection needed. Scope any agreement to the point and fields checked.
- **Running times.** Use separate labels for “Scheduled”, “Published” and “Observed”. Explain where a published value is an estimate. For an archive reporting delays or cancellations, show those values as reported by the source. Keep the service date visible and show the date and time zone when needed to read an overnight or cross-border time.
- **Review.** Use “Needs clarification”, “Accepted locally” and “Rejected locally”. Collect a reason and offer an optional question with an owner. Show “Review needs updating” when a newer revision makes a previous decision stale. Export the selected evidence, coverage limits and review as Markdown and JSON.

## How it connects to the app

Use `queue()` and `dossier()` in `src/nightdesk/desk.py` for the primary flow. Use `works_evidence()` and `run_evidence()` for browsing, and the existing reviewed ES comparison for linked runs. Reuse the current review, audit and export paths. The presentation layer should translate field names, format dates and group existing evidence. Keep the existing rules for matching, completeness, source selection and review history with those services.

On the first screen, show the active workspace and comparison scope. Keep uncertainty at the evidence it applies to. Make provenance easy to open, with source, capture time, coverage reason and licence before raw fields and IDs.

## Walkthrough and acceptance

Use the synthetic train `aa:101` on 17 November 2026 in the first sketch. The exit time changes from 23:00 to 23:01 and the boundary times differ. A reader should be able to open the train, find both times, trace the source and record a question for a colleague without entering a revision ID. Evidence is in the v1 and v2 `legs.csv` fixtures and the checked workflow in `docs/DEMO.md`.

Check three more states in the sketches and the implemented UI. A partial capture explains why presence is uncertain. A stale review exposes the previous decision and the next action. The CC0 Infrabel example in `docs/DEMO.md` makes the scheduled and observed departures easy to tell apart.

## Build order

1. Agree on the screen content and navigation in this plan.
2. Complete P4.1 research and make low-fidelity queue and train-detail sketches. Walk through the scenarios above and agree on a visual direction.
3. Implement the approved queue and details in P4.2. Verify the same workflows with keyboard navigation, a narrow window, and the offline demo setup.
