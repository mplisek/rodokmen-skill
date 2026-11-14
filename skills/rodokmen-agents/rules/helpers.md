# Working with helper agents

## R-HELP-001

when: a helper agent finds and reads records
do: let it write only to `pracovni/pom_<branch>/` and never to `data/`; the main session writes the data; keep the helper outputs until their content is extracted
why: a helper has no context and no right to decide what becomes a fact
source: SKILL.md#Pomocníci (subagenti) – šetrně

## R-HELP-002

when: writing the brief for a helper
do: give the volume, the images, whom to look for, the result format (key, image, coordinates of the record, transcription), the technical pitfalls and the throttle rules (network only through the throttle, stop and report when it says stopped); ask it to state for every image what it actually read (year, first name) and to mention clearly related occurrences; never ask it to write a transcription of a record it did not see
why: a helper that did not see an image "reads" blind and the invented transcription looks real
source: SKILL.md#Pomocníci (subagenti) – šetrně

## R-HELP-003

when: a helper reports new persons
do: have it mark them with temporary links (`nova1`, `nova2`) with father, mother, husband, not with guessed person numbers; assign the numbers and the place in the data yourself when you write
why: guessed numbers collide with the numbering of the data
source: SKILL.md#Pomocníci (subagenti) – šetrně

## R-HELP-004

when: choosing what to give to helpers
do: do not send them to badly legible books (Kurrent of the first half of the 19th century, faded images) unless you give the exact image; keep to one browser helper at a time and prefer tools without a browser; have them read at 100 percent, not from an overview scaled to a third; for the reading of an index use the column mode
why: overview scaling and shared browser tabs produced wrong readings and lost searches
source: SKILL.md#Pomocníci (subagenti) – šetrně

## R-HELP-005

when: planning a big round of helpers
do: tell the user what you plan and why and get approval first; run the helpers on the cheaper model for search and first reading, and keep the verification on the image and the writing for yourself
why: a round costs many credits and the user should know why
source: SKILL.md#Pomocníci (subagenti) – šetrně
