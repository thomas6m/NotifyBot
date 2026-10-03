#!/usr/bin/env python3
"""
notification_inventory.py - Child script for the Parallel Orchestrator

Collects the users of EVERY group mapped to each namespace and writes
notification.csv:
    time, cluster, namespace, env, appid, ids, groups

Environment is derived from the LAST character of the cluster name:
    *p -> prod    *u -> uat    *d -> dev    (anything else is rejected)

Which groups count as "mapped to a namespace" (--group-source):
    rolebindings  every Group subject of every RoleBinding in the namespace,
                  whatever its name or role (admin, edit, view, custom roles)
    naming        only app_ecs_{env}_{namespace}_edit / _view (old behaviour)
    both          union of the two (default) - nothing the old logic found is lost
Users bound DIRECTLY to the namespace (RoleBinding subject kind=User) are
included too, unless --groups-only is given. ServiceAccounts and system:*
identities are never treated as people.

Optional narrowing:
    --roles admin,edit,view        only bindings to these roles count
    --exclude-groups REGEX         ignore matching groups, e.g. platform-admin
                                   groups bound into every namespace

Group members are expanded from one `oc get group` call and the bindings come
from one `oc get rolebinding --all-namespaces` call, so the whole cluster still
costs a fixed number of API calls. If the login may not list RoleBindings
cluster-wide, the run falls back to the naming convention with a warning.

Only real person ids are kept. A user name must contain an SOEID - two letters
followed by five digits - optionally with a few extra characters before or after
it (e.g. "xab12345", "ab12345_adm", "CN=ab12345,OU=Users"). The SOEID itself is
used: "ab12345_adm" -> ab12345@citi.com. Names without one ("kube:admin",
"admin", "svc-deploy", "john.smith@...") are rejected and logged, so they never
become e-mail addresses. --id-pattern changes the rule ('' = keep every name,
the old behaviour). Namespaces with no valid users are skipped. The output file is only
created when at least one row exists. The "groups" column lists the groups
whose members were used, for auditing.

Base folder resolution (used for .secrets, logs, inventory, output,
.exec_homes):
    1. -b / --base-folder on the command line
    2. the current working directory

Data is read via the `oc` CLI (oc get ns / oc get group) against a
per-cluster login session stored under an isolated exec_home, so parallel
runs against different clusters do not clobber each other's kubeconfig.
"""

import argparse
import base64
import csv
import getpass
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Dict, List, Optional, Set, Tuple

import pytz
from cryptography.fernet import Fernet


CSV_COLUMNS = ["time", "cluster", "namespace", "env", "appid", "ids", "groups"]
GROUPS_SEPARATOR = ";"

# Where a namespace's groups come from (see module docstring).
GROUP_SOURCES        = ("rolebindings", "naming", "both")
DEFAULT_GROUP_SOURCE = "both"
NAMING_SUFFIXES      = ("edit", "view")
DEFAULT_EXCLUDE_GROUPS = r"^system:"

# Subject names that are not people (service accounts, system identities).
# Skipped before the id rule, so e.g. "system:serviceaccount:ns-ab12345:sa"
# can never yield a bogus "ab12345".
NON_PERSON_PREFIXES = ("system:",)

# A person's id (SOEID): two letters + five digits. Letters or other characters
# may come before/after it; another digit may not, so a 6+ digit run such as
# "ab123456" is not mistaken for "ab12345". The matched text is the id used.
DEFAULT_ID_PATTERN = r"(?<!\d)[A-Za-z]{2}\d{5}(?!\d)"
REJECTED_LOG_EXAMPLES = 10
OUTPUT_FILENAME = "notification.csv"

SGT_TZ = pytz.timezone("Asia/Singapore")

# Namespaces are included only when the name starts with one of these prefixes.
NAMESPACE_PREFIXES = ("gcb", "pbwm", "icg", "gcg", "cti", "cto")
NAMESPACE_PREFIX_RE = re.compile(r"^(" + "|".join(NAMESPACE_PREFIXES) + r")")

# Cluster-name last character -> environment token used in group names.
ENV_BY_SUFFIX = {"p": "prod", "u": "uat", "d": "dev"}

ID_DOMAIN = "@citi.com"

