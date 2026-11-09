@echo off
rem Re-run the analysis (no training) for saved runs, then the attribution and comparison.
rem Needs the predictions written by train_model.py / train_cicids2017.py.
rem Run from the repository root with the virtual environment active:
rem     scripts\rerun_analysis.bat                 (all five runs)
rem     scripts\rerun_analysis.bat jan_rf cic_hgb  (only the named runs)
rem The baseline (feb_rf) is analysed by: python scripts\analyze_attack_share.py

set RUNS=%*
if "%RUNS%"=="" set RUNS=feb_hgb jan_rf jan_hgb cic_rf cic_hgb

for %%R in (%RUNS%) do (
    echo.
    echo ================= %%R =================
    python scripts\analyze_attack_share.py --run %%R || exit /b 1
)

python scripts\attribute_alarms.py || exit /b 1
python scripts\compare_runs.py || exit /b 1
echo.
echo Done. Commit the changes in results\ and push.
