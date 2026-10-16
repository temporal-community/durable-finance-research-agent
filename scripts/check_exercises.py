"""Copy each exercise dir, uncomment every `# TODO` block, run its tests. Exercise+uncomment must go green."""
import re, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(sys.argv[1])
bad = 0
for mod in sorted((ROOT / "modules").iterdir()):
    ex = mod / "exercise"
    tmp = Path(tempfile.mkdtemp()) / "exercise"
    shutil.copytree(ex, tmp, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "published"))
    for f in tmp.glob("*.py"):
        lines, out, active = f.read_text().split("\n"), [], False
        for ln in lines:
            if re.match(r"\s*# TODO", ln):
                active = True; out.append(ln); continue
            if active and re.match(r"\s*#( |$)", ln):
                out.append(re.sub(r"^(\s*)# ?", r"\1", ln)); continue
            active = False; out.append(ln)
        f.write_text("\n".join(out))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-o", "asyncio_mode=auto"], cwd=tmp, capture_output=True, text=True)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
    print(mod.name, "->", "GREEN" if r.returncode == 0 else "RED", "|", tail)
    bad += r.returncode != 0
sys.exit(bad)
