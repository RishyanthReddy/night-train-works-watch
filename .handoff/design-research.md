# Nightdesk design research

P4.1 proposal for the review queue and train details. The [interactive prototype](phase4-ui-prototype.html) uses synthetic examples.

## Public references

| Reference opened | Pattern to use in Nightdesk |
| --- | --- |
| [National Rail disruptions](https://www.nationalrail.co.uk/disruptions/) | Lead with a plain-language headline and keep the affected service and update time nearby. Use capture times rather than implying that the Nightdesk list is live. |
| [TfL service status](https://tfl.gov.uk/tube-dlr-overground/status/?cid=status-updates) | Put the affected section next to the short finding. Keep a boundary result specific to the selected point and date. |
| [HSE control-room design](https://www.hse.gov.uk/comah/sragtech/techmeascontrol.htm) | Pair a status with its meaning and show feedback after an action. Give the operator words for each state even when a badge has an accent colour. |
| [GOV.UK task list](https://design-system.service.gov.uk/components/task-list/) | Keep a visible status and open action on each train/date row. Show review status separately from evidence coverage. |
| [GitHub change review](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/reviewing-proposed-changes-in-a-pull-request) | Put labelled values side by side and keep saving a decision a separate action. Flag a prior review when the selected revision changes. |
| [GOV.UK summary list](https://design-system.service.gov.uk/components/summary-list/) | Show source, capture time, coverage and licence as short label/value pairs. Keep exact source evidence one action away. |
| [GitHub audit log](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/reviewing-the-audit-log-for-your-organization) | Lead an event with actor, action, affected record and time. Put exact event details and verification in Data and audit. |
| [Streamlit dataframe](https://docs.streamlit.io/develop/api-reference/data/st.dataframe) | Use display fields only in tables. Open a train through an explicit labelled control and resolve any selected row to a stable train/date. |
| [Streamlit columns](https://docs.streamlit.io/develop/api-reference/layout/st.columns) | Use one Before/After pair that wraps in reading order. Keep review and uncertainty in the main document flow. |
| [Streamlit theming](https://docs.streamlit.io/develop/concepts/configuration/theming) | Use native controls and offline type. The usual project-wide theme configuration lives outside the Phase 4 allowlist. Keep styling scoped to the UI. |

Direct Firecrawl checks returned the National Rail and GOV.UK pages. Three parallel research agents covered rail/incident decisions, queues and traceability, and Streamlit feasibility. The team opened the official pages linked above and checked Streamlit against the pinned 1.67.0 version.

## Proposed direction

- **Queue.** Show the workspace, selected comparison and any coverage limitation above the list. Give each train/date a short change summary, an evidence finding, a review label and one “Open train” action. Show an assigned owner by name. Use a separate state when a comparison is unavailable.
- **Train details.** Lead with the train, date and changed field. Show before and after values with visible headings. Then put the boundary or works finding and its scope above the local decision form. Label source evidence and the earliest useful next action. Preserve queue context and keyboard focus on return.
- **Visual style.** A restrained navy header, white reading surfaces, dark slate text, teal primary actions, and neutral status labels. Use amber with words for incomplete evidence and reviews that need attention. Proposed desktop sizes are 34 px for page headings, 20 px for section headings, 16 px for reading text and 14 px for secondary labels. Use system fonts, tabular time values and visible focus.
- **Tools outside the main flow.** Put provider imports and audit in their own area. Keep independent works and run inspection discoverable. Use the existing scheduled/published/observed distinction for running times. Archived reports retain their original delay and cancellation wording.

The screen leads with the reason and evidence for a finding. Its scope is local review. Avoid live signalling and dispatch controls, inferred cancellations, and colour-only status cues.

## Streamlit implementation limits

The browser prototype describes content and behaviour. Native Streamlit controls and layout will determine the final rendering. The dataframe grid owns its typography, keyboard behaviour and cell layout, so it is appropriate for longer evidence lists. Use explicit selection and a stable record key for the primary review path. Native columns can stack at narrow widths. Reruns require explicit state for the active comparison, selected train and saved review. Plan to verify focus order, returning to the same train, and narrow-window wrapping on the actual app. Keep raw provenance and diagnostic codes expandable without hiding uncertainty.

## Review tasks

1. Open the synthetic train, find 23:00 and 23:01, explain the boundary discrepancy and locate the two source records.
2. Select the partial capture. Explain which fact is missing and what remains unknown.
3. Select the newer revision. Find the stale review, save a reason and a follow-up, download the draft, and confirm that the queue shows the new disposition.
4. Repeat the primary actions using only the keyboard and at a narrow width. For the later Streamlit acceptance, also check the CC0 Infrabel scheduled and observed clocks, plus the public-demo workspace lock.

The prototype exercises three synthetic comparison states on one train. Capture clock labels are illustrative. The full and revised scenarios use the AA and BB timetable values and file rows from the v1–v3 synthetic fixtures. Drafts live in the page session and download as plain text. The existing app supplies multi-train navigation, running-time evidence, persistent local reviews and Markdown/JSON exports in P4.2 acceptance.

## Revised visual direction

The [new prototype](phase4-modern-review.html) applies the user’s feedback on the dated first design. The queue stays next to the selected train on wide screens. The changed time is the focal point, followed by a two-point boundary comparison. Sources and local review are accessible from the same record. A small-screen selector switches between the same cases.

| Reference opened | What the redesign uses |
| --- | --- |
| [Plain Issues List on SaaSFrame](https://www.saasframe.io/examples/plain-issues-list) | The viewed screenshot separates navigation from a short, easy-to-scan queue. Nightdesk adapts that hierarchy to put the change first, with the train and review state directly below. |
| [Linear’s redesign](https://linear.app/changelog/2024-03-20-new-linear-ui) and [inbox screenshot on Changelog Gallery](https://www.changelog.gallery/posts/welcome-to-the-new-linear/) | The viewed screenshot keeps the selected item and its terse queue beside the details. Nightdesk gives the changed values the larger share of the screen. |
| [Linear Split Inbox](https://linear.app/changelog/2021-12-02-workspace-templates) | Keep the queue visible when acting on an item, so a review does not reset the selection. |

Mobbin’s public web catalogue did not expose usable screens through the web reader. The Google Search page returned no usable results in the fetched HTML. Public web and image search located the examples above, whose published screenshots were downloaded and visually inspected. The mockup uses an original warm off-white and green palette, a rail mark drawn in CSS, tabular time typography and amber text treatments for uncertain evidence. No reference assets are included.

Run evidence shows the CC0 Infrabel example at Hergenrath. The selected stop’s CSV line gives European Sleeper 400 on 1 Oct 2026, 09:05:00 scheduled and 09:59:40 observed. This view has its own source and scope and is separate from the synthetic change examples. Like the first prototype, the new design is standalone and keeps drafts in the page session.
