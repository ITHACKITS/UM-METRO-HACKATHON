# Task-based user validation

## Goal

Test whether intended users can complete the workflow and understand its limits,
not whether they like the colors or agree with the team. Aim for one PPL/agronomist
and approximately five farmers or representative users. Report the actual number.

## Consent and setup

Explain that participation is voluntary, the prototype is experimental, and no
care/agronomic decision should rely on it alone. Obtain consent for notes/video
separately. Use participant codes; keep names/contact details and signed forms
off-Git. Do not show participants the desired answer.

Use a real phone and representative consented/licensed photos. Counterbalance the
starting mode when practical. The facilitator reads the same neutral prompts and
does not coach unless the participant has stopped; record every hint.

## Four core tasks

1. **Choose a mode.** “You see symptoms on a leaf” or “you can see an insect on the
   plant.” Ask the participant to start the appropriate check.
2. **Capture/select a usable photo.** Observe whether the instructions lead to the
   correct distance, framing, focus, and mode-specific subject.
3. **Interpret a result.** Ask: “What does this result tell you, and what does it not
   tell you?” A correct explanation mentions an indication/model, uncertainty, and
   that it is not a diagnosis or safety guarantee.
4. **Choose a safe next action.** The participant should identify retaking/inspecting
   or contacting a PPL/agronomy expert—not an autonomous pesticide action.

Include at least one `retake`, one `abstain`, one disease candidate result, and one
pest result or clear no-detection limitation across the sessions.

## Observation form (one row per task, stored privately)

| Field | Allowed value/example |
| --- | --- |
| participant code | non-identifying code |
| role familiarity | farmer / PPL / representative; coarse experience band |
| task/version | stable task ID and UI commit |
| completed | yes / with hint / no |
| time seconds | measured, not estimated |
| retakes | count |
| interpretation | correct / partial / unsafe, with verbatim short note |
| hints | count and neutral hint text |
| issue code | navigation / capture / language / model-boundary / next-action |
| qualitative note | non-identifying observation |

Do not record sensitive farm economics, precise location, phone number, or medical/
personal details.

## Aggregate report

Report participant count and role mix, completion per task, median/range time,
retake rate, hint rate, interpretation errors, unsafe-action selections, and major
themes. With very small samples, show counts and avoid percentages that imply
population precision. Include the UI/model version and dates.

Suggested release criteria:

- every participant can distinguish disease versus visible-pest mode after no more
  than one neutral hint;
- no participant leaves believing the result is a definitive diagnosis or that no
  pest detection means safe;
- every participant can find the PPL/retake next action;
- critical wording problems are corrected and retested.

These are product-comprehension gates, not scientific accuracy metrics.

## Expert review

Separately ask the PPL/agronomist to review every Indonesian class/common name,
capture instruction, limitation, and next-action sentence using
`TERMINOLOGY_REVIEW.md`. Record version/date/role and unresolved items. A general
“looks good” is insufficient.

