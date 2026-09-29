# Launch OfflineMind in Streamlit
$venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -m streamlit run (Join-Path $PSScriptRoot "app\main.py")
} else {
    python -m streamlit run app\main.py
}
