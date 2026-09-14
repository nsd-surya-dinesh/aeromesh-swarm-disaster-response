@echo off
echo ================================================================================
echo AEROMESH-SWARM SUBMISSION VERIFICATION
echo ================================================================================
echo.

cd /d C:\Users\nagas\uav_swarm_disaster_response

echo [1/4] Verifying ROS 2 Interface...
python ros2_interface\ros2_bridge.py
echo.
echo.

echo [2/4] Running Quick Test Sample...
python -m pytest tests/test_comm.py::test_rf_channel_creation -v
echo.
echo.

echo [3/4] Checking Project Structure...
echo Core modules:
dir /b core\*.py
echo.
echo ROS2 interface:
dir /b ros2_interface\*.py
echo.
echo Documentation:
dir /b docs\*.md
echo.

echo [4/4] Verifying Demo Snapshots...
if exist scenario_3_snapshots (
    echo [+] Demo snapshots found:
    dir /b scenario_3_snapshots\*.png
) else (
    echo [!] No snapshots yet - run: python generate_demo_snapshots.py 3
)
echo.
echo.

echo ================================================================================
echo VERIFICATION COMPLETE
echo ================================================================================
echo.
echo Next steps:
echo   1. Run full tests: python -m pytest tests/ -v
echo   2. Run scenario: python run_simulation.py --scenario 1
echo   3. Check status: python verify_submission.py
echo.
pause
