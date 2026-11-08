import importlib
import pkgutil
import json
import gz
print("gz namespace", list(gz.__path__))
for package in ("gz.transport13", "gz.msgs10"):
    try:
        module = importlib.import_module(package)
        print(package, "OK", getattr(module, "Node", None))
        if package.endswith("msgs10"):
            print([m.name for m in pkgutil.iter_modules(module.__path__) if any(x in m.name for x in ("box", "pose", "factory", "wrench"))])
        else:
            print("subscribe", module.Node.subscribe.__doc__)
            print("request", module.Node.request.__doc__)
    except Exception as exc:
        print(package, type(exc).__name__, str(exc))
