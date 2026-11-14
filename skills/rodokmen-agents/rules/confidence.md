# Confidence of data (doc, prob, fam)

## R-CONF-001

when: recording any fact about a person in the data
do: use `doc` only for what was read directly on the image of a record that identifies the person unambiguously; `prob` for a strong match (name, period, place, house, trade) without a direct record, always with a `note` saying why; `fam` for what comes from the family; `mh` only for a foreign tree; `unk` when only the place in the tree is known
why: a plausible match recorded as `doc` becomes a false ancestor that later generations of research build on
source: reference/matriky.md#Stavy údajů v datech

## R-CONF-002

when: a helper agent or another tool has read a record and its reading is about to be recorded
do: verify the reading yourself on the image (crop of the record) before recording it as `doc`; "medium" confidence from a helper is not enough for `doc`
why: the helper is the same model without your context (two families of the same name in one village), so its reading is a second look only after you check it
source: SKILL.md#Pomocníci (subagenti) – šetrně

## R-CONF-003

when: reading German-language forms (for example Vienna) or any form where years, marital status, occupation, addresses or witnesses are filled in
do: verify years, status (single or widowed), occupation, addresses and witness names on the crop yourself before recording `doc`; leave an uncertain field out and describe the doubt in the note instead of writing a question mark
why: these are the fields that are most often missing or confused on German forms, and a question mark in the data looks like a reading
source: reference/matriky.md#Typické pasti (ze skutečného výzkumu)
