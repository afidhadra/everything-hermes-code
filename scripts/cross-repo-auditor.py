#!/usr/bin/env python3
"""
Everything Hermes Code — Cross-Repo Auditor (Layer C)

Deep audit across FE (Vue/TS), BE (Go), and DB (SQL migrations).
Validates model field sync, RBAC/permission coverage, and data contract integrity.

Usage:
    python3 cross-repo-auditor.py --be <BE_DIR> --fe <FE_DIR>
    python3 cross-repo-auditor.py --be ~/frozen-pos-api --fe ~/frozen-pos-frontend
    python3 cross-repo-auditor.py --be ~/frozen-pos-api --fe ~/frozen-pos-frontend --check models
    python3 cross-repo-auditor.py --be ~/frozen-pos-api --fe ~/frozen-pos-frontend --check permissions
"""

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# Import Layer B's DB schema extractor
import importlib.util
_ra_spec = importlib.util.spec_from_file_location(
    "ra", Path(__file__).parent / "regression-analyzer.py"
)
ra = importlib.util.module_from_spec(_ra_spec)
_ra_spec.loader.exec_module(ra)


# ============================================================
# Models
# ============================================================

@dataclass
class StructField:
    name: str
    go_type: str
    json_tag: str
    db_tag: str


@dataclass
class GoStruct:
    name: str
    file: str
    fields: list[StructField] = field(default_factory=list)


@dataclass
class TSField:
    name: str
    ts_type: str
    optional: bool = False


@dataclass
class TSInterface:
    name: str
    file: str
    fields: list[TSField] = field(default_factory=list)


@dataclass
class PermissionCheck:
    location: str  # file:line
    perm_string: str
    context: str  # route guard, middleware, etc.


@dataclass
class Mismatch:
    entity: str
    layer: str  # BE, FE, DB
    field: str
    issue: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW


# ============================================================
# Go Struct Parser
# ============================================================

# Go struct pattern: type Name struct { ... }
GO_STRUCT_RE = re.compile(
    r'type\s+(\w+)\s+struct\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}',
    re.MULTILINE | re.DOTALL
)

# Go field: Name    Type    `json:"xxx" db:"yyy"`
GO_FIELD_RE = re.compile(
    r'^\s*([A-Z]\w*)\s+'  # Field name (exported)
    r'([\w\[\]\.\*\(\)]+)'  # Type
    r'(?:\s+`([^`]*)`)?'  # Tags
)

# Tag extractors
JSON_TAG_RE = re.compile(r'json:"([^,}]+)')
DB_TAG_RE = re.compile(r'db:"([^,}]+)')


def parse_go_structs(be_dir: Path) -> list[GoStruct]:
    """Parse all Go structs from model/entity/domain files."""
    structs = []
    skip_dirs = {"vendor", ".git", "node_modules", "build", "dist", "test"}

    # Focus on model/entity/domain files
    model_patterns = ["model", "entity", "domain", "dto", "response", "request"]

    for f in be_dir.rglob("*.go"):
        if any(part in skip_dirs for part in f.parts):
            continue

        # Skip test files
        if f.name.endswith("_test.go"):
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Only parse files that look like models
        fname_lower = f.name.lower()
        path_lower = str(f.relative_to(be_dir)).lower()
        is_model = any(p in path_lower for p in model_patterns)

        for m in GO_STRUCT_RE.finditer(content):
            name = m.group(1)
            body = m.group(2)

            # Skip non-model structs (config, etc.) unless in model dir
            if not is_model and name in ("App", "Config", "SMTPConfig",
                                          "DatabaseConfig", "RedisConfig"):
                continue

            struct = GoStruct(name=name, file=str(f.relative_to(be_dir)))
            for line in body.split("\n"):
                fm = GO_FIELD_RE.match(line)
                if fm:
                    fname = fm.group(1)
                    ftype = fm.group(2)
                    tags = fm.group(3) or ""

                    json_tag = ""
                    db_tag = ""
                    # Clean tags: remove escaped quotes
                    clean_tags = tags.replace('\\"', '"')
                    jm = JSON_TAG_RE.search(clean_tags)
                    if jm:
                        json_tag = jm.group(1).split(",")[0]
                    dm = DB_TAG_RE.search(clean_tags)
                    if dm:
                        db_tag = dm.group(1).split(",")[0]

                    struct.fields.append(StructField(
                        name=fname,
                        go_type=ftype,
                        json_tag=json_tag,
                        db_tag=db_tag,
                    ))

            if len(struct.fields) >= 3:
                structs.append(struct)

    return structs


