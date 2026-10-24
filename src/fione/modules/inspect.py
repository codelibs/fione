"""Reads an uploaded module's ``MODULE`` metadata: ``python -I -m fione.modules.inspect <file>``.

Importing the file runs its top-level code, which is why this is a separate short-lived process
and never the API process. It prints ``{"module": MODULE, "has_run": bool}`` as JSON on stdout
and nothing else; the parent checks the metadata. Files it may write are capped, so a module
cannot fill the disk while it is being inspected.
"""

import importlib.util
import json
import sys

MAX_FILE_BYTES = 1 << 20  # the largest file this process may write (stdout included)


def main(path: str) -> int:
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE_BYTES, MAX_FILE_BYTES))
    except (ImportError, ValueError, OSError):
        pass  # no limits on this platform; the parent's timeout still applies
    spec = importlib.util.spec_from_file_location("fione_uploaded_module", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "MODULE"):
        print("the file does not define MODULE", file=sys.stderr)
        return 2
    if not callable(getattr(module, "run", None)):
        print("the file does not define run(df, params, ctx)", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps({"module": module.MODULE, "has_run": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
