# IEEE Manuscript

This directory is the self-contained submission package.

- `main.tex`: editable IEEE conference manuscript.
- `main.pdf`: compiled manuscript.
- `figures/`: figures used by the manuscript.
- `data/multiuav_resource_contrasts_v1.csv`: frozen source table for the
  compact resource figure.
- `build_resource_figure.py`: deterministic resource-figure generator.

Build from this directory:

```powershell
python build_resource_figure.py
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The manuscript reports static plan fidelity. It does not report official
simulator execution or physical-flight results.

