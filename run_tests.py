"""
运行全量测试并打印结果
"""
import subprocess
import sys
import os

env = os.environ.copy()
env.setdefault("QT_QPA_PLATFORM", "offscreen")

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "--timeout=30"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    env=env
)

output = result.stdout + result.stderr

with open("pytest_result.txt", "w", encoding="utf-8") as f:
    f.write(output)

lines = output.splitlines()
print(f"共 {len(lines)} 行，退出码: {result.returncode}")
print("\n".join(lines[-30:]))
sys.exit(result.returncode)
