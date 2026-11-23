"""
Data Dictionary Generator and Schema Introspection for Oryva Planning.
Inspects Pydantic entity schemas and derives:
1. Markdown Data Dictionary (type, required/optional, allowed values, units, uniqueness, validation rule)
2. SQL DDL for SQLite & DuckDB
"""

from typing import Dict, Any, List
from pydantic.fields import FieldInfo
from oryva_planning.schema.entities import CORE_ENTITIES, ENTITY_RELATIONSHIPS


def generate_data_dictionary_rows() -> Dict[str, List[Dict[str, Any]]]:
    """Extract structured data dictionary metadata for all entities."""
    dictionary = {}

    for entity_name, model in CORE_ENTITIES.items():
        fields_info = []
        for field_name, field in model.model_fields.items():
            # Extract type name
            type_annotation = field.annotation
            type_str = getattr(type_annotation, "__name__", str(type_annotation))
            type_str = type_str.replace("typing.", "").replace("oryva_planning.schema.enums.", "")

            is_required = field.is_required()
            extra = field.json_schema_extra or {}
            is_pk = extra.get("pk", False)
            fk_ref = extra.get("fk", None)
            is_unique = extra.get("unique", False) or is_pk

            # Allowed values
            allowed_values = "Any valid type"
            if hasattr(type_annotation, "__members__"):
                allowed_values = ", ".join([e.value for e in type_annotation])
            elif field_name in ("approved", "is_active", "is_primary", "capacity_check_passed", "policy_check_passed"):
                allowed_values = "True, False"

            # Determine units
            units = "N/A"
            lower_name = field_name.lower()
            if "cost" in lower_name or "price" in lower_name:
                units = "USD"
            elif "qty" in lower_name or "capacity" in lower_name:
                units = "Units / Pieces"
            elif "days" in lower_name:
                units = "Days"
            elif "score" in lower_name or "impact" in lower_name or "rate" in lower_name:
                units = "Ratio / Score (0-1 or 0-100)"
            elif "week" in lower_name:
                units = "Week (YYYYWww)"
            elif "date" in lower_name:
                units = "Date (YYYY-MM-DD)"
            elif "ts" in lower_name or "created_at" in lower_name:
                units = "Timestamp ISO-8601"

            # Validation rule
            rules = []
            if is_pk:
                rules.append("PRIMARY KEY")
            if is_unique:
                rules.append("UNIQUE")
            if fk_ref:
                rules.append(f"FOREIGN KEY -> {fk_ref}")
            if not is_required:
                rules.append("NULLABLE")
            else:
                rules.append("NOT NULL")

            # Check metadata constraints (ge, le, min_length, pattern)
            for m in field.metadata:
                m_type = type(m).__name__
                if hasattr(m, "ge") and m.ge is not None:
                    rules.append(f"value >= {m.ge}")
                if hasattr(m, "gt") and m.gt is not None:
                    rules.append(f"value > {m.gt}")
                if hasattr(m, "le") and m.le is not None:
                    rules.append(f"value <= {m.le}")
                if hasattr(m, "pattern") and m.pattern is not None:
                    rules.append(f"regex: `{m.pattern}`")

            fields_info.append({
                "field_name": field_name,
                "type": type_str,
                "required": "Required" if is_required else "Optional",
                "allowed_values": allowed_values,
                "units": units,
                "uniqueness": "Unique" if is_unique else "Non-Unique",
                "validation_rule": "; ".join(rules),
                "description": field.description or ""
            })
        dictionary[entity_name] = fields_info

    return dictionary


def generate_markdown_data_dictionary() -> str:
    """Generate comprehensive GitHub Flavored Markdown data dictionary."""
    dict_data = generate_data_dictionary_rows()
    lines = [
        "# Oryva AI - Comprehensive Data Dictionary",
        "",
        "This data dictionary is derived directly from the single-source-of-truth Pydantic schema layer in `oryva_planning.schema.entities`.",
        "",
        "## Table of Contents",
        ""
    ]

    for entity_name in dict_data.keys():
        lines.append(f"- [{entity_name}](#{entity_name.lower()})")

    lines.append("")
    lines.append("## Entity Relationship Summary")
    lines.append("")
    lines.append("| Parent Entity | Child Entity | Cardinality | Relationship Role |")
    lines.append("|---|---|---|---|")
    for rel in ENTITY_RELATIONSHIPS:
        lines.append(f"| `{rel['parent']}` | `{rel['child']}` | {rel['cardinality']} | {rel['type']} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    for entity_name, fields in dict_data.items():
        lines.append(f"### {entity_name}")
        lines.append("")
        lines.append("| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |")
        lines.append("|---|---|---|---|---|---|---|")
        for f in fields:
            desc_rule = f"**Rule:** {f['validation_rule']}<br>**Desc:** {f['description']}"
            lines.append(f"| `{f['field_name']}` | `{f['type']}` | {f['required']} | {f['units']} | {f['uniqueness']} | `{f['allowed_values']}` | {desc_rule} |")
        lines.append("")

    return "\n".join(lines)


def generate_sql_ddl(dialect: str = "sqlite") -> str:
    """Generate SQL CREATE TABLE statements for all registered entities."""
    sql_statements = []
    dict_data = generate_data_dictionary_rows()

    for entity_name, fields in dict_data.items():
        col_defs = []
        pk_cols = []
        for f in fields:
            col_type = "TEXT"
            if "int" in f["type"].lower():
                col_type = "INTEGER"
            elif "float" in f["type"].lower():
                col_type = "REAL"
            elif "bool" in f["type"].lower():
                col_type = "INTEGER"

            constraints = []
            if "PRIMARY KEY" in f["validation_rule"]:
                pk_cols.append(f["field_name"])
            if "NOT NULL" in f["validation_rule"]:
                constraints.append("NOT NULL")

            col_defs.append(f"    {f['field_name']} {col_type} {' '.join(constraints)}".strip())

        if pk_cols:
            col_defs.append(f"    PRIMARY KEY ({', '.join(pk_cols)})")

        stmt = f"CREATE TABLE IF NOT EXISTS {entity_name.lower()} (\n" + ",\n".join(col_defs) + "\n);"
        sql_statements.append(stmt)

    return "\n\n".join(sql_statements)
