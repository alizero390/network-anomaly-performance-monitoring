@echo off
rem Train and analyse the three robustness runs, then compare them with the baseline.
rem Run from the repository root with the virtual environment active:
rem     scripts\run_robustness.bat                 (all three runs)
rem     scripts\run_robustness.bat jan_rf jan_hgb  (only the named runs)
rem Expect roughly 15-30 minutes for all three.

set RUNS=%*
if "%RUNS%"=="" set RUNS=feb_hgb jan_rf jan_hgb

for %%R in (%RUNS%) do (
    for /f "tokens=1,2 delims=_" %%A in ("%%R") do (
        echo.
        echo ================= %%R =================
        python scripts\train_model.py --session %%A --model %%B || exit /b 1
        python scripts\analyze_attack_share.py --run %%R || exit /b 1
    )
)

python scripts\compare_runs.py || exit /b 1
echo.
echo Done. Commit the changes in results\ and push.
