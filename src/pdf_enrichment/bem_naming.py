"""
BEM Naming Engine for PDF Form Fields

Generates BEM-style field names following financial services conventions.
"""

import logging
import re
from typing import Dict, List, Optional

from .field_types import FormField, FieldType, GROUPED_FIELD_TYPES

logger = logging.getLogger(__name__)


class BEMNamingEngine:
    """Engine for generating BEM-style field names."""
    
    def __init__(self) -> None:
        self.reserved_words = {
            "class", "id", "name", "type", "value", "checked", "selected",
            "disabled", "readonly", "required", "multiple", "hidden"
        }
        
        # Common abbreviations to expand
        self.abbreviations = {
            "addr": "address",
            "dob": "date-of-birth",
            "ssn": "social-security-number",
            "tel": "telephone",
            "ph": "phone",
            "num": "number",
            "qty": "quantity",
            "amt": "amount",
            "pct": "percent",
            "desc": "description",
            "info": "information",
            "req": "request",
            "sub": "submission",
            "auth": "authorization",
            "sig": "signature",
            "ben": "beneficiary",
            "cont": "contingent",
            "prim": "primary",
            "sec": "secondary",
            "alt": "alternative",
            "temp": "temporary",
            "perm": "permanent",
            "curr": "current",
            "prev": "previous",
            "add": "additional",
            "opt": "optional",
            "min": "minimum",
            "max": "maximum",
            "avg": "average",
            "tot": "total",
            "fed": "federal",
            "st": "state",
            "loc": "local",
            "intl": "international",
            "dom": "domestic",
            "bus": "business",
            "pers": "personal",
            "prof": "professional",
            "med": "medical",
            "leg": "legal",
            "fin": "financial",
            "ins": "insurance",
            "inv": "investment",
            "ret": "retirement",
            "comp": "compensation",
            "sal": "salary",
            "wage": "wages",
            "inc": "income",
            "exp": "expenses",
            "ded": "deduction",
            "cred": "credit",
            "deb": "debit",
            "bal": "balance",
            "pymt": "payment",
            "dep": "deposit",
            "with": "withdrawal",
            "trans": "transaction",
            "acct": "account",
            "chk": "checking",
            "sav": "savings",
            "cd": "certificate-deposit",
            "ira": "individual-retirement-account",
            "roth": "roth-ira",
            "trad": "traditional",
            "conv": "conventional",
            "mort": "mortgage",
            "cc": "credit-card",
            "dc": "debit-card",
            "ach": "automated-clearing-house",
            "wire": "wire-transfer",
            "eft": "electronic-funds-transfer",
            "dd": "direct-deposit",
            "ap": "automatic-payment",
            "bil": "billing",
            "inv": "invoice",
            "stmt": "statement",
            "conf": "confirmation",
            "ref": "reference",
            "yr": "year",
            "mo": "month",
            "wk": "week",
            "dy": "day",
            "hr": "hour",
            "est": "estimated",
            "act": "actual",
            "proj": "projected",
            "bud": "budget",
            "plan": "planned",
            "sched": "scheduled",
            "due": "due-date",
            "exp": "expiration",
            "eff": "effective",
            "start": "start-date",
            "end": "end-date",
            "term": "termination",
            "canc": "cancellation",
            "ren": "renewal",
            "ext": "extension",
            "mod": "modification",
            "upd": "update",
            "chg": "change",
            "corr": "correction",
            "rev": "revision",
            "ver": "version",
            "stat": "status",
            "cond": "condition",
            "rsn": "reason",
            "purp": "purpose",
            "obj": "objective",
            "targ": "target",
            "lim": "limit",
            "res": "restriction",
            "exc": "exception",
            "incl": "including",
            "excl": "excluding",
            "app": "applicable",
            "tbd": "to-be-determined",
            "tbc": "to-be-confirmed",
            "misc": "miscellaneous",
            "gen": "general",
            "spec": "specific",
            "det": "detailed",
            "sum": "summary",
            "ovr": "overview",
            "brf": "brief",
            "comp": "complete",
            "part": "partial",
            "full": "full",
            "net": "net",
            "gross": "gross",
            "pre": "before",
            "post": "after",
            "dur": "during",
            "vol": "voluntary",
            "mand": "mandatory",
            "rec": "recommended",
            "sug": "suggested",
            "nec": "necessary",
            "pref": "preferred",
            "def": "default",
            "std": "standard",
            "cust": "custom",
            "auto": "automatic",
            "man": "manual",
            "sys": "system",
            "usr": "user",
            "adm": "administrator",
            "mgr": "manager",
            "sup": "supervisor",
            "dir": "director",
            "exec": "executive",
            "ceo": "chief-executive-officer",
            "cfo": "chief-financial-officer",
            "cto": "chief-technology-officer",
            "hr": "human-resources",
            "it": "information-technology",
            "qa": "quality-assurance",
            "rd": "research-development",
            "mkt": "marketing",
            "sls": "sales",
            "svc": "service",
            "ops": "operations",
            "prod": "production",
            "dev": "development",
            "test": "testing",
            "demo": "demonstration",
            "trial": "trial",
            "beta": "beta",
            "alpha": "alpha",
            "rc": "release-candidate",
            "rel": "release",
            "build": "build",
            "pkg": "package",
            "dist": "distribution",
            "inst": "installation",
            "cfg": "configuration",
            "set": "settings",
            "prop": "properties",
            "attr": "attributes",
            "meta": "metadata",
            "doc": "documentation",
            "help": "help",
            "msg": "message",
            "note": "note",
            "warn": "warning",
            "err": "error",
            "log": "log",
            "dbg": "debug",
            "trace": "trace",
            "perf": "performance",
            "bench": "benchmark",
            "mock": "mock",
            "stub": "stub",
            "fake": "fake",
            "sim": "simulation",
            "emu": "emulation",
            "virt": "virtual",
            "real": "real",
            "live": "live",
            "stage": "staging",
            "local": "local",
            "remote": "remote",
            "cloud": "cloud",
            "hybrid": "hybrid",
            "pub": "public",
            "priv": "private",
            "sec": "secure",
            "enc": "encrypted",
            "dec": "decrypted",
            "arch": "archived",
            "backup": "backup",
            "rest": "restore",
            "sync": "synchronize",
            "async": "asynchronous",
            "batch": "batch",
            "stream": "stream",
            "queue": "queue",
            "stack": "stack",
            "heap": "heap",
            "pool": "pool",
            "cache": "cache",
            "buf": "buffer",
            "mem": "memory",
            "disk": "disk",
            "net": "network",
            "conn": "connection",
            "sess": "session",
            "authz": "authorization",
            "perm": "permission",
            "role": "role",
            "grp": "group",
            "prof": "profile",
            "sett": "settings",
            "env": "environment",
            "var": "variable",
            "const": "constant",
            "param": "parameter",
            "arg": "argument",
            "val": "value",
            "res": "result",
            "ret": "return",
            "out": "output",
            "in": "input",
            "resp": "response",
            "data": "data",
            "field": "field",
            "col": "column",
            "row": "row",
            "rec": "record",
            "ent": "entity",
            "obj": "object",
            "inst": "instance",
            "ptr": "pointer",
            "loc": "location",
            "pos": "position",
            "idx": "index",
            "key": "key",
            "pair": "pair",
            "map": "mapping",
            "dict": "dictionary",
            "list": "list",
            "arr": "array",
            "vec": "vector",
            "coll": "collection",
            "seq": "sequence",
            "ser": "series",
            "chain": "chain",
            "link": "link",
            "node": "node",
            "elem": "element",
            "item": "item",
            "piece": "piece",
            "frag": "fragment",
            "chunk": "chunk",
            "block": "block",
            "sect": "section",
            "seg": "segment",
            "div": "division",
            "cat": "category",
            "cls": "class",
            "kind": "kind",
            "sort": "sort",
            "ord": "order",
            "rank": "rank",
            "lvl": "level",
            "tier": "tier",
            "grade": "grade",
            "score": "score",
            "rate": "rate",
            "ratio": "ratio",
            "frac": "fraction",
            "int": "integer",
            "cnt": "count",
            "vol": "volume",
            "cap": "capacity",
            "med": "median",
            "vs": "versus",
            "v": "versus",
            "per": "per",
            "ea": "each",
            "ind": "individual",
            "sep": "separate",
            "comb": "combined",
            "joint": "joint",
            "shr": "shared",
            "comm": "common",
            "corp": "corporate",
            "org": "organization",
            "co": "company",
            "llc": "limited-liability-company",
            "lp": "limited-partnership",
            "gp": "general-partnership",
            "sole": "sole-proprietorship",
            "gov": "government",
            "mun": "municipal",
            "cnty": "county",
            "twn": "town",
            "vil": "village",
            "ward": "ward",
            "prec": "precinct",
            "zone": "zone",
            "area": "area",
            "reg": "region",
            "terr": "territory",
            "prov": "province",
            "cty": "country",
            "nat": "national",
            "glob": "global",
            "univ": "universal",
            "world": "worldwide",
            "earth": "earthwide",
            "plan": "planetary",
            "gal": "galactic",
            "cosm": "cosmic",
            "inf": "infinite",
            "unlim": "unlimited",
            "bound": "bounded",
            "fin": "finite",
            "indef": "indefinite",
            "abs": "abstract",
            "conc": "concrete",
            "phys": "physical",
            "dig": "digital",
            "ana": "analog",
            "bin": "binary",
            "hex": "hexadecimal",
            "oct": "octal",
            "dec": "decimal",
            "flt": "floating-point",
            "fix": "fixed-point",
            "pos": "positive",
            "neg": "negative",
            "zero": "zero",
            "null": "null",
            "empty": "empty",
            "blank": "blank",
            "void": "void",
            "none": "none",
            "any": "any",
            "all": "all",
            "some": "some",
            "few": "few",
            "many": "many",
            "most": "most",
            "sev": "several",
            "mult": "multiple",
            "sing": "single",
            "uni": "unique",
            "dup": "duplicate",
            "trip": "triplicate",
            "quad": "quadruple",
            "quint": "quintuple",
            "sext": "sextuple",
            "sept": "septuple",
            "oct": "octuple",
            "non": "nonuple",
            "cent": "centuple",
            "mil": "milluple",
            "bil": "billuple",
            "tril": "trilluple",
        }
    
    def generate_bem_name(
        self, field: FormField, section: str, context: Dict[str, any]
    ) -> str:
        """Generate a BEM-style name for a form field."""
        try:
            # Start with the section as block
            block = self._sanitize_block_name(section)
            
            # Generate element name from field info
            element = self._generate_element_name(field)
            
            # Generate modifier if needed
            modifier = self._generate_modifier(field, context)
            
            # Combine into BEM format
            if field.type in GROUPED_FIELD_TYPES and field.type == FieldType.RADIO_GROUP:
                # Radio groups get --group suffix
                bem_name = f"{block}_{element}--group"
            elif modifier:
                bem_name = f"{block}_{element}__{modifier}"
            else:
                bem_name = f"{block}_{element}"
            
            # Ensure uniqueness
            bem_name = self._ensure_uniqueness(bem_name, context.get("existing_names", []))
            
            return bem_name
            
        except Exception as e:
            logger.warning(f"Error generating BEM name for {field.api_name}: {e}")
            return self._sanitize_field_name(field.api_name)
    
    def _sanitize_block_name(self, section: str) -> str:
        """Sanitize section name for use as BEM block."""
        if not section or section == "unknown":
            return "general"
        
        # Convert to lowercase and replace spaces/underscores with hyphens
        sanitized = section.lower().replace("_", "-").replace(" ", "-")
        
        # Remove non-alphanumeric characters except hyphens
        sanitized = re.sub(r'[^a-z0-9-]', '', sanitized)
        
        # Remove multiple consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        
        return sanitized or "general"
    
    def _generate_element_name(self, field: FormField) -> str:
        """Generate element name from field information."""
        # Start with the field label if available
        if field.label and field.label.strip():
            element = field.label.strip()
        else:
            # Fall back to API name
            element = field.api_name
        
        # Clean up the element name
        element = self._sanitize_field_name(element)
        
        # Expand common abbreviations
        element = self._expand_abbreviations(element)
        
        # Remove common prefixes that don't add value
        element = re.sub(r'^(input|field|text|data|info|value)-?', '', element)
        
        return element or "field"
    
    def _generate_modifier(self, field: FormField, context: Dict[str, any]) -> Optional[str]:
        """Generate modifier for field variations."""
        # Check if this is a radio button (not group)
        if field.type == FieldType.RADIO_BUTTON:
            # Extract option value from field name
            option_match = re.search(r'(option|choice|select)[-_]?(\w+)', field.api_name, re.IGNORECASE)
            if option_match:
                return self._sanitize_field_name(option_match.group(2))
        
        # Check for common modifiers in field name
        modifiers = {
            "gross": "gross",
            "net": "net",
            "pretax": "pretax",
            "posttax": "posttax",
            "monthly": "monthly",
            "yearly": "yearly",
            "annual": "annual",
            "quarterly": "quarterly",
            "weekly": "weekly",
            "daily": "daily",
            "primary": "primary",
            "secondary": "secondary",
            "contingent": "contingent",
            "alternate": "alternate",
            "current": "current",
            "previous": "previous",
            "temporary": "temporary",
            "permanent": "permanent",
            "optional": "optional",
            "required": "required",
            "minimum": "minimum",
            "maximum": "maximum",
            "total": "total",
            "subtotal": "subtotal",
            "first": "first",
            "last": "last",
            "middle": "middle",
            "initial": "initial",
            "suffix": "suffix",
            "prefix": "prefix",
            "start": "start",
            "end": "end",
            "begin": "begin",
            "finish": "finish",
            "open": "open",
            "close": "close",
            "enable": "enable",
            "disable": "disable",
            "active": "active",
            "inactive": "inactive",
            "visible": "visible",
            "hidden": "hidden",
            "public": "public",
            "private": "private",
            "internal": "internal",
            "external": "external",
            "local": "local",
            "remote": "remote",
            "online": "online",
            "offline": "offline",
            "connected": "connected",
            "disconnected": "disconnected",
        }
        
        field_name_lower = field.api_name.lower()
        for keyword, modifier in modifiers.items():
            if keyword in field_name_lower:
                return modifier
        
        return None
    
    def _sanitize_field_name(self, name: str) -> str:
        """Sanitize field name to BEM-compliant format."""
        # Convert to lowercase
        sanitized = name.lower()
        
        # Replace spaces, underscores, and other separators with hyphens
        sanitized = re.sub(r'[_\s]+', '-', sanitized)
        
        # Remove non-alphanumeric characters except hyphens
        sanitized = re.sub(r'[^a-z0-9-]', '', sanitized)
        
        # Remove multiple consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        
        # Remove leading numbers
        sanitized = re.sub(r'^[0-9-]+', '', sanitized)
        
        return sanitized or "field"
    
    def _expand_abbreviations(self, name: str) -> str:
        """Expand common abbreviations in field names."""
        # Split name into parts
        parts = name.split('-')
        
        # Expand each part
        expanded_parts = []
        for part in parts:
            if part in self.abbreviations:
                expanded_parts.append(self.abbreviations[part])
            else:
                expanded_parts.append(part)
        
        return '-'.join(expanded_parts)
    
    def _ensure_uniqueness(self, bem_name: str, existing_names: List[str]) -> str:
        """Ensure BEM name is unique by adding numeric suffix if needed."""
        if bem_name not in existing_names:
            return bem_name
        
        # Try adding numeric suffixes
        counter = 2
        while f"{bem_name}-{counter}" in existing_names:
            counter += 1
        
        return f"{bem_name}-{counter}"
    
    def validate_bem_name(self, name: str) -> bool:
        """Validate that a name follows BEM conventions."""
        # Check basic BEM pattern
        if not re.match(r'^[a-z][a-z0-9-]*_[a-z][a-z0-9-]*(?:__[a-z][a-z0-9-]*|--group)?$', name):
            return False
        
        # Check for reserved words
        parts = name.replace('__', '_').replace('--', '_').split('_')
        if any(part in self.reserved_words for part in parts):
            return False
        
        return True
