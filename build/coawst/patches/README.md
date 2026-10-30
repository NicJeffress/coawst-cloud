# COAWST patches

`series` lists the patches in the order they are applied. They are grouped in
three folders by how well established they are:

| Folder | Kind | What its test must show |
|---|---|---|
| `1-fixes/` | COAWST did something wrong | fails without the patch, passes with it |
| `2-improvements/` | no change to the physics, or a new capability | results unchanged (bit-identical or rounding level) |
| `3-experimental/` | off unless a cpp option switches it on | build unchanged with the option off; what has and has not been checked |

Several patches edit the same files, so they only apply in this order. An
experimental patch moves to the improvements after an accuracy test against a
converged reference.

Each patch is documented here with a status card:

| Field | Meaning |
|---|---|
| Type | fix, improvement or experimental |
| Changes results? | no (crash, output or run-control fix only), output (values written change, the computation does not), yes (the computed solution changes, in the cases named), speed, new (a capability COAWST did not have) |
| Default | on, or the cpp option that switches it on |
| Evidence | the test case and the numbers |
| Test | the script that checks it |
| Upstream | reported or proposed to COAWST? |

(No patches yet: the series is empty and the build is COAWST as shipped.)
