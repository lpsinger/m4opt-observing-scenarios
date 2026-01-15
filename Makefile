all: data/observing-scenarios.ecsv data/events.ecsv tables/selected-detected.tex

runs.zip:
	curl -OL https://zenodo.org/records/18223624/files/runs.zip

data/observing-scenarios.ecsv: runs.zip scripts/unpack-observing-scenarios.py
	python scripts/unpack-observing-scenarios.py

tables/selected-detected.tex: scripts/selected-detected.py data/events.ecsv
	python scripts/selected-detected.py

data/events.ecsv: scripts/events-ecsv.py data/observing-scenarios.ecsv
	python scripts/events-ecsv.py