# ============================================================
# TS Interface Parser
# ============================================================

TS_INTERFACE_RE = re.compile(
    r'(?:export\s+)?interface\s+(\w+)\s*\{([^}]+)\}',
    re.MULTILINE | re.DOTALL
)

TS_TYPE_RE = re.compile(
    r'(?:export\s+)?type\s+(\w+)\s*=\s*\{([^}]+)\}',
    re.MULTILINE | re.DOTALL
)

# TS field: name: type  or  name?: type
TS_FIELD_RE = re.compile(
    r'^\s*(\w+)(\?)?:\s*(.+?)(?:[,;]|\s*$)',
    re.MULTILINE
)

# Skip types that are not domain models
TS_SKIP_TYPES = {
    "ImportMetaEnv", "ComponentPublicInstanceConstructor",
    "ShallowUnwrapRef", "Awaited", "Promise",
}


def parse_ts_interfaces(fe_dir: Path) -> list[TSInterface]:
    """Parse TS interfaces and types from FE source (skip node_modules)."""
    interfaces = []
    skip_dirs = {"node_modules", ".git", "dist", "build", ".vite"}

    for f in fe_dir.rglob("*.ts"):
        if any(part in skip_dirs for part in f.parts):
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Parse interfaces
        for m in TS_INTERFACE_RE.finditer(content):
            name = m.group(1)
            body = m.group(2)

            if name in TS_SKIP_TYPES:
                continue

            iface = TSInterface(name=name, file=str(f.relative_to(fe_dir)))
            for fm in TS_FIELD_RE.finditer(body):
                iface.fields.append(TSField(
                    name=fm.group(1),
                    ts_type=fm.group(3).strip().rstrip(",;"),
                    optional=bool(fm.group(2)),
                ))

            if len(iface.fields) >= 2:
                interfaces.append(iface)

        # Parse type aliases with object body
        for m in TS_TYPE_RE.finditer(content):
            name = m.group(1)
            body = m.group(2)

            if name in TS_SKIP_TYPES:
                continue

            iface = TSInterface(name=name, file=str(f.relative_to(fe_dir)))
            for fm in TS_FIELD_RE.finditer(body):
                iface.fields.append(TSField(
                    name=fm.group(1),
                    ts_type=fm.group(3).strip().rstrip(",;"),
                    optional=bool(fm.group(2)),
                ))

            if len(iface.fields) >= 2:
                interfaces.append(iface)

    return interfaces


# ============================================================
# Permission Parser
# ============================================================

# BE permission strings: Permission(permUsecase, "produk.view")
BE_PERM_RE = re.compile(r'Permission\s*\([^)]+,\s*"([^"]+)"')
# BE role checks: RequireAnyRole(constants.RoleXxx, ...)
BE_ROLE_RE = re.compile(r'RequireAnyRole\s*\(([^)]+)\)')
BE_ROLE_CONST_RE = re.compile(r'constants\.(Role\w+)')


def parse_be_permissions(be_dir: Path) -> list[PermissionCheck]:
    """Extract permission strings from Go middleware/route files."""
    perms = []
    skip_dirs = {"vendor", ".git", "test"}

    for f in be_dir.rglob("*.go"):
        if any(part in skip_dirs for part in f.parts):
            continue
        if f.name.endswith("_test.go"):
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(content.split("\n"), 1):
            for m in BE_PERM_RE.finditer(line):
                perms.append(PermissionCheck(
                    location=f"{f.relative_to(be_dir)}:{i}",
                    perm_string=m.group(1),
                    context="middleware",
                ))
            for m in BE_ROLE_RE.finditer(line):
                roles = BE_ROLE_CONST_RE.findall(m.group(1))
                for role in roles:
                    perms.append(PermissionCheck(
                        location=f"{f.relative_to(be_dir)}:{i}",
                        perm_string=f"role:{role}",
                        context="role_guard",
                    ))

    return perms


# FE PERMISSIONS constant: PERMISSIONS = { X: 'value', ... }
FE_PERMS_CONST_RE = re.compile(
    r'PERMISSIONS\s*=\s*\{([^}]+)\}',
    re.DOTALL
)
FE_PERM_VALUE_RE = re.compile(r"(\w+):\s*'([^']+)'")

