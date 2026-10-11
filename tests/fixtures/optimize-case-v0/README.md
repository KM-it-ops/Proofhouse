# Case schema v0 fixtures (0.4.1)

Written by the unmodified 0.4.1 code at commit 0c63d33, through
`proofhouse-compiler optimize ...`, before the case schema v1 change
(MISSION-040 T-040-01). Do not regenerate them with newer code: they stand
for cases that already exist on users' disks.

- `full/`: objective, compiled answers, four accepted constraints, seven
  criteria (prompt and output targets, one manual verdict), two revisions,
  two recorded outputs and one `check --all`.
- `fresh/`: a case straight after `optimize new`.
- `bundle-0.4.1.zip`: `optimize export` of `full/`.
- `golden.json`: what 0.4.1 reported for `full/` (check results per revision,
  the v1-to-v2 comparison and the v2 evidence report), with run ids and
  times replaced by `RUN` and `AT`.

The Markdown packets (`01-clarify.md` and so on) are left out; they are not
records and they embed machine paths. Files here are stored byte for byte
(`-text` in `.gitattributes`).
