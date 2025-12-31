all: data/observing-scenarios.ecsv data/events.ecsv tables/selected-detected.tex

runs_SNR-10.zip:
	curl -OL https://zenodo.org/records/14585837/files/runs_SNR-10.zip

data/observing-scenarios.ecsv: runs_SNR-10.zip scripts/unpack-observing-scenarios.py
	python scripts/unpack-observing-scenarios.py

tables/selected-detected.tex: scripts/selected-detected.py data/events.ecsv
	python scripts/selected-detected.py

data/events.ecsv: scripts/events-ecsv.py
	python scripts/events-ecsv.py