DEFAULT_USERNAME       = "user1"
DEFAULT_RETRIES        = 3
RETRY_SLEEP_SECONDS    = 2
ENV_FERNET_KEY         = "ORCHESTRATOR_FERNET_KEY"
ENV_ENCRYPTED_PASSWORD = "ORCHESTRATOR_ENCRYPTED_PASSWORD"


def resolve_base_folder(cli_value: Optional[Path]) -> Path:
    """Base folder: CLI value first, otherwise the current working directory.

    Resolved to an absolute path so it stays valid regardless of any later
    directory changes.
    """
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    return Path.cwd().resolve()


# --------------------------------------------------------------------------- #
# oc helpers - every call runs against an isolated exec_home / KUBECONFIG
# --------------------------------------------------------------------------- #
def _oc_env(exec_home: Path) -> dict:
    env = os.environ.copy()
    env["HOME"]       = str(exec_home)
    env["KUBECONFIG"] = str(exec_home / ".kube" / "config")
    return env


def _oc_login_secure(api_url: str, username: str, password: str,
                     exec_home: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["oc", "login", api_url, "-u", username, "--insecure-skip-tls-verify"],
        input=f"{password}\n",
        check=True, capture_output=True, text=True, env=_oc_env(exec_home),
    )


def _oc_login_token(api_url: str, token: str,
                    exec_home: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["oc", "login", api_url, f"--token={token}", "--insecure-skip-tls-verify"],
        check=True, capture_output=True, text=True, env=_oc_env(exec_home),
    )


def _oc_whoami_token(exec_home: Path) -> str:
    return subprocess.run(
        ["oc", "whoami", "-t"],
        check=True, capture_output=True, text=True, env=_oc_env(exec_home),
    ).stdout.strip()


def _oc_get_json(args: List[str], exec_home: Path) -> dict:
    """Run `oc <args> -o json` and return the parsed object.

    stderr is captured so a failure (e.g. 'forbidden') can be reported.
    """
    res = subprocess.run(
        ["oc", *args, "-o", "json"],
        capture_output=True, text=True, env=_oc_env(exec_home),
    )
    if res.returncode != 0:
        raise subprocess.CalledProcessError(res.returncode, res.args,
                                            res.stdout, res.stderr)
    return json.loads(res.stdout)


def cluster_to_env(cluster_name: str) -> Optional[str]:
    """prod/uat/dev from the cluster's last character, or None if invalid."""
    if not cluster_name:
        return None
    return ENV_BY_SUFFIX.get(cluster_name[-1].lower())


# Same precedence as the Splunk rex/eval:
#   \d{6,}  -> appid_6plus   (a run of 6 or more digits, taken whole)
#   \d{4,5} -> appid_4to5    (a run of 4-5 digits)
#   else    -> "NA"
APPID_6PLUS_RE = re.compile(r"\d{6,}")
APPID_4TO5_RE  = re.compile(r"\d{4,5}")


def extract_appid(namespace: str) -> str:
    """Extract the appid from a namespace, preferring a 6+ digit run,
    then a 4-5 digit run, else 'NA'. Mirrors the Splunk logic:
        rex "(?P<appid_6plus>\\d{6,})"
        rex "(?P<appid_4to5>\\d{4,5})"
        eval appid = case(isnotnull(appid_6plus), appid_6plus,
                          isnotnull(appid_4to5),  appid_4to5, 1=1, "NA")
    """
    m = APPID_6PLUS_RE.search(namespace or "")
    if m:
        return m.group(0)
    m = APPID_4TO5_RE.search(namespace or "")
    if m:
        return m.group(0)
    return "NA"


def get_sgt_execution_time() -> int:
    return int(datetime.now(SGT_TZ).timestamp())


@dataclass
class ClusterMetrics:
    cluster_name:       str
    start_time:         float
    end_time:           float = 0.0
    success:            bool  = False
    auth_method:        str   = ""
    total_oc_calls:     int   = 0
    auth_attempts:      int   = 0
    namespaces_seen:    int   = 0
    namespaces_written: int   = 0
    groups_fetched:     int   = 0
    rolebindings_fetched: int = 0
    group_source_used:  str   = ""
    groups_not_found:   int   = 0   # bound groups with no Group object (no members)
    rejected_names: Set[str] = field(default_factory=set)  # user names without an SOEID
    error_count:        int   = 0
    final_attempt:      int   = 0
    error_messages: List[str] = field(default_factory=list)

    @property
    def processing_time_seconds(self) -> float:
        return self.end_time - self.start_time if self.end_time > 0 else 0.0

    def add_error(self, msg: str) -> None:
        self.error_messages.append(msg)
        self.error_count += 1


