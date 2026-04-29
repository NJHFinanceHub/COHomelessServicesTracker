"""
Socrata SODA 2.0 client for the Denver Open Checkbook.

Dataset: City of Denver Checkbook
URL:     https://data.colorado.gov/Business/City-of-Denver-Checkbook/wnau-xrqi
API:     https://data.colorado.gov/resource/wnau-xrqi.json

The client is intentionally tiny: a metadata fetcher (so we discover real
column names at runtime instead of hard-coding them and silently breaking
when the city renames a field), a paginated `query` generator, and a
where-clause builder. No DB writes — that lands in Phase 1.

Authentication is optional. Without a `SOCRATA_APP_TOKEN` env var, requests
are throttled per Socrata's anonymous-user policy; with one, they get the
higher per-token quota. Either way the data is public.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional

import requests


DEFAULT_DOMAIN = "data.colorado.gov"
DEFAULT_DATASET_ID = "wnau-xrqi"  # City of Denver Checkbook
DEFAULT_PAGE_SIZE = 1000          # Socrata hard-caps $limit at 50000 but 1000 is plenty
USER_AGENT = "denver-homelessness-tracker/0.1 (+https://github.com/njhfinancehub/cohomelessservicestracker)"


@dataclass(frozen=True)
class SocrataDataset:
    domain: str = DEFAULT_DOMAIN
    dataset_id: str = DEFAULT_DATASET_ID

    @property
    def resource_url(self) -> str:
        return f"https://{self.domain}/resource/{self.dataset_id}.json"

    @property
    def metadata_url(self) -> str:
        # Views API returns the canonical metadata blob (column names, types, last update)
        return f"https://{self.domain}/api/views/{self.dataset_id}.json"


class SocrataClient:
    """Minimal SODA 2.0 client. One dataset per instance."""

    def __init__(
        self,
        dataset: Optional[SocrataDataset] = None,
        app_token: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.dataset = dataset or SocrataDataset()
        self.app_token = app_token or os.environ.get("SOCRATA_APP_TOKEN") or ""
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        if self.app_token:
            self._session.headers["X-App-Token"] = self.app_token

    # ---- metadata --------------------------------------------------------

    def metadata(self) -> Dict[str, Any]:
        """Fetch view metadata. Used to discover real column names."""
        resp = self._session.get(self.dataset.metadata_url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def columns(self) -> List[Dict[str, str]]:
        """Return `[{name, fieldName, dataTypeName}, ...]` from metadata."""
        meta = self.metadata()
        cols = meta.get("columns", []) or []
        return [
            {
                "name": c.get("name", ""),
                "fieldName": c.get("fieldName", ""),
                "dataTypeName": c.get("dataTypeName", ""),
            }
            for c in cols
        ]

    def last_updated(self) -> Optional[int]:
        """Epoch seconds of dataset's last update (`rowsUpdatedAt`), if present."""
        meta = self.metadata()
        return meta.get("rowsUpdatedAt")

    # ---- query -----------------------------------------------------------

    def query(
        self,
        *,
        select: Optional[str] = None,
        where: Optional[str] = None,
        order: Optional[str] = None,
        limit: int = DEFAULT_PAGE_SIZE,
        max_rows: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream rows matching the query. Paginates with $limit/$offset.

        SoQL clauses are passed verbatim — caller is responsible for quoting
        per Socrata syntax. For `where`, double-quotes around field names and
        single-quotes around string values, e.g.:

            where="upper(vendor_name) LIKE '%COALITION%'"
        """
        params_base: Dict[str, str] = {"$limit": str(limit)}
        if select:
            params_base["$select"] = select
        if where:
            params_base["$where"] = where
        if order:
            params_base["$order"] = order

        offset = 0
        emitted = 0
        while True:
            params = dict(params_base)
            params["$offset"] = str(offset)
            resp = self._session.get(
                self.dataset.resource_url,
                params=params,
                timeout=self.timeout,
            )
            # Socrata returns 429 when throttled; back off and retry once
            if resp.status_code == 429:
                time.sleep(2.0)
                resp = self._session.get(
                    self.dataset.resource_url,
                    params=params,
                    timeout=self.timeout,
                )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                return
            for row in batch:
                yield row
                emitted += 1
                if max_rows is not None and emitted >= max_rows:
                    return
            if len(batch) < limit:
                return
            offset += limit

    def count(self, where: Optional[str] = None) -> int:
        """COUNT(*) over the dataset, optionally filtered."""
        params: Dict[str, str] = {"$select": "count(*) AS n"}
        if where:
            params["$where"] = where
        resp = self._session.get(
            self.dataset.resource_url,
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return 0
        return int(rows[0].get("n", 0))
