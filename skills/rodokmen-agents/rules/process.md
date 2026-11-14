# Process information stays out of the web

## R-PROC-001

when: writing a fact, note, summary, description or public text
do: leave out who did the work ("helper N3e", "main agent", the model name), how it was verified ("checked on the image", "four eyes", "wave 3") and task numbers; keep the source, the confidence and the facts
why: these phrases ended up in texts that the family reads on the website
source: reference/zapisy.md#Co nepatří do dat ani na web

## R-PROC-002

when: you need to record how a result was obtained
do: put the process information only into the queues, the research log (field `proces`) and commit messages, never into `f`, `note`, `shrnuti` or `popis`; the scripts `denik.py` and `otazky.py` refuse such text
why: one place for the process keeps the public texts clean
source: fork

## R-PROC-003

when: a text shown on the website names a family line
do: write the plain name of the line; the build replaces it with the uniform badge, do not mark it up by hand; when a rule on appearance is needed in a methodology text, use an invented example name
why: one presentation of a family line on every page, and methodology that is portable between projects
source: fork
