"""
Are the Blender renders in blender/out still drawn from the data as it is now?

Plain Python, no Blender, so CI runs it. It recomputes the inputs fingerprint (blender/inputs.py:
the drawn parts of expeditions/dist/data plus the render scripts) and each output's sha256, and
compares them with blender/out/badr.manifest.json. A mismatch means the data, the script or a file
changed since the render: re-render on a Mac with the command it prints, and commit what it writes.
"""

from __future__ import annotations

import json
import sys

import inputs


def main() -> int:
    if not inputs.MANIFEST.exists():
        print(f"FAIL: {inputs.MANIFEST.relative_to(inputs.ROOT)} is missing; render with:\n  {inputs.COMMAND}")
        return 1
    manifest = json.loads(inputs.MANIFEST.read_text(encoding="utf-8"))
    stale = []
    if manifest.get("inputs_sha256") != inputs.fingerprint():
        stale.append("the inputs changed (badr.json or stars.json where the render draws them, or a render script)")
    for name, out in manifest.get("outputs", {}).items():
        path = inputs.OUT / name
        if not path.exists():
            stale.append(f"{name} is missing")
        elif inputs.file_sha(path) != out.get("sha256"):
            stale.append(f"{name} is not the file the render wrote")
    if stale:
        print("FAIL: the Blender renders are stale:")
        for s in stale:
            print(f"  - {s}")
        print(f"Re-render on a Mac with Blender {manifest.get('blender', '5.2')}, from the repository root:\n  {inputs.COMMAND}")
        return 1
    print(f"OK: {len(manifest['outputs'])} Blender renders match their inputs ({manifest['inputs_sha256'][:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
