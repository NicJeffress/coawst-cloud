# Tests

## Checks on the patch series

| Script | What it checks |
|---|---|
| `same_source/compare_series.sh SOURCE SERIES_A DIR_A SERIES_B DIR_B` | Two patch series give the same COAWST source, file by file. Run it whenever the series is reordered, split or regenerated. |

Example: before a reorganisation, save the old series and its patches, then

```bash
tests/same_source/compare_series.sh COAWST-<ref>.tar.gz \
    old/series old/ build/coawst/patches/series build/coawst/patches/
```

prints `IDENTICAL: <n> files` or the files that differ.

The tests behind each patch (fixes, improvements, experimental options) are
added together with the patches.
