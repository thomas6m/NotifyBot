#!/usr/bin/env python3
"""
notification_inventory.py - Child script for the Parallel Orchestrator

Collects OpenShift edit/view group membership per namespace and writes
notification.csv:
    time, cluster, namespace, ids

Environment is derived from the LAST character of the cluster name:
    *p -> prod    *u -> uat    *d -> dev    (anything else is rejected)

For each namespace matching the prefix filter, the union of users in
    app_ecs_{env}_{namespace}_edit
    app_ecs_{env}_{namespace}_view
is collected, de-duplicated, and each user id is suffixed with @citi.com.
Namespaces with no users are skipped. The output file is only created
when at least one row exists.

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
from typing import Dict, List, Optional, Tuple

import pytz
from cryptography.fernet import Fernet


CSV_COLUMNS = ["time", "cluster", "namespace", "env", "appid", "ids"]
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
DEFAULT_BASE_FOLDER    = Path("/data/OSE/")
ENV_FERNET_KEY         = "ORCHESTRATOR_FERNET_KEY"
ENV_ENCRYPTED_PASSWORD = "ORCHESTRATOR_ENCRYPTED_PASSWORD"


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
    """Run `oc <args> -o json` and return the parsed object."""
    out = subprocess.check_output(
        ["oc", *args, "-o", "json"], text=True, env=_oc_env(exec_home),
    )
    return json.loads(out)


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

    def __init__(self):
        self.logger: Optional[logging.Logger] = None
        self.exec_home: Optional[Path]        = None

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

    def ids_for_namespace(self, namespace: str, env: str,
                          groups: Dict[str, List[str]]) -> List[str]:
        """Union of the _edit and _view group users (in-memory), suffixed with the domain.

        A missing group is simply absent from the lookup and contributes nothing,
        matching the original behaviour where a non-existent group was empty.
        """
        users = set()
        for suffix in ("edit", "view"):
            group_name = f"app_ecs_{env}_{namespace}_{suffix}"
            for user in groups.get(group_name, ()):
                users.add(user)
        return sorted(f"{u}{ID_DOMAIN}" for u in users)

    # -------------------------------------------------------------- output
    def get_single_mode_output_path(self, cluster_name: str,
                                    output_arg: Optional[str],
                                    from_inventory: bool) -> Path:
        if output_arg:
            p = Path(output_arg)
            return p / OUTPUT_FILENAME if p.is_dir() else p
        if from_inventory:
            return Path("/data/OSE/output") / f"notification_{cluster_name}.csv"
        d = Path(f"/data/OSE/{cluster_name}/output")
        d.mkdir(parents=True, exist_ok=True)
        return d / OUTPUT_FILENAME

    def get_multi_mode_output_dir(self, output_arg: Optional[str] = None) -> Path:
        d = Path(output_arg) if output_arg else Path("/data/OSE/output")
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

                rows: List[Dict] = []
                for ns in namespaces:
                    ids = self.ids_for_namespace(ns, env, groups)
                    if not ids:
                        continue
                    rows.append({
                        "time":      execution_time,
                        "cluster":   cluster_name,
                        "namespace": ns,
                        "env":       env,
                        "appid":     extract_appid(ns),
                        "ids":       ",".join(ids),  # DictWriter quotes this field
                    })

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
        description="Collect OpenShift edit/view group membership per namespace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-u",  "--username",    default=DEFAULT_USERNAME)
    p.add_argument("-tk", "--token",       help="Bearer token (oc login --token)")
    p.add_argument("-b",  "--base-folder", type=Path)
    p.add_argument("-i",  "--inventory",   help="Cluster inventory file")
    p.add_argument("-c",  "--cluster-name")
    p.add_argument("-o",  "--output",      help="Output folder/file")
    p.add_argument("-m",  "--mode",        choices=["single", "multi"], default="single")
    p.add_argument("-A",  "--all-namespaces", action="store_true", default=True,
                   help="Pull from every namespace (default)")
    p.add_argument("-P",  "--prefix-only", dest="all_namespaces",
                   action="store_false",
                   help=f"Restrict to namespaces starting with {NAMESPACE_PREFIXES}")
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

        base_folder = args.base_folder or DEFAULT_BASE_FOLDER
        base_paths  = {
            "key_file":      base_folder / ".secrets" / ".fernet.key",
            "password_file": base_folder / ".secrets" / ".password.enc",
            "cluster_file":  base_folder / "cluster-inventory.txt",
            "log_dir":       base_folder / "logs",
            "output_dir":    Path("/data/OSE/output"),
        }

        script = NotificationInventoryScript()
        script.setup_logging(base_paths, args.log_level,
                             cluster_name=args.cluster_name, mode=args.mode)
        script.logger.info("NOTIFICATION INVENTORY COLLECTION")
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
