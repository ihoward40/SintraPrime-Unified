"""
Gate 2: Self-contained process recovery test
Runs writer subprocess, kills it, then runs reader subprocess
"""
import os
import sys
import time
import subprocess
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

artifacts_dir = Path(__file__).parent


def test_process_recovery():
    """Execute forced-termination recovery test"""
    
    print("=== GATE 2: SEPARATE-PROCESS FORCED-TERMINATION RECOVERY ===")
    print(f"Working Directory: {os.getcwd()}")
    print(f"Artifacts Directory: {artifacts_dir}")
    
    db_path = artifacts_dir / "gate2_test.db"
    pid_file = artifacts_dir / "gate2_pid.txt"
    
    # Clean up from previous runs
    for f in [db_path, pid_file]:
        if f.exists():
            f.unlink()
            print(f"Cleaned up: {f}")
    
    # Step 1: Launch writer subprocess
    print("\n[1] Launching writer subprocess...")
    writer_script = artifacts_dir / "gate2_checkpoint_writer.py"
    
    proc = subprocess.Popen(
        [sys.executable, str(writer_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for PID file to be created
    max_wait = 10
    for i in range(max_wait):
        if pid_file.exists():
            break
        time.sleep(0.5)
    else:
        stdout, stderr = proc.communicate(timeout=2)
        print(f"ERROR: PID file not created after {max_wait}s")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False
    
    writer_pid = int(pid_file.read_text().strip())
    print(f"Writer PID: {writer_pid}")
    print(f"Writer process running: {proc.poll() is None}")
    
    # Wait for checkpoint to be written
    time.sleep(2)
    
    if not db_path.exists():
        proc.kill()
        stdout, stderr = proc.communicate()
        print(f"ERROR: Database not created")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False
    
    print(f"Database created: {db_path}")
    
    # Step 2: Forcibly terminate writer process
    print(f"\n[2] Forcibly terminating writer (PID {writer_pid})...")
    proc.kill()  # Force kill
    stdout, stderr = proc.communicate(timeout=2)
    print(f"Writer terminated. Exit code: {proc.returncode}")
    print(f"Writer STDOUT: {stdout[:200] if stdout else '(none)'}")
    if stderr:
        print(f"Writer STDERR: {stderr[:200]}")
    
    # Verify process is dead
    time.sleep(1)
    assert proc.poll() is not None, "Process should be terminated"
    print("Writer process confirmed dead")
    
    # Step 3: Launch fresh reader subprocess
    print(f"\n[3] Launching reader subprocess (fresh Python interpreter)...")
    reader_script = artifacts_dir / "gate2_checkpoint_reader.py"
    
    result = subprocess.run(
        [sys.executable, str(reader_script)],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    print(f"Reader exit code: {result.returncode}")
    print(f"Reader STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"Reader STDERR:\n{result.stderr}")
    
    # Step 4: Validate recovery
    if result.returncode == 0 and "RECOVERY_VERIFIED=True" in result.stdout:
        print("\n[4] ✓ GATE 2 PASSED: Checkpoint recovered in separate process after forced termination")
        return True
    else:
        print(f"\n[4] ✗ GATE 2 FAILED: Recovery failed")
        return False


if __name__ == "__main__":
    try:
        success = test_process_recovery()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Exception during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