# FE route guards: permissions: [PERMISSIONS.XXX, ...]
FE_ROUTE_PERM_RE = re.compile(
    r'permissions:\s*\[([^\]]+)\]',
    re.MULTILINE
)
# FE allowedRoles: ['developer', 'owner', ...]
FE_ROUTE_ROLE_RE = re.compile(
    r"allowedRoles:\s*\[([^\]]+)\]",
    re.MULTILINE
)


def parse_fe_permissions(fe_dir: Path) -> tuple[set[str], list[str]]:
    """Extract permission strings and route guards from FE.
    Returns (permission_strings, route_guard_strings)
    """
    perm_strings = set()
    route_guards = []
    skip_dirs = {"node_modules", ".git", "dist", "build"}

    # Find permissions constant file
    for f in fe_dir.rglob("*.ts"):
        if any(part in skip_dirs for part in f.parts):
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Parse PERMISSIONS constant
        for m in FE_PERMS_CONST_RE.finditer(content):
            for vm in FE_PERM_VALUE_RE.finditer(m.group(1)):
                perm_strings.add(vm.group(2))

        # Parse route guards
        fname = f.name
        for m in FE_ROUTE_PERM_RE.finditer(content):
            guard = m.group(1).strip()
            route_guards.append(f"{fname}: permissions: [{guard}]")

        for m in FE_ROUTE_ROLE_RE.finditer(content):
            roles = m.group(1).strip()
            route_guards.append(f"{fname}: allowedRoles: [{roles}]")

    return perm_strings, route_guards


# ============================================================
# Cross-Reference Validators
# ============================================================

def snake_to_camel(s: str) -> str:
    """Convert snake_case to camelCase."""
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def camel_to_snake(s: str) -> str:
    """Convert camelCase/PascalCase to snake_case."""
    # Handle consecutive uppercase (e.g. ID, URL, SKU, UPC)
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', s)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.lower()


def validate_model_sync(
    go_structs: list[GoStruct],
    ts_interfaces: list[TSInterface],
    db_tables: dict,
) -> list[Mismatch]:
    """Cross-reference field names across Go, TS, and DB."""
    mismatches = []

    # Build lookup: struct name → set of json tags
    go_by_name: dict[str, GoStruct] = {s.name.lower(): s for s in go_structs}
    ts_by_name: dict[str, TSInterface] = {i.name.lower(): i for i in ts_interfaces}

    # Go ↔ TS comparison (match by json tag ↔ ts field name)
    matched = 0
    for go_struct in go_structs:
        # Try to find matching TS interface
        ts_key = go_struct.name.lower()

        # Also try without common suffixes
        candidates = [ts_key, ts_key.replace("model", ""),
                       ts_key.replace("entity", ""),
                       ts_key + "response", ts_key + "dto"]

        ts_match = None
        for cand in candidates:
            if cand in ts_by_name:
                ts_match = ts_by_name[cand]
                break

        if not ts_match:
            continue

        matched += 1
        go_json_fields = {f.json_tag for f in go_struct.fields if f.json_tag}
        ts_field_names = {f.name for f in ts_match.fields}

        # Fields in Go but not TS
        for gf in go_struct.fields:
            if gf.json_tag and gf.json_tag not in ts_field_names:
                # Check if it's optional/nullable
                if "omitempty" not in gf.json_tag:
                    mismatches.append(Mismatch(
                        entity=go_struct.name,
                        layer="FE",
                        field=gf.json_tag,
                        issue=f"Go field '{gf.name}' (json: '{gf.json_tag}') missing from TS interface '{ts_match.name}'",
                        severity="MEDIUM",
                    ))

        # Fields in TS but not Go
        for tf in ts_match.fields:
            if tf.name not in go_json_fields and not tf.optional:
                mismatches.append(Mismatch(
                    entity=ts_match.name,
                    layer="BE",
                    field=tf.name,
                    issue=f"TS field '{tf.name}' has no matching Go json tag in '{go_struct.name}'",
                    severity="LOW",
                ))

    # Go ↔ DB comparison (match db_tag or camel_to_snake(name) → DB column)
    for go_struct in go_structs:
        struct_lower = go_struct.name.lower()
        # Try plural and singular table names
        table_candidates = [struct_lower, struct_lower + "s", struct_lower + "es",
                            struct_lower.replace("model", "").strip()]

        db_table = None
        db_name = None
        for tc in table_candidates:
            if tc in db_tables:
                db_table = db_tables[tc]
                db_name = tc
                break

        if not db_table:
            continue

        db_cols_lower = {c.lower() for c in db_table}

        for gf in go_struct.fields:
            # Use db_tag if present, otherwise camel_to_snake
            col_name = gf.db_tag if gf.db_tag else camel_to_snake(gf.name)
            if col_name.lower() not in db_cols_lower:
                mismatches.append(Mismatch(
                    entity=f"{go_struct.name} ↔ {db_name}",
                    layer="DB",
                    field=col_name,
                    issue=f"Go field '{gf.name}' → DB column '{col_name}' not found in table '{db_name}'",
                    severity="HIGH",
                ))

    return mismatches


