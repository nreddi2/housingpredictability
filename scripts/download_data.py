"""Fetch public project inputs once and preserve the original bytes.

Existing snapshots are verified and reused. Set CENSUS_API_KEY in the local
environment to include ACS income estimates. Keys are never written to files.
"""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib
import json
import os
import urllib.request
import urllib.parse
import argparse

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
SOURCES = {
    "zillow_county_zhvi_2026-11-01.csv": "https://files.zillowstatic.com/research/public_csvs/zhvi/County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    "mortgage30us_2026-11-01.csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acs-years', type=int, nargs='+', default=[2019, 2024])
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "pilot_download_manifest.json"
    records = json.loads(path.read_text()) if path.exists() else []
    known = {r["filename"]: r for r in records}
    for name, url in SOURCES.items():
        dest = RAW / name
        if dest.exists():
            if name not in known:
                raise ValueError(f"Existing file lacks provenance: {name}")
            assert hashlib.sha256(dest.read_bytes()).hexdigest() == known[name]["sha256"]
            print(f"Verified existing snapshot: {name}")
            continue
        # Provider URLs are live. A different response cannot recreate the old vintage.
        request = urllib.request.Request(url, headers={"User-Agent": "DTSC2302 academic research"})
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
        if b"<html" in body[:1000].lower():
            raise ValueError(f"Provider returned HTML instead of CSV for {name}")
        digest = hashlib.sha256(body).hexdigest()
        if name in known and digest != known[name]["sha256"]:
            raise ValueError(f"Live data changed for {name}. Obtain the original snapshot from the group; do not relabel a new vintage.")
        now = datetime.now(timezone.utc)
        if name not in known and now.astimezone(ZoneInfo("America/New_York")).date().isoformat() != "2026-11-01":
            raise ValueError("This downloader targets the Nov 1 snapshot. Configure a new dated snapshot before downloading a new vintage.")
        dest.write_bytes(body)
        if name not in known:
            records.append({"filename": name, "url": url, "retrieved_at_utc": now.isoformat(),
                            "project_access_date": "2026-11-01", "sha256": digest, "bytes": len(body)})
            path.write_text(json.dumps(records, indent=2))
        print(f"Downloaded and verified: {name}")

    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        print("ACS not downloaded: Census requires an API key. Set CENSUS_API_KEY locally; never commit it.")
        return
    access_date = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    for year in sorted(set(args.acs_years)):
        params = {"get": "NAME,B19013_001E,B19013_001M", "for": "county:*", "in": "state:37"}
        public_url = f"https://api.census.gov/data/{year}/acs/acs5?" + urllib.parse.urlencode(params)
        url = public_url + "&key=" + urllib.parse.quote(key, safe="")
        name = f"acs5_income_nc_{year}_{access_date}.json"
        dest = RAW / name
        if dest.exists():
            item = next((r for r in records if r['filename'] == name), None)
            if item is None or hashlib.sha256(dest.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError(f"Existing ACS snapshot failed provenance verification: {name}")
            print(f"Verified existing ACS snapshot: {name}")
            continue
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                body = response.read()
            data = json.loads(body)
            assert len(data) == 101 and "B19013_001E" in data[0]
        except Exception:
            # Avoid echoing an exception whose URL could include the key.
            raise RuntimeError(f"ACS {year} request failed or returned unexpected data; verify the local key and Census service.") from None
        dest.write_bytes(body)
        records.append({"filename": name, "url": public_url,
                        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                        "project_access_date": access_date, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
        path.write_text(json.dumps(records, indent=2))
        print(f"Downloaded ACS {year}: 100 NC counties")


if __name__ == "__main__":
    main()
