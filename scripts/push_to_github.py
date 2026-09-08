import subprocess
import sys
import os

def run(cmd):
    print(f">> {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=r"D:\meme-intel", capture_output=True, text=True)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    return res.returncode

print("Checking git repo...")
if not os.path.exists(r"D:\meme-intel\.git"):
    run("git init -b main")

# Configure remote
run("git remote remove origin")
run("git remote add origin https://github.com/datphuocnguyen04/meme-intel.git")

# Stage files
run("git add .")

# Commit
run('git commit -m "Initial commit: Memecoin Intel Terminal"')

# Push
code = run("git push -u origin main")
if code == 0:
    print("SUCCESS: Pushed to datphuocnguyen04/meme-intel!")
else:
    print("Push finished with code:", code)
