"""Dev stack manager: uv run python scripts/dev.py up|down|status|doctor|exec.
Starts Temporal dev server, mock finance API, control panel, test UI and the mitmproxy network plane."""
import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / ".run"
PROXY = "http://127.0.0.1:8888"
PORTS = {"temporal": 7233, "temporal-ui": 8233, "mock-api": 8001, "panel": 5050, "ui": 8000, "proxy": 8888}


def load_env():
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def port_open(p):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", p)) == 0


def services():
    py = [sys.executable, "-m"]
    bind = os.environ.get("BIND_HOST", "127.0.0.1")  # Instruqt sets 0.0.0.0 so service tabs can reach the ports
    temporal = ["temporal", "server", "start-dev", "--ip", bind, "--db-filename", str(RUN / "temporal.db")]
    if not shutil.which("temporal"):
        temporal = None
    return {
        "temporal": temporal,
        "mock-api": py + ["uvicorn", "app:app", "--app-dir", "shared/mock-finance-api", "--host", "127.0.0.1", "--port", "8001"],
        "panel": py + ["uvicorn", "controlpanel:app", "--app-dir", "shared/netplane", "--host", bind, "--port", "5050"],
        "ui": py + ["uvicorn", "app:app", "--app-dir", "shared/ui", "--host", bind, "--port", "8000"],
        "proxy": [sys.executable, "-m", "mitmproxy.tools.main"],  # replaced below
    }


def up():
    load_env()
    RUN.mkdir(exist_ok=True)
    cmds = services()
    if cmds["temporal"] is None:
        sys.exit("Temporal CLI not found. Install: brew install temporal  (or https://docs.temporal.io/cli)")
    cmds["proxy"] = ["mitmdump", "--listen-port", "8888", "-s", "shared/netplane/toggle_addon.py", "-q"]
    env = {**os.environ, "NETPLANE_STATE": str(RUN / "netplane-state.json")}
    (RUN / "netplane-state.json").write_text('{"kill_all": false, "services": {"llm": true}}')
    for name, cmd in cmds.items():
        port = {"temporal": 7233, "mock-api": 8001, "panel": 5050, "ui": 8000, "proxy": 8888}[name]
        if port_open(port):
            print(f"  {name}: port {port} already in use, skipping (run `just down` if it is stale)")
            continue
        log = open(RUN / f"{name}.log", "w")
        p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        (RUN / f"{name}.pid").write_text(str(p.pid))
        print(f"  {name}: started (pid {p.pid}, log .run/{name}.log)")
    for _ in range(40):
        if all(port_open(p) for p in PORTS.values()):
            break
        time.sleep(0.5)
    build_ca_bundle()
    status()
    print("\nUI http://localhost:8000   Control panel http://localhost:5050   Temporal UI http://localhost:8233")


def down():
    for pidf in RUN.glob("*.pid"):
        try:
            os.killpg(int(pidf.read_text()), signal.SIGTERM)
        except (ProcessLookupError, ValueError, PermissionError):
            pass
        pidf.unlink()
    print("stopped")


def status():
    for n, p in PORTS.items():
        print(f"  {n:12} :{p}  {'up' if port_open(p) else 'DOWN'}")


def build_ca_bundle():
    """certifi + mitmproxy CA, so HTTPS through the proxy is trusted by Python clients."""
    import certifi
    ca = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"
    for _ in range(20):
        if ca.exists():
            break
        time.sleep(0.5)
    if ca.exists():
        (RUN / "ca-bundle.pem").write_text(Path(certifi.where()).read_text() + "\n" + ca.read_text())


def exec_cmd(cwd, cmd, proxy=True):
    """Run a learner command with the LLM traffic routed through the network plane."""
    load_env()
    env = dict(os.environ)
    if proxy and port_open(8888):
        bundle = RUN / "ca-bundle.pem"
        env.update(HTTP_PROXY=PROXY, HTTPS_PROXY=PROXY, NO_PROXY="127.0.0.1,localhost")
        if bundle.exists():
            env.update(SSL_CERT_FILE=str(bundle), REQUESTS_CA_BUNDLE=str(bundle))
    sys.exit(subprocess.call(cmd, cwd=ROOT / cwd, env=env))


def doctor():
    load_env()
    ok = True

    def check(name, good, fix=""):
        nonlocal ok
        print(f"  [{'ok' if good else 'FAIL'}] {name}" + ("" if good else f"\n         fix: {fix}"))
        ok &= bool(good)

    check("Python 3.12+", sys.version_info >= (3, 12), "uv python install 3.12")
    check("uv", shutil.which("uv"), "https://docs.astral.sh/uv/")
    check("Temporal CLI", shutil.which("temporal"), "brew install temporal")
    check(".env present", (ROOT / ".env").exists() or os.environ.get("LITELLM_API_KEY"), "cp .env.example .env and fill it in")
    base = os.environ.get("LITELLM_API_BASE", "")
    check("LITELLM_API_BASE set", base.startswith("http"), "set LITELLM_API_BASE in .env")
    host = urlparse(base).hostname or ""
    if host in ("localhost", "127.0.0.1"):
        print("  [warn] LITELLM_API_BASE points at this machine. Traffic to localhost bypasses the proxy, so the 'cut the LLM'")
        print("         Break It scenes will not work. Use a gateway on another host. From Docker, a host gateway is")
        print("         reachable as http://host.docker.internal:<port>, not 127.0.0.1.")
    for n, p in PORTS.items():
        if not port_open(p):
            continue
        check(f"port {p} free for {n}", False, f"something already listens on {p}; run `just down` or stop it (macOS: AirPlay uses 5000, not 5050)")
    if base.startswith("http") and os.environ.get("LITELLM_API_KEY"):
        try:
            req = urllib.request.Request(base.rstrip("/") + "/v1/models", headers={"Authorization": "Bearer " + os.environ["LITELLM_API_KEY"]})
            urllib.request.urlopen(req, timeout=8)
            check(f"LiteLLM reachable ({urlparse(base).hostname})", True)
        except Exception as e:
            check("LiteLLM reachable", False, f"{e}")
    print("\nAll good." if ok else "\nFix the items above, then `just up`.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    argv = sys.argv[1:]
    cmd_argv = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd_argv = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["up", "down", "status", "doctor", "exec"])
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--no-proxy", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "exec":
        exec_cmd(a.cwd, cmd_argv, proxy=not a.no_proxy)
    {"up": up, "down": down, "status": status, "doctor": doctor}[a.cmd]()
