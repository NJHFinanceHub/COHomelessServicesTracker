# Denver Homelessness Dollar Tracker — orchestration
#
# v1: a Makefile is enough. Reach for Prefect/Dagster only if it actually hurts.

PYTHON      ?= python3
DB_PATH     ?= data/processed/tracker.sqlite
SCHEMA      := db/schema.sql
WEB_DIR     := web

.PHONY: help db etl etl-checkbook compute build dev clean test fmt

help:
	@echo "Targets:"
	@echo "  make db              Initialize SQLite DB from db/schema.sql"
	@echo "  make etl             Run all ETL jobs (idempotent)"
	@echo "  make etl-checkbook   Pull latest Denver Open Checkbook payments"
	@echo "  make compute         Compute unit economics → data/processed/*.json"
	@echo "  make build           Build the Next.js static site"
	@echo "  make dev             Run the Next.js dev server"
	@echo "  make test            Run pytest on etl/tests/"
	@echo "  make clean           Remove built DB and processed JSON"

db: $(DB_PATH)

$(DB_PATH): $(SCHEMA)
	@mkdir -p $(dir $(DB_PATH))
	@rm -f $(DB_PATH)
	$(PYTHON) -c "import sqlite3; \
con = sqlite3.connect('$(DB_PATH)'); \
con.executescript(open('$(SCHEMA)').read()); \
con.close(); \
print('Initialized $(DB_PATH)')"

etl: etl-checkbook

etl-checkbook: $(DB_PATH)
	$(PYTHON) -m etl.sources.denver_checkbook.run --db $(DB_PATH)

compute: $(DB_PATH)
	$(PYTHON) -m etl.transform.compute_unit_economics --db $(DB_PATH) --out data/processed

build:
	cd $(WEB_DIR) && npm install && npm run build

dev:
	cd $(WEB_DIR) && npm install && npm run dev

test:
	$(PYTHON) -m pytest etl/tests -q

fmt:
	$(PYTHON) -m ruff format etl

clean:
	rm -f $(DB_PATH)
	rm -f data/processed/*.json
