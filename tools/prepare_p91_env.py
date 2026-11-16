#!/usr/bin/env python3
"""P94 preflight for the P91 one-shot session.

Verifies the deployed NRO, restores Forge INFO logging (root cause of the
"no [rai] lines" sessions), rotates the previous log WITHOUT deleting it,
and clears the watcher status file.

Exit code: 0 = safe to play, 1 = DO NOT PLAY (preflight failed).
"""
import datetime
import hashlib
import shutil
import sys
from pathlib import Path

EXPECT_MD5 = "0ab6cbec301b4336fbbd50dcb71f9008"


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 7:
        print("[x] usage: prepare_p91_env.py CFG PLUG REF OUT STATUS BACKUP")
        return 1
    cfg, plug, ref, out, status, backup = (Path(x) for x in sys.argv[1:7])
    errors = []

    # -- 1. deployed NRO must be byte-identical to the P90 build -------------
    if not plug.exists() or not ref.exists():
        errors.append("plugin NRO or reference NRO missing")
    else:
        a, b = md5(plug), md5(ref)
        if a != b:
            errors.append("deployed NRO differs from out/rai_p90_probe.nro")
        elif a != EXPECT_MD5:
            errors.append("deployed NRO md5 %s != expected %s" % (a, EXPECT_MD5))
        else:
            print("[ok] deployed NRO = P90 probe build (%s)" % a[:8])

    # -- 2. Forge log level: 'error' silently drops every [rai] INFO line ---
    if not cfg.exists():
        errors.append("Forge config.ini not found: %s" % cfg)
    else:
        text = cfg.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        hit = -1
        for i, line in enumerate(lines):
            s = line.strip().lower().replace(" ", "")
            if s.startswith("level="):
                hit = i
                break
        if hit < 0:
            if not backup.exists():
                shutil.copy2(cfg, backup)
            lines.insert(0, "[log]")
            lines.insert(1, "level = info")
            cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print("[fix] [log] level missing -> inserted 'level = info'")
        else:
            value = lines[hit].strip().lower().replace(" ", "").split("=", 1)[1]
            if value != "info":
                if not backup.exists():
                    shutil.copy2(cfg, backup)
                lines[hit] = "level = info"
                cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
                print("[fix] Forge log level '%s' -> 'info' (backup: %s)"
                      % (value, backup.name))
            else:
                print("[ok] Forge log level = info")

    # -- 3. rotate by timestamp, never delete an older session --------------
    if out.exists():
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = out.with_name(out.name + "." + stamp + ".prev")
        n = 1
        while dst.exists():
            dst = out.with_name(out.name + "." + stamp + "_" + str(n) + ".prev")
            n += 1
        shutil.move(str(out), str(dst))
        print("[ok] previous log preserved as %s" % dst.name)

    # -- 4. reset watcher status --------------------------------------------
    if status.exists():
        status.unlink()
    status.parent.mkdir(parents=True, exist_ok=True)

    if errors:
        for e in errors:
            print("[x] " + e)
        print("[x] PREFLIGHT FAILED - DO NOT PLAY. Tell the agent.")
        return 1
    print("[ok] PREFLIGHT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