def validate_permission_sync(
    be_perms: list[PermissionCheck],
    fe_perm_strings: set[str],
    fe_route_guards: list[str],
    db_tables: dict,
) -> list[Mismatch]:
    """Cross-reference permissions across BE middleware and FE route guards."""
    mismatches = []

    # Extract unique BE permission strings (excluding role checks)
    be_perm_strings = {p.perm_string for p in be_perms
                       if not p.perm_string.startswith("role:")}

    # BE-only permissions (defined in BE but never referenced in FE)
    be_only = be_perm_strings - fe_perm_strings
    for perm in sorted(be_only):
        mismatches.append(Mismatch(
            entity="permissions",
            layer="FE",
            field=perm,
            issue=f"BE permission '{perm}' has no matching FE PERMISSIONS constant",
            severity="LOW",
        ))

    # FE-only permissions (referenced in FE but not in BE)
    fe_only = fe_perm_strings - be_perm_strings
    for perm in sorted(fe_only):
        mismatches.append(Mismatch(
            entity="permissions",
            layer="BE",
            field=perm,
            issue=f"FE permission '{perm}' has no matching BE middleware check",
            severity="HIGH",
        ))

    # Check permissions table in DB
    if "permissions" in db_tables or "role_has_permissions" in db_tables:
        pass  # Permissions are in DB, would need to query live DB for values

    return mismatches


# ============================================================
# Report Generator
# ============================================================

SEVERITY_COLORS = {
    "CRITICAL": "\033[0;31m",
    "HIGH": "\033[1;31m",
    "MEDIUM": "\033[1;33m",
    "LOW": "\033[0;36m",
}
NC = "\033[0m"


