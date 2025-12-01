.PHONY: install-docs
install-docs:
	pip install -e "dev/[docs]"

.PHONY: serve-docs
serve-docs:
	mkdocs serve
