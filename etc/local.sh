#!/bin/bash
eval "$(conda shell.bash hook)"
conda activate streamlit
export SNOWCLI_CONNECTION_NAME="mkazwe001_docmore"
../img/main.sh local