def detect_orchestrator_execution() -> bool:
    return bool(os.environ.get(ENV_FERNET_KEY) and os.environ.get(ENV_ENCRYPTED_PASSWORD))


class NotificationInventoryScript:

    def __init__(self, base_folder: Path,
                 group_source: str = DEFAULT_GROUP_SOURCE,
                 roles: Optional[Set[str]] = None,
                 exclude_groups: Optional[str] = DEFAULT_EXCLUDE_GROUPS,
                 include_direct_users: bool = True,
                 id_pattern: Optional[str] = DEFAULT_ID_PATTERN):
        self.logger: Optional[logging.Logger] = None
        self.exec_home: Optional[Path]        = None
        self.base_folder: Path                = base_folder
        self.group_source         = group_source
        self.roles                = {r.lower() for r in roles} if roles else None
        self.exclude_groups_re    = re.compile(exclude_groups) if exclude_groups else None
        self.include_direct_users = include_direct_users
        self.id_re                = re.compile(id_pattern) if id_pattern else None

    # ---------------------------------------------------------------- setup
    def setup_logging(self, base_paths: Dict, log_level: str = "INFO",
                      cluster_name: Optional[str] = None,
                      mode: Optional[str] = None) -> None:
        log_dir: Path = base_paths["log_dir"]
        log_dir.mkdir(parents=True, exist_ok=True)
        script_name = Path(sys.argv[0]).stem
        if mode == "single" and cluster_name:
            log_file = log_dir / f"{script_name}_{cluster_name}_{int(time.time())}_log.txt"
        else:
            log_file = log_dir / f"{script_name}_log.txt"
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Log file: {log_file}")

    def setup_execution_home(self, base_folder: Path) -> Path:
        d = base_folder / ".exec_homes" / f"exec_{os.getpid()}_{int(time.time())}"
        d.mkdir(parents=True, exist_ok=True)
        (d / ".kube").mkdir(parents=True, exist_ok=True)
        return d

    def cleanup_execution_home(self, exec_home: Path) -> None:
        try:
            if exec_home and exec_home.exists():
                shutil.rmtree(exec_home)
        except Exception:
            pass

    def build_api_url(self, cluster_name: str) -> str:
        # Adjust this template to your real API endpoint scheme.
        return f"https://api.{cluster_name}.example.com:6443"

    def get_password(self, base_paths: Dict, cluster_count: int) -> Optional[str]:
        if os.environ.get(ENV_FERNET_KEY) and os.environ.get(ENV_ENCRYPTED_PASSWORD):
            try:
                key = base64.b64decode(os.environ[ENV_FERNET_KEY])
                enc = base64.b64decode(os.environ[ENV_ENCRYPTED_PASSWORD])
                return Fernet(key).decrypt(enc).decode()
            except Exception:
                pass
        key_file = base_paths["key_file"]
        pwd_file = base_paths["password_file"]
        if key_file.exists() and pwd_file.exists():
            try:
                return Fernet(key_file.read_bytes()).decrypt(pwd_file.read_bytes()).decode()
            except Exception:
                pass
        if cluster_count == 1:
            return getpass.getpass("Enter password: ")
        return None

    # ------------------------------------------------------------- oc access
    def get_token(self, api_url: str, username: str, password: Optional[str],
                  token: Optional[str], metrics: ClusterMetrics) -> Optional[str]:
        """Authenticate against the cluster and return the session token.

        Same logic as the route script's get_token: `oc login` into the
        isolated exec_home, then `oc whoami -t` to read the session token,
        with the password redacted from any error output. The login also
        establishes the kubeconfig that the subsequent `oc get` calls use
        (the route script consumed the token over HTTP; here it additionally
        backs the `oc get` session, so a provided --token is applied with
        `oc login --token` rather than used as a bare bearer).
        """
        try:
            if token:
                _oc_login_token(api_url, token, self.exec_home)
                metrics.auth_method = "token"
            else:
                _oc_login_secure(api_url, username, password, self.exec_home)
                metrics.auth_method = "password"
            metrics.total_oc_calls += 1
            metrics.auth_attempts  += 1

            session_token = _oc_whoami_token(self.exec_home)
            metrics.total_oc_calls += 1

            if not session_token:
                error_msg = "Authentication failed: empty token from 'oc whoami -t'"
                metrics.add_error(error_msg)
                self.logger.error(error_msg)
                return None

            self.logger.info(f"Successfully authenticated ({metrics.auth_method})")
            return session_token

        except subprocess.CalledProcessError as e:
            err = e.stderr if isinstance(e.stderr, str) else (
                e.stderr.decode() if e.stderr else str(e)
            )
            if password:
                err = err.replace(password, "***REDACTED***")
            error_msg = f"Authentication failed: {err.strip()}"
            metrics.add_error(error_msg)
            self.logger.error("Authentication failed")
            return None
        except Exception as exc:
            error_msg = f"Authentication failed: {type(exc).__name__}"
            metrics.add_error(error_msg)
            self.logger.error(error_msg)
            return None

    def list_namespaces(self, metrics: ClusterMetrics,
                        all_namespaces: bool = False) -> List[str]:
        """Namespace names from the cluster.

        By default only names matching the prefix allow-list are returned;
        with all_namespaces=True every namespace on the cluster is returned
        (the prefix filter is skipped).
        """
        data = _oc_get_json(["get", "ns"], self.exec_home)
        metrics.total_oc_calls += 1
        names = [
            item.get("metadata", {}).get("name", "")
            for item in data.get("items", [])
            if item.get("metadata", {}).get("name", "")
        ]
        if all_namespaces:
            return names
        return [n for n in names if NAMESPACE_PREFIX_RE.match(n)]

    def fetch_all_groups(self, metrics: ClusterMetrics) -> Dict[str, List[str]]:
        """One `oc get group` call -> {group_name: [users]} for in-memory lookup.

        Fetching every group once and matching names in memory is far cheaper
        than a get-per-namespace: the whole cluster costs a single API call
        regardless of how many namespaces match.
        """
        data = _oc_get_json(["get", "group"], self.exec_home)
        metrics.total_oc_calls += 1
        groups: Dict[str, List[str]] = {}
        for item in data.get("items", []):
            name = item.get("metadata", {}).get("name", "")
            if name:
                groups[name] = item.get("users") or []
        metrics.groups_fetched = len(groups)
        return groups

    def fetch_namespace_bindings(self, metrics: ClusterMetrics
                                 ) -> Dict[str, List[Tuple[str, str, str]]]:
        """One `oc get rolebinding -A` call -> {namespace: [(kind, name, role)]}.

        kind is the subject kind (Group / User / ServiceAccount), role is the
        RoleBinding's roleRef name (admin, edit, view, or a custom role).
        """
        data = _oc_get_json(["get", "rolebinding", "--all-namespaces"], self.exec_home)
        metrics.total_oc_calls += 1
        bindings: Dict[str, List[Tuple[str, str, str]]] = {}
        count = 0
        for item in data.get("items", []):
            ns = item.get("metadata", {}).get("namespace", "")
            role = (item.get("roleRef") or {}).get("name", "")
            if not ns:
                continue
            count += 1
            for subj in item.get("subjects") or []:
                kind, name = subj.get("kind", ""), subj.get("name", "")
                if kind and name:
                    bindings.setdefault(ns, []).append((kind, name, role))
        metrics.rolebindings_fetched = count
        return bindings

    @staticmethod
    def _is_person(name: str) -> bool:
        return bool(name) and not name.startswith(NON_PERSON_PREFIXES)

    def extract_id(self, name: str) -> Optional[str]:
        """E-mail id for a user name, or None when it is not a person's id.

        With the default rule the SOEID inside the name is used, lower-cased:
        "AB12345" / "xab12345" / "ab12345_adm" / "ab12345@citi.com" ->
        "ab12345@citi.com". With --id-pattern '' the name is kept as before
        (@citi.com appended unless it already contains '@').
        """
        name = name.strip()
        if not self._is_person(name):
            return None
        if self.id_re is None:
            return name if "@" in name else f"{name}{ID_DOMAIN}"
        m = self.id_re.search(name)
        return f"{m.group(0).lower()}{ID_DOMAIN}" if m else None

    def access_for_namespace(self, namespace: str, env: str,
                             groups: Dict[str, List[str]],
                             bindings: Optional[Dict[str, List[Tuple[str, str, str]]]],
                             metrics: ClusterMetrics) -> Tuple[List[str], List[str]]:
        """(ids, group_names) for one namespace.

        Groups come from the namespace's RoleBindings and/or the
        app_ecs_{env}_{namespace}_{edit|view} naming convention (see
        --group-source). Group members are expanded from the in-memory group
        lookup; direct User subjects are added as-is. `bindings` is None when
        RoleBindings could not be read (naming convention only).
        """
        group_names: Set[str] = set()
        users: Set[str] = set()

        if bindings is not None and self.group_source in ("rolebindings", "both"):
            for kind, name, role in bindings.get(namespace, ()):
                if self.roles is not None and role.lower() not in self.roles:
                    continue
                if kind == "Group":
                    group_names.add(name)
                elif kind == "User" and self.include_direct_users:
                    users.add(name)
                # ServiceAccount subjects are not people - ignored

        if bindings is None or self.group_source in ("naming", "both"):
            for suffix in NAMING_SUFFIXES:
                name = f"app_ecs_{env}_{namespace}_{suffix}"
                if name in groups:
                    group_names.add(name)

        ids: Set[str] = set()

        def add(user_name: str) -> bool:
            uid = self.extract_id(user_name)
            if uid:
                ids.add(uid)
                return True
            if self._is_person(user_name.strip()):   # system:* is skipped silently
                metrics.rejected_names.add(user_name.strip())
            return False

        for u in users:                          # users bound directly
            add(u)

        used_groups: List[str] = []
        for name in sorted(group_names):
            if self.exclude_groups_re and self.exclude_groups_re.search(name):
                continue
            if name not in groups:
                # Bound but no Group object (e.g. not synced): no members to add
                metrics.groups_not_found += 1
                self.logger.debug(f"{namespace}: group '{name}' is bound but does not exist")
                continue
            contributed = [add(member) for member in groups[name]]
            if any(contributed):                 # list only groups that gave a valid id
                used_groups.append(name)

        return sorted(ids), used_groups

    # -------------------------------------------------------------- output
    def get_single_mode_output_path(self, cluster_name: str,
                                    output_arg: Optional[str],
                                    from_inventory: bool) -> Path:
        if output_arg:
            p = Path(output_arg)
            return p / OUTPUT_FILENAME if p.is_dir() else p
        if from_inventory:
            return self.base_folder / "output" / f"notification_{cluster_name}.csv"
        d = self.base_folder / cluster_name / "output"
        d.mkdir(parents=True, exist_ok=True)
        return d / OUTPUT_FILENAME

    def get_multi_mode_output_dir(self, output_arg: Optional[str] = None) -> Path:
        d = Path(output_arg) if output_arg else self.base_folder / "output"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def backup_file(self, path: Path, backup_count: int) -> None:
        if not path.exists():
            return
        for i in range(backup_count - 1, 0, -1):
            src = Path(f"{path}.{i}")
            dst = Path(f"{path}.{i + 1}")
            if src.exists():
                src.rename(dst)
        path.rename(Path(f"{path}.1"))

    def write_to_csv(self, rows: List[Dict], output_file: Path,
                     backup_count: int) -> None:
        if not rows:
            self.logger.info(f"No rows - skipping {output_file.name}")
            return
        output_file.parent.mkdir(parents=True, exist_ok=True)
        self.backup_file(output_file, backup_count)
        with open(output_file, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        self.logger.info(f"Wrote {len(rows)} rows -> {output_file}")

    # ------------------------------------------------------------ processing
    def process_cluster(self, cluster_name: str, username: str,
                        password: Optional[str], token: Optional[str],
                        retries: int, all_namespaces: bool = False
                        ) -> Tuple[List[Dict], ClusterMetrics]:
        metrics = ClusterMetrics(cluster_name=cluster_name, start_time=time.time())

        env = cluster_to_env(cluster_name)
        if env is None:
            metrics.end_time = time.time()
            msg = f"Invalid cluster '{cluster_name}': name must end with p, u, or d"
            metrics.add_error(msg)
            self.logger.error(msg)
            return [], metrics

        api_url        = self.build_api_url(cluster_name)
        execution_time = get_sgt_execution_time()
        self.logger.info(f"Cluster: {cluster_name} | env: {env} | API: {api_url}")

        for attempt in range(1, retries + 1):
            metrics.final_attempt = attempt
            self.logger.info(f"Attempt {attempt}/{retries}")
            try:
                auth_token = self.get_token(api_url, username, password,
                                            token, metrics)
                if not auth_token:
                    self.logger.error("Authentication failed")
                    if attempt < retries:
                        sleep(RETRY_SLEEP_SECONDS)
                    continue

                namespaces = self.list_namespaces(metrics, all_namespaces)
                metrics.namespaces_seen = len(namespaces)
                scope = "all" if all_namespaces else "prefix-matched"
                self.logger.info(f"Namespaces ({scope}): {len(namespaces)}")

                groups = self.fetch_all_groups(metrics)
                self.logger.info(f"Groups fetched: {metrics.groups_fetched}")

                bindings = None
                if self.group_source in ("rolebindings", "both"):
                    try:
                        bindings = self.fetch_namespace_bindings(metrics)
                        self.logger.info(
                            f"RoleBindings fetched: {metrics.rolebindings_fetched}")
                    except subprocess.CalledProcessError as e:
                        err = (e.stderr or "").strip().splitlines()
                        self.logger.warning(
                            "Cannot list RoleBindings cluster-wide "
                            f"({err[-1] if err else 'oc error'}) - falling back to "
                            "the app_ecs_{env}_{namespace}_edit/_view naming convention")
                        metrics.add_error("rolebindings unavailable - naming fallback")
                metrics.group_source_used = (self.group_source if bindings is not None
                                             or self.group_source == "naming"
                                             else "naming (fallback)")

                metrics.groups_not_found = 0  # count per attempt
                metrics.rejected_names = set()
                rows: List[Dict] = []
                for ns in namespaces:
                    ids, used_groups = self.access_for_namespace(
                        ns, env, groups, bindings, metrics)
                    if not ids:
                        continue
                    rows.append({
                        "time":      execution_time,
                        "cluster":   cluster_name,
                        "namespace": ns,
                        "env":       env,
                        "appid":     extract_appid(ns),
                        "ids":       ",".join(ids),  # DictWriter quotes this field
                        "groups":    GROUPS_SEPARATOR.join(used_groups),
                    })
                if metrics.rejected_names:
                    sample = sorted(metrics.rejected_names)
                    more = len(sample) - REJECTED_LOG_EXAMPLES
                    self.logger.warning(
                        f"{len(sample)} user name(s) rejected - no SOEID "
                        f"(2 letters + 5 digits): {', '.join(sample[:REJECTED_LOG_EXAMPLES])}"
                        + (f" ... +{more} more (see --log-level DEBUG)" if more > 0 else ""))
                    self.logger.debug(f"All rejected user names: {sample}")
                if metrics.groups_not_found:
                    self.logger.info(
                        f"{metrics.groups_not_found} namespace group binding(s) "
                        "point to groups that do not exist (no members)")
                self.logger.info(f"Group source: {metrics.group_source_used}")

                metrics.namespaces_written = len(rows)
                metrics.success  = True
                metrics.end_time = time.time()
                self.logger.info(
                    f"+ {cluster_name} - {len(rows)} namespaces with ids"
                )
                return rows, metrics

            except Exception as exc:
                self.logger.error(
                    f"Error processing {cluster_name}: {type(exc).__name__}"
                )
                self.logger.debug("Exception detail:", exc_info=True)
                metrics.add_error(f"{type(exc).__name__}")
                if attempt < retries:
                    sleep(RETRY_SLEEP_SECONDS)

        metrics.end_time = time.time()
        self.logger.error(f"All {retries} attempts failed for {cluster_name}")
        for err in metrics.error_messages:
            self.logger.error(f"  - {err}")
        return [], metrics


def create_argument_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Collect the members of every group mapped to each OpenShift namespace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-u",  "--username",    default=DEFAULT_USERNAME)
    p.add_argument("-tk", "--token",       help="Bearer token (oc login --token)")
    p.add_argument("-b",  "--base-folder", type=Path,
                   help="Base folder for .secrets, logs, inventory and output "
                        "(default: current working directory)")
    p.add_argument("-i",  "--inventory",   help="Cluster inventory file")
    p.add_argument("-c",  "--cluster-name")
    p.add_argument("-o",  "--output",      help="Output folder/file")
    p.add_argument("-m",  "--mode",        choices=["single", "multi"], default="single")
    p.add_argument("-A",  "--all-namespaces", action="store_true", default=True,
                   help="Pull from every namespace (default)")
    p.add_argument("-P",  "--prefix-only", dest="all_namespaces",
                   action="store_false",
                   help=f"Restrict to namespaces starting with {NAMESPACE_PREFIXES}")
    p.add_argument("-g",  "--group-source", choices=GROUP_SOURCES,
                   default=DEFAULT_GROUP_SOURCE,
                   help="Where a namespace's groups come from: 'rolebindings' "
                        "(every group bound in the namespace), 'naming' "
                        "(app_ecs_{env}_{ns}_edit/_view only - old behaviour) "
                        f"or 'both' (default: {DEFAULT_GROUP_SOURCE})")
    p.add_argument("--roles",
                   help="Comma-separated roles to count, e.g. admin,edit,view "
                        "(default: every role)")
    p.add_argument("--exclude-groups", default=DEFAULT_EXCLUDE_GROUPS,
                   help="Regex of group names to ignore, e.g. "
                        "'^system:|^ocp-platform-admins$' "
                        f"(default: '{DEFAULT_EXCLUDE_GROUPS}'; '' = none)")
    p.add_argument("--groups-only", action="store_true",
                   help="Ignore users bound directly to a namespace "
                        "(RoleBinding subject kind=User); only group members count")
    p.add_argument("--id-pattern", default=DEFAULT_ID_PATTERN,
                   help="Regex a user name must contain to count as a person; the "
                        "matched text becomes the id (default: SOEID = 2 letters + "
                        "5 digits, extra characters allowed around it). "
                        "'' = keep every name (old behaviour)")
    p.add_argument("--backup-count",       type=int, default=3)
    p.add_argument("-r",  "--retries",     type=int, default=DEFAULT_RETRIES)
    p.add_argument("--log-level",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    return p


def main() -> int:
    wall_start = time.time()
    try:
        is_orchestrator = detect_orchestrator_execution()
        parser = create_argument_parser()
        # Tolerate extra orchestrator-supplied args in orchestrator mode.
        args = parser.parse_known_args()[0] if is_orchestrator else parser.parse_args()

        # Priority: 1) -b/--base-folder   2) current working directory
        base_folder = resolve_base_folder(args.base_folder)
        base_folder_source = "CLI" if args.base_folder else "current working directory"

        base_paths  = {
            "key_file":      base_folder / ".secrets" / ".fernet.key",
            "password_file": base_folder / ".secrets" / ".password.enc",
            "cluster_file":  base_folder / "cluster-inventory.txt",
            "log_dir":       base_folder / "logs",
            "output_dir":    base_folder / "output",
        }

        roles = ({r.strip() for r in args.roles.split(",") if r.strip()}
                 if args.roles else None)
        try:
            script = NotificationInventoryScript(
                base_folder,
                group_source=args.group_source,
                roles=roles,
                exclude_groups=args.exclude_groups or None,
                include_direct_users=not args.groups_only,
                id_pattern=args.id_pattern or None,
            )
        except re.error as exc:
            print(f"Error: invalid --exclude-groups or --id-pattern regex: {exc}")
            return 2
        script.setup_logging(base_paths, args.log_level,
                             cluster_name=args.cluster_name, mode=args.mode)
        script.logger.info("NOTIFICATION INVENTORY COLLECTION")
        script.logger.info(f"Base folder ({base_folder_source}): {base_folder}")
        script.logger.info(
            f"Group source: {args.group_source} | roles: "
            f"{','.join(sorted(roles)) if roles else 'all'} | exclude groups: "
            f"{args.exclude_groups or 'none'} | direct users: "
            f"{'no' if args.groups_only else 'yes'} | id rule: "
            f"{args.id_pattern or 'none (every name kept)'}"
        )
        script.logger.info(
            "Namespace scope: "
            + ("ALL namespaces" if args.all_namespaces
               else f"prefix filter {NAMESPACE_PREFIXES}")
        )
        script.exec_home = script.setup_execution_home(base_folder)

        # Resolve cluster list.
        if args.cluster_name:
            clusters = [args.cluster_name]
        else:
            clusters_file = args.inventory or str(base_paths["cluster_file"])
            try:
                with open(clusters_file) as fh:
                    clusters = [l.strip() for l in fh
                                if l.strip() and not l.startswith("#")]
                script.logger.info(f"Read {len(clusters)} clusters from {clusters_file}")
            except Exception as exc:
                script.logger.error(f"Could not read cluster list: {exc}")
                return 1

        # Resolve auth.
        if args.token:
            password = None
            script.logger.info("Using provided bearer token")
        else:
            password = script.get_password(base_paths, len(clusters))
            if not password:
                script.logger.error("No authentication method available")
                return 1
            script.logger.info("Using username/password authentication")

        # Resolve output target.
        from_inventory = not bool(args.cluster_name)
        if args.mode == "single":
            if len(clusters) == 1:
                output_file = script.get_single_mode_output_path(
                    clusters[0], args.output, from_inventory
                )
            else:
                output_dir  = (Path(args.output) if args.output
                               else script.get_multi_mode_output_dir())
                output_file = output_dir / OUTPUT_FILENAME
            script.logger.info(f"Output: {output_file}")
        else:
            output_dir = script.get_multi_mode_output_dir(args.output)
            script.logger.info(f"Output directory: {output_dir}")

        all_rows:    List[Dict]           = []
        all_metrics: List[ClusterMetrics] = []
        success_count = 0

        for idx, cluster in enumerate(clusters, 1):
            script.logger.info(f"[{idx}/{len(clusters)}] {cluster}")
            rows, cm = script.process_cluster(
                cluster, args.username, password, args.token, args.retries,
                args.all_namespaces,
            )
            all_metrics.append(cm)

            if cm.success:
                success_count += 1
                if args.mode == "single":
                    all_rows.extend(rows)
                else:
                    if rows:
                        cf = output_dir / f"notification_{cluster}.csv"
                        script.write_to_csv(rows, cf, args.backup_count)
                        script.logger.info(f"Written: {cf}")
                    else:
                        script.logger.info(
                            f"No ids found for {cluster} - CSV not created"
                        )
            else:
                script.logger.warning(
                    f"Collection failed for {cluster} - CSV not written"
                )

        if args.mode == "single":
            if all_rows:
                script.write_to_csv(all_rows, output_file, args.backup_count)
                script.logger.info(f"Consolidated CSV: {output_file}")
            else:
                script.logger.info(
                    "No ids found across all clusters - CSV not created"
                )

        elapsed        = time.time() - wall_start
        total_ns       = sum(m.namespaces_written for m in all_metrics if m.success)
        total_oc_calls = sum(m.total_oc_calls     for m in all_metrics)

        script.logger.info("=" * 60)
        script.logger.info("EXECUTION SUMMARY")
        script.logger.info("=" * 60)
        script.logger.info(f"Elapsed:            {elapsed:.2f}s")
        script.logger.info(f"Namespaces written: {total_ns}")
        script.logger.info(f"oc calls:           {total_oc_calls}")
        script.logger.info(f"Success:            {success_count}/{len(clusters)}")

        if success_count > 0:
            print(f"\n{'='*70}")
            print("SUCCESS: Notification inventory collection completed!")
            print(f"{'='*70}")
            print(f"  Mode:       {args.mode}")
            print(f"  Clusters:   {success_count}/{len(clusters)}")
            print(f"  Namespaces: {total_ns}")
            print(f"  Time:       {elapsed:.1f}s")
            return 0

        print("\nError: Collection failed for all clusters")
        return 1

    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as exc:
        import traceback
        print(f"\nError: {type(exc).__name__}: see log for details")
        traceback.print_exc()
        return 1
    finally:
        try:
            if "script" in locals() and getattr(script, "exec_home", None):
                script.cleanup_execution_home(script.exec_home)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
