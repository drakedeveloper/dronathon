"""Cache primary research for local reading; do not bundle papers with code."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1] / "artifacts" / "papers"
ROOT.mkdir(parents=True, exist_ok=True)
PAPERS = {
    "energy-1804.02238": "https://arxiv.org/pdf/1804.02238",
    "rotor-drag-1712.02402": "https://arxiv.org/pdf/1712.02402",
    "geometric-1003.2005": "https://arxiv.org/pdf/1003.2005",
    "airsim-1705.05065": "https://arxiv.org/pdf/1705.05065",
    "trajectories-2008.00595": "https://arxiv.org/pdf/2008.00595",
}


def fetch(item):
    name, url = item
    path = ROOT / f"{name}.pdf"
    try:
        if not path.exists():
            with urllib.request.urlopen(url, timeout=45) as response:
                data = response.read(25_000_000)
            if not data.startswith(b"%PDF"):
                raise ValueError("Response is not a PDF")
            path.write_bytes(data)
        reader = PdfReader(path)
        text = "\n".join(f"\n--- PAGE {i+1} ---\n" + p.extract_text() for i, p in enumerate(reader.pages))
        path.with_suffix(".txt").write_text(text, encoding="utf-8")
        return {"name": name, "url": url, "pages": len(reader.pages), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    except Exception as exc:
        return {"name": name, "url": url, "error": str(exc)}


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        manifest = list(pool.map(fetch, PAPERS.items()))
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
