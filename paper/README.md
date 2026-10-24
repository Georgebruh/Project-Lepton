# The paper (Workstream E)

LaTeX source of the LEPTON paper. One file per section in `sections/`, each opened by a comment
with its task code and the files its numbers come from. All styling is in `lepton.sty`, so the
sections can move to another template unchanged.

Status (October 23): E3 (the objectives), E4 (background, problem, scope and limitations, and
the assumptions table), E5 (the methodology, and its formulas in Appendix D), E6 (the results,
Tables 2-4 and Figures 1-4) and E9 (the executive summary, 247 words) are written. E7 (the
references) was checked on October 23: all 40 cited, every DOI matched against Crossref or
DataCite. E8 (the appendices) is written: A, the study design and Layer 1's steps (Figures A1
and A2); B, the models (Table B1); C, the assumptions; D, the formulas; E, the data sources
with their download dates (Table E1).
Note: E1's reading of the 2026 PJDSC primer (branch `E1-submission-rules`) is that the final
submission is a slide deck, a video and this repository, with no written paper. The team writes
the paper anyway, as the project's full report.

## Build it

**Overleaf:** zip this `paper/` folder, then New Project → Upload Project. In Menu, set
Compiler to pdfLaTeX and Main document to `main.tex`. Overleaf runs Biber (the references) by
itself.

**In VS Code** (Windows):

1. Install TinyTeX, a small TeX Live (no admin rights needed). In PowerShell (VS Code's
   terminal is fine):

   ```
   cd $env:TEMP
   curl.exe -fsSLO https://tinytex.yihui.org/install-bin-windows.ps1
   powershell -ExecutionPolicy Bypass -File install-bin-windows.ps1
   ```

   It installs to `%APPDATA%\TinyTeX` and adds itself to your PATH. Do not double-click
   TinyTeX's `install-bin-windows.bat` instead: on October 21, 2026 its download line quoted
   the address in single quotes, which Command Prompt does not understand, so it installed
   nothing.
2. Close VS Code completely and reopen it: its terminals keep the PATH it started with. If
   `tlmgr` is still "not recognized", sign out of Windows and back in: VS Code takes its PATH
   from Windows Explorer, which may still hold the old one. Then, in a terminal, add the
   packages this paper uses:

   ```
   tlmgr update --self
   tlmgr install biblatex biber biblatex-apa csquotes logreq montserrat fontaxes mweights ly1 titlesec enumitem eso-pic booktabs caption xurl babel-english microtype fancyhdr
   ```

3. Install the extension **LaTeX Workshop** (by James Yu). Mathematic's "LaTeX" extension
   only colours the text; it cannot build.
4. Open `paper/main.tex`. **Ctrl + Alt + B** builds it, **Ctrl + Alt + V** shows the PDF in a
   tab, and every save rebuilds it. Errors appear in the Problems panel.

**Without VS Code**, from this folder: `latexmk -pdf main.tex`, or `pdflatex main`,
`biber main`, `pdflatex main`, `pdflatex main`. A full TeX Live has every package. MiKTeX works
too, but its latexmk needs Perl installed separately.

Checked on October 24 with TinyTeX (TeX Live 2026) and latexmk, as LaTeX Workshop runs it:
27 pages with the appendices, no errors, no overfull lines, no undefined references, Biber
without warnings.

## Files

| File | Task | What |
| --- | --- | --- |
| `main.tex` | | Title block and the order of the sections |
| `lepton.sty` | | Page, Montserrat type, colours, headings, the band at the top of each page, `\checkme`, `\cfg` |
| `sections/summary.tex` | E9 | Executive summary (written last, under 250 words, with D5's primary result) and keywords |
| `sections/background.tex` | E4 | Background |
| `sections/problem.tex` | E4 | The problem |
| `sections/objectives.tex` | E3 | Objectives: the proposal's four, worded as they were tested; the last is D5's primary endpoint (M4 against M3) |
| `sections/scope.tex` | E4 | Scope, limitations, and what is not covered (future work) |
| `sections/methodology.tex` | E5 | Methodology: data, the shared flood computation, Layer 1, Layer 2, evaluation; Table 1 (the storms) |
| `sections/results.tex` | E6 | Results: the city forecast (Table 2, the scores; Table 3, the checks), the storm runs (Table 4, the doses) and D8's Figures 1-4. Numbers from `results/`, including `python -m src.score_tables` |
| `sections/appendix.tex` | E8 | Appendices A-E: the study design and Layer 1's steps (Figures A1, A2), the models (Table B1), E4's assumptions, E5's formulas, the data sources with download dates (Table E1) |
| `tables/assumptions.tex` | E4 | Table C1: every assumption, its value, its `config.py` name and how it was tested |
| `tables/formulas.tex` | E5 | Table D1: the formula behind each step of the methodology, with the `src/` file that computes it |
| `references.bib` | E7 | References, APA 7th edition (biblatex-apa) |
| `figures/` | D8, E8 | The paper's figures: D8's `d8_fig1`-`d8_fig4` PNGs and E8's `e8_fig_design.png` and `e8_fig_layer1.png`, copied from `results/` (copy them again after `python -m src.paper_figures` or `python -m src.diagrams` reruns); `figures/pjdsc-logo.png` replaces the band's words |

## Rules for writing here

- **Every number comes from `results/`, `config.py` or a note in `data/raw/`**, and the comment
  at the top of the section says which file. E11 checks them all.
- **Dose figures:** each one says it is a stock-planning figure, not a prescription (rule 10).
- **`\checkme{...}`** prints a red note: a claim a teammate must confirm, or a result still to
  come. Search the folder for `checkme` before submitting: none may be left.
- **Citations:** `\parencite{key}` gives (Author, 2026); `\textcite{key}` gives Author (2026).
  Add each new work to `references.bib` in sentence case, with proper nouns in braces, e.g.
  `{Quezon City}`, so their capitals survive.
- **No formulas in the main text** (E5); they go in an appendix.
- **No first person.** This is a research paper: write "this study", "the proposed model" (M4)
  or the passive ("cases were counted by week of onset"), never "we", "our" or "us".
- **No case-level records**, in the text or in a table (rule 11): weekly counts only.
- Build files go to the folder you compile in; `.gitignore` here keeps them out of git.