def generate_report(
    go_structs: list[GoStruct],
    ts_interfaces: list[TSInterface],
    db_schema: dict,
    be_perms: list[PermissionCheck],
    fe_perms: set[str],
    fe_route_guards: list[str],
    model_mismatches: list[Mismatch],
    perm_mismatches: list[Mismatch],
) -> str:
    """Generate cross-repo audit report."""
    lines = [
        "=" * 70,
        "CROSS-REPO AUDIT REPORT",
        "=" * 70,
        "",
        f"BE Go structs:      {len(go_structs)}",
        f"FE TS interfaces:   {len(ts_interfaces)}",
        f"DB tables:          {db_schema.get('table_count', 0)}",
        f"DB columns:         {db_schema.get('total_columns', 0)}",
        f"BE permissions:     {len(be_perms)}",
        f"FE permissions:     {len(fe_perms)}",
        f"FE route guards:    {len(fe_route_guards)}",
        "",
    ]

    # --- Model Sync ---
    lines.extend([
        "-" * 70,
        "MODEL SYNC (Go ↔ TS ↔ DB)",
        "-" * 70,
    ])

    if not model_mismatches:
        lines.append("  ✅ No model field mismatches found")
    else:
        by_severity: dict[str, list[Mismatch]] = defaultdict(list)
        for m in model_mismatches:
            by_severity[m.severity].append(m)

        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            items = by_severity.get(sev, [])
            if items:
                color = SEVERITY_COLORS.get(sev, "")
                lines.append(f"\n  {color}[{sev}]{NC} {len(items)} mismatch(es)")
                for m in items:
                    lines.append(f"    {color}→{NC} {m.entity}: {m.issue}")

    lines.append("")

    # --- Permission Sync ---
    lines.extend([
        "-" * 70,
        "PERMISSION SYNC (BE middleware ↔ FE guards)",
        "-" * 70,
    ])

    be_perm_set = {p.perm_string for p in be_perms
                   if not p.perm_string.startswith("role:")}
    be_roles = {p.perm_string for p in be_perms
                if p.perm_string.startswith("role:")}

    lines.append(f"\n  BE permission strings: {sorted(be_perm_set)}")
    lines.append(f"\n  BE role guards: {sorted(be_roles)}")
    lines.append(f"\n  FE PERMISSIONS values: {sorted(fe_perms)}")

    if not perm_mismatches:
        lines.append("\n  ✅ All permissions match")
    else:
        for m in perm_mismatches:
            color = SEVERITY_COLORS.get(m.severity, "")
            lines.append(f"  {color}[{m.severity}]{NC} {m.issue}")

    lines.append("")

    # --- FE Route Guards ---
    lines.extend([
        "-" * 70,
        f"FE ROUTE GUARDS ({len(fe_route_guards)})",
        "-" * 70,
    ])
    for guard in fe_route_guards:
        lines.append(f"  → {guard}")

    lines.append("")

    # --- Summary ---
    total_issues = len(model_mismatches) + len(perm_mismatches)
    critical = sum(1 for m in model_mismatches + perm_mismatches
                   if m.severity == "CRITICAL")
    high = sum(1 for m in model_mismatches + perm_mismatches
               if m.severity == "HIGH")

    lines.extend([
        "-" * 70,
        "VERDICT",
        "-" * 70,
    ])

    if critical > 0:
        lines.append(f"  🔴 {critical} CRITICAL — fix before deploy")
    if high > 0:
        lines.append(f"  🟡 {high} HIGH — review before deploy")
    if total_issues == 0:
        lines.append("  🟢 FE/BE/DB in sync — no mismatches found")
    else:
        lines.append(f"  ℹ️  Total issues: {total_issues}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Cross-Repo Auditor — deep FE/BE/DB sync validation"
    )
    parser.add_argument(
        "--be", required=True, type=str,
        help="Backend directory (Go)"
    )
    parser.add_argument(
        "--fe", required=True, type=str,
        help="Frontend directory (Vue/TS)"
    )
    parser.add_argument(
        "--check",
        choices=["all", "models", "permissions"],
        default="all",
        help="What to check (default: all)"
    )

    args = parser.parse_args()

    be_dir = Path(args.be)
    fe_dir = Path(args.fe)

    if not be_dir.is_dir():
        print(f"❌ BE directory not found: {be_dir}")
        sys.exit(1)
    if not fe_dir.is_dir():
        print(f"❌ FE directory not found: {fe_dir}")
        sys.exit(1)

    # Banner
    print()
    print("=" * 70)
    print("  CROSS-REPO AUDITOR")
    print("=" * 70)

    # --- Parse BE ---
    print("\n📦 Parsing Go structs...")
    go_structs = parse_go_structs(be_dir)
    print(f"   Found {len(go_structs)} structs")

    print("\n📦 Parsing BE permissions...")
    be_perms = parse_be_permissions(be_dir)
    print(f"   Found {len(be_perms)} permission checks")

    # --- Parse FE ---
    print("\n📦 Parsing TS interfaces...")
    ts_interfaces = parse_ts_interfaces(fe_dir)
    print(f"   Found {len(ts_interfaces)} interfaces/types")

    print("\n📦 Parsing FE permissions...")
    fe_perms, fe_route_guards = parse_fe_permissions(fe_dir)
    print(f"   Found {len(fe_perms)} permission strings, "
          f"{len(fe_route_guards)} route guards")

    # --- Parse DB ---
    print("\n📦 Extracting DB schema...")
    db_schema = ra.extract_db_schema(str(be_dir))
    print(f"   Found {db_schema['table_count']} tables, "
          f"{db_schema['total_columns']} columns")

    # --- Validate ---
    model_mismatches = []
    perm_mismatches = []

    if args.check in ("all", "models"):
        print("\n🔍 Validating model sync (Go ↔ TS ↔ DB)...")
        model_mismatches = validate_model_sync(
            go_structs, ts_interfaces, db_schema.get("tables", {})
        )
        print(f"   Found {len(model_mismatches)} model mismatches")

    if args.check in ("all", "permissions"):
        print("\n🔍 Validating permission sync (BE ↔ FE)...")
        perm_mismatches = validate_permission_sync(
            be_perms, fe_perms, fe_route_guards, db_schema.get("tables", {})
        )
        print(f"   Found {len(perm_mismatches)} permission mismatches")

    # --- Report ---
    report = generate_report(
        go_structs, ts_interfaces, db_schema,
        be_perms, fe_perms, fe_route_guards,
        model_mismatches, perm_mismatches,
    )
    print(f"\n{report}")

    # Exit code
    total_high = sum(1 for m in model_mismatches + perm_mismatches
                     if m.severity in ("CRITICAL", "HIGH"))
    sys.exit(1 if total_high > 0 else 0)


if __name__ == "__main__":
    main()
