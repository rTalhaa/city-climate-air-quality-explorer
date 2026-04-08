UV := uv
LOOKBACK_DAYS ?= 365

.PHONY: install fetch run refresh lint

install:
	$(UV) sync

fetch:
	$(UV) run climate-fetch --lookback-days $(LOOKBACK_DAYS)

run:
	$(UV) run streamlit run dashboard/app.py

refresh:
	$(UV) run climate-fetch --lookback-days $(LOOKBACK_DAYS)
	$(UV) run streamlit run dashboard/app.py

lint:
	$(UV) run ruff check .
