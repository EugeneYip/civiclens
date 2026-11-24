"""Fail-closed checks for the roster pilot; standard library only."""
import json
from pathlib import Path
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"www.cec.gov.tw", "web.cec.gov.tw"}

def validate(data):
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(data["release_status"] == "blocked_pending_independent_review", "Pilot is not approved for publication")
    require(data["expected_count"] == 6 and data["national_reference_count"] == 19100, "Wrong scope or denominator")
    records = data["records"]
    require(len(records) == data["expected_count"], "Incomplete district")
    numbers = [r["ballot_number"] for r in records]
    require(numbers == list(range(1, data["expected_count"] + 1)), "Missing, duplicate or unsorted ballot number")
    keys = set()
    registry = data["source_registry"]
    for r in records:
        key = tuple(r[k] for k in ("election_id", "jurisdiction_code", "office_id", "district_id", "ballot_number"))
        require(key[:4] == ("2026-local", "01", "municipal-mayor", "01-citywide"), "Unexpected district")
        require(key not in keys, "Duplicate identity key")
        keys.add(key)
        require(set(r["fields"]) == {"name", "party"}, "Unexpected personal fields")
        for field, expected_ids in (("name", {"final", "draw"}), ("party", {"draw"})):
            f = r["fields"][field]
            require(isinstance(f["value"], str) and bool(f["value"].strip()), "Missing value")
            require(f["status"] == "verified" and f["source_kind"] == "official", "Unverified field")
            evidence = f["evidence"]
            require({e["url"] for e in evidence} == {registry[i]["url"] for i in expected_ids}, "Missing or wrong primary source")
            for e in evidence:
                u = urlsplit(e["url"])
                require(u.scheme == "https" and u.hostname in ALLOWED and not u.username and not u.password, "Unapproved source host")
                require(bool(e["locator"]) and bool(e["reviewer"]) and e["retrieved_on"] == data["reviewed_on"], "Incomplete evidence")
    return len(records)

if __name__ == "__main__":
    print("Pilot records validated:", validate(json.loads((ROOT / "data/roster-pilot.json").read_text())))
