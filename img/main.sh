#!/bin/bash
mode=$(echo "$1" | tr '[:upper:]' '[:lower:]')
if [[ ".${mode}" != ".local" ]] ; then
	cp -f /opt/spcs/stage/app.tar.gz /opt/spcs/
	cd /opt/spcs/
	tar -zxvf app.tar.gz
fi

cd /opt/spcs/app
ollama serve &
python3 -m streamlit run ./app.py --server.address=0.0.0.0 --browser.gatherUsageStats false $@ 2>&1
