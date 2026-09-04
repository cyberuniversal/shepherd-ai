# Anonymous NeurIPS 2026 Manuscript

This directory is a self-contained anonymous NeurIPS 2026 main-track format
package. It preserves the frozen study claims and results from `paper/main.tex`
while removing authors, affiliations, acknowledgments, identifying links, and
identifying PDF metadata.

Build from this directory:

```powershell
pdflatex -jobname=validation_placement_neurips_2026_anonymous `
  -interaction=nonstopmode -halt-on-error main.tex
pdflatex -jobname=validation_placement_neurips_2026_anonymous `
  -interaction=nonstopmode -halt-on-error main.tex
```

The main paper content ends on page 8. References begin on page 8, continue on
page 9, and are followed by the appendices and mandatory checklist; these
materials do not count toward the NeurIPS main-paper page limit. The official
`neurips_2026.sty` file is included without modification.

Before submission, provide code and evidence through a genuinely anonymous
supplementary archive or anonymous repository. Do not replace the anonymous
style with `final` or `preprint` unless the venue stage specifically requires
it.
