PY ?= python3
TMP ?= /tmp/simgrammar-determinism

.PHONY: check validate style build sqlite find hooks determinism sources calibrate-sheet pr-check tasks pdf

check: validate style
	$(PY) scripts/build.py --check

validate:
	$(PY) scripts/validate.py

# house style for the book and the videos (book/STYLE.md, book/tells.yaml)
style:
	$(PY) scripts/style_check.py

build:
	$(PY) scripts/build.py

sqlite:
	$(PY) scripts/build.py --sqlite

# I11: two builds under different hash seeds must be byte-identical (CI runs this on every push)
determinism:
	rm -rf $(TMP) && mkdir -p $(TMP)
	PYTHONHASHSEED=1 $(PY) scripts/build.py --out $(TMP)/a
	PYTHONHASHSEED=2 $(PY) scripts/build.py --out $(TMP)/b
	diff -r $(TMP)/a $(TMP)/b && echo "determinism OK"

# optional: typeset the paper as pdf-out/paper.pdf with tectonic (not part of check or CI; ADR-0008). Its first run
# fetches TeX packages; one tectonic version gives a byte-identical PDF. `scripts/paper_pdf.py --tex-only` writes the source alone.
pdf: build
	$(PY) scripts/paper_pdf.py

# network: fetch cited sources and check claim quotes and store ids (not part of the build)
sources:
	$(PY) scripts/check_sources.py

# what CI will say about your branch: scope (E039) and, with network, the quotes and store ids you touched
pr-check:
	@git config github.user >/dev/null || { echo "set your GitHub handle first: git config github.user <handle> (the PR check compares it with the run's operator)"; exit 2; }
	$(PY) scripts/pr_scope.py --base origin/main --author "$$(git config github.user)"
	$(PY) scripts/check_sources.py --changed origin/main

tasks:
	$(PY) scripts/make_tasks.py

calibrate-sheet:
	$(PY) scripts/calibrate.py sheet

hooks:
	git config core.hooksPath .githooks
