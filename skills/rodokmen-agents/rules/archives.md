# Respect for archives

## R-ARCH-001

when: any network request to an archive or another throttled site
do: go through the throttle (`tools/slusne.py`) in every form: own scripts, `curl`, shell scripts; when it says the site is stopped, do not retry, do not work around it with another tool or the browser, tell the user and do other work
why: archives block the IP address after a series of quick requests, sometimes for hours
source: SKILL.md#Šetrně k archivům – brzda `tools/slusne.py`

## R-ARCH-002

when: reading in a browser on a portal that does not allow scripts (for example MZA, SOA Třeboň, SOA Praha, ZA Opava)
do: read at a human pace (at least 5 seconds between pages for targeted searches, 10 seconds when paging); one browser per archive, no helpers, no parallel requests or loops over whole volumes; on 403, 429 or 503 stop at once, record the stop in the throttle and continue another day
why: the throttle does not apply in the browser, so the discipline is yours, and archives can block even the browser
source: SKILL.md#Šetrně k archivům – brzda `tools/slusne.py`

## R-ARCH-003

when: a request would download in bulk from a paid service, solve a CAPTCHA, enter credentials or payment details, or bypass a protection
do: do not do it; read only what the user opens or what you need one item at a time, and ask the user for the rest
why: bulk access leads to the blocking of the account and the credentials and the CAPTCHA are the user's alone
source: SKILL.md#Co nikdy
