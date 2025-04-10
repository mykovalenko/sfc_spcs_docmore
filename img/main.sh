#!/bin/bash
mode=$(echo "$1" | tr '[:upper:]' '[:lower:]')
if [[ ".${mode}" != ".local" ]] ; then
	cp -f /opt/spcs/stage/app.tar.gz /opt/spcs/
	cd /opt/spcs/
	tar -zxvf app.tar.gz

	ollama serve & python3 -m streamlit run ./app/app.py --server.address=0.0.0.0 --browser.gatherUsageStats false $@ 2>&1
else
	cd ../
	python3 -m streamlit run ./app/app.py --server.address=0.0.0.0 --browser.gatherUsageStats false $@ 2>&1
fi

