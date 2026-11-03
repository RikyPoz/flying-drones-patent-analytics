"""Shared sector definition: loads config/sector.yaml and builds the sector queries.

Usage in any notebook (works from the repo root, notebooks/ or src/):

    import sys
    from pathlib import Path
    ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
                if (p / "config" / "sector.yaml").exists())
    sys.path.insert(0, str(ROOT / "src"))

    from sector import load_sector, sector_family_ids, sector_appln_ids
    cfg = load_sector()
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "sector.yaml"


@dataclass(frozen=True)
class Sector:
    version: str
    env: str
    name: str
    cpc_prefixes: tuple
    ipc_prefixes: tuple
    keywords: tuple
    year_min: int
    year_max: int
    family_time_column: str
    appln_time_column: str
    truncated_years: dict
    ipr_type: str

    @property
    def last_complete_year(self) -> int:
        t = self.truncated_years
        return self.year_max - max(t[self.family_time_column], t[self.appln_time_column])

    def output_name(self, stem: str, ext: str = "csv") -> str:
        """e.g. cfg.output_name('validation') -> 'validation_TEST_v1.csv'"""
        return f"{stem}_{self.env}_{self.version}.{ext}"


def load_sector(path: Path = CONFIG_PATH, env: str | None = None) -> Sector:
    """Read the YAML config. Pass env='PROD' to override the environment without editing the file."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    s, t = raw["sector"], raw["time"]
    return Sector(
        version=str(raw["version"]),
        env=env or raw.get("env", "TEST"),
        name=s["name"],
        cpc_prefixes=tuple(s.get("cpc_prefixes") or ()),
        ipc_prefixes=tuple(s.get("ipc_prefixes") or ()),
        keywords=tuple(k.lower() for k in (s.get("keywords") or ())),
        year_min=int(t["year_min"]),
        year_max=int(t["year_max"]),
        family_time_column=t["family_time_column"],
        appln_time_column=t["appln_time_column"],
        truncated_years=dict(t["truncated_years"]),
        ipr_type=raw.get("counting", {}).get("ipr_type", "PI"),
    )


# ---------------------------------------------------------------- query builders (TIP only)
# epo.tipdata is imported lazily so load_sector() also works outside TIP.

def _conditions():
    from sqlalchemy import func, or_
    from epo.tipdata.patstat.database.models import TLS202_APPLN_TITLE, TLS203_APPLN_ABSTR

    def symbol_prefix(column, codes):
        symbol = func.replace(column, " ", "")
        return or_(*(symbol.like(c.replace(" ", "") + "%") for c in codes))

    def keyword(terms):
        title = func.lower(TLS202_APPLN_TITLE.appln_title)
        abstract = func.lower(TLS203_APPLN_ABSTR.appln_abstract)
        return or_(*(col.like(f"%{t}%") for t in terms for col in (title, abstract)))

    return symbol_prefix, keyword


def _sector_query(db, cfg: Sector, key_column):
    """UNION of CPC, IPC and keyword matches, returning one column (appln_id or docdb_family_id)."""
    from epo.tipdata.patstat.database.models import (
        TLS201_APPLN, TLS202_APPLN_TITLE, TLS203_APPLN_ABSTR, TLS209_APPLN_IPC, TLS224_APPLN_CPC,
    )
    symbol_prefix, keyword = _conditions()
    parts = []
    if cfg.cpc_prefixes:
        parts.append(
            db.query(key_column)
            .join(TLS224_APPLN_CPC, TLS201_APPLN.appln_id == TLS224_APPLN_CPC.appln_id)
            .filter(symbol_prefix(TLS224_APPLN_CPC.cpc_class_symbol, cfg.cpc_prefixes))
        )
    if cfg.ipc_prefixes:
        parts.append(
            db.query(key_column)
            .join(TLS209_APPLN_IPC, TLS201_APPLN.appln_id == TLS209_APPLN_IPC.appln_id)
            .filter(symbol_prefix(TLS209_APPLN_IPC.ipc_class_symbol, cfg.ipc_prefixes))
        )
    if cfg.keywords:
        parts.append(
            db.query(key_column)
            .select_from(TLS201_APPLN)
            .outerjoin(TLS202_APPLN_TITLE, TLS201_APPLN.appln_id == TLS202_APPLN_TITLE.appln_id)
            .outerjoin(TLS203_APPLN_ABSTR, TLS201_APPLN.appln_id == TLS203_APPLN_ABSTR.appln_id)
            .filter(keyword(cfg.keywords))
        )
    if not parts:
        raise ValueError("config/sector.yaml defines no CPC codes, IPC codes or keywords")
    return parts[0].union(*parts[1:])   # UNION removes duplicates


def sector_appln_ids(db, cfg: Sector):
    """Query of the appln_ids that match the sector definition (Step 0 style)."""
    from epo.tipdata.patstat.database.models import TLS201_APPLN
    return _sector_query(db, cfg, TLS201_APPLN.appln_id.label("appln_id"))


def sector_family_ids(db, cfg: Sector):
    """Query of the docdb_family_ids that belong to the sector (Step 1 style)."""
    from epo.tipdata.patstat.database.models import TLS201_APPLN
    return _sector_query(db, cfg, TLS201_APPLN.docdb_family_id.label("docdb_family_id"))
