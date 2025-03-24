#!/bin/bash
eval "$(conda shell.bash hook)"
conda activate streamlit
./main.sh local
