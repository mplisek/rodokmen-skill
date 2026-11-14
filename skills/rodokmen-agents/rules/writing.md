# Writing data and web texts

## R-WRITE-001

when: writing to the data files
do: write through the scripts (`zapis.py` for `zaznamy`, `svazky`, `prepisy`, `dokumenty`; `denik.py` for the research log; `otazky.py` for public questions); never edit the data files with `sed -i`, ad-hoc scripts or manual redirection
why: manual edits damage the file format (escapes) and leave the data half changed when a step fails
source: fork

## R-WRITE-002

when: about to change the data in a bigger step
do: make sure the data is backed up in git and propose a commit after the step
why: a damaged data file must be recoverable
source: SKILL.md#Co nikdy

## R-WRITE-003

when: writing any text that goes to the web (facts, notes, summaries, public questions, log rows)
do: write only the source (book, signature, image, page), the confidence and the facts; about living people only name and year of birth; no process information
why: the family reads these texts and living people must not appear in detail
source: reference/zapisy.md#Co nepatří do dat ani na web
