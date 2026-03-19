import os
import re
import subprocess

from astroid import nodes
from pylint.checkers import BaseChecker


REQUIRED_VALUES = {
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",
}

REQUIRED_ORDER = [
    "name",
    "version",
    "summary",
    "description",
    "author",
    "website",
    "company",
    "maintainer",
    "license",
    "support",
    "price",
    "currency",
]


class ManifestChecker(BaseChecker):
    name = "syncoria-manifest-checker"
    priority = -1

    msgs = {
        "E9001": (
            "Duplicate key '%s' in manifest",
            "duplicate-manifest-key",
            "Manifest contains duplicate keys.",
        ),
        "E9002": (
            "Invalid value for key '%s'. Expected %r, got %r",
            "invalid-manifest-value",
            "Manifest key has incorrect value.",
        ),
        "E9003": (
            "Manifest keys are not in required order\nExpected order: {}\nGot: {}".format(REQUIRED_ORDER, "%s"),
            "invalid-manifest-order",
            "Manifest keys are not in required sequence.",
        ),
        "E9004": (
            "Manifest version %r is invalid for branch %r. Expected pattern %r",
            "invalid-manifest-version-for-branch",
            "Manifest version does not match the current Git branch series.",
        ),
    }

    def visit_module(self, node: nodes.Module) -> None:
        if not node.file or not node.file.endswith("__manifest__.py"):
            return

        for child in node.body:
            if isinstance(child, nodes.Assign) and isinstance(child.value, nodes.Dict):
                self._check_manifest(child.value)
                return

            if isinstance(child, nodes.Expr) and isinstance(child.value, nodes.Dict):
                self._check_manifest(child.value)
                return

    def _literal_value(self, node):
        if isinstance(node, nodes.Const):
            return node.value
        return None

    def _get_current_branch(self) -> str | None:
        env_branch = os.getenv("GIT_BRANCH") or os.getenv("BRANCH_NAME")
        if env_branch:
            return env_branch.strip()

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            branch = result.stdout.strip()
            return branch or None
        except Exception:
            return None

    def _extract_series_from_branch(self, branch: str) -> tuple[str, str] | None:
        """
        Detects series anywhere in branch name.

        Examples matched:
        - 18.0
        - 18.0-fix-payroll
        - feature/18.0/payroll
        - hotfix-18.0-x
        - bugfix_odoo_17.0_partner_sync

        Does not match inside larger numeric strings like 118.05 unless separated.
        """
        match = re.search(r"(?<!\d)(\d+)\.(\d+)(?!\d)", branch)
        if not match:
            return None
        return match.group(1), match.group(2)

    def _expected_version_pattern_for_branch(self, branch: str) -> str | None:
        series = self._extract_series_from_branch(branch)
        if not series:
            return None

        major, minor = series
        return rf"^{major}\..+$"

    def _check_manifest(self, dict_node: nodes.Dict) -> None:
        keys_seen = set()
        keys_list = []
        manifest_version = None
        version_node = None

        for key_node, value_node in dict_node.items:
            key = self._literal_value(key_node)
            if key is None:
                continue

            keys_list.append(key)

            if key in keys_seen:
                self.add_message(
                    "duplicate-manifest-key",
                    node=key_node,
                    args=(key,),
                )
            else:
                keys_seen.add(key)

            if key in REQUIRED_VALUES:
                expected = REQUIRED_VALUES[key]
                actual = self._literal_value(value_node)
                if actual != expected:
                    self.add_message(
                        "invalid-manifest-value",
                        node=value_node,
                        args=(key, expected, actual),
                    )

            if key == "version":
                manifest_version = self._literal_value(value_node)
                version_node = value_node

        prefix = keys_list[: len(REQUIRED_ORDER)]
        if prefix != REQUIRED_ORDER:
            self.add_message("invalid-manifest-order", node=dict_node)

        branch = self._get_current_branch()
        if branch and manifest_version and isinstance(manifest_version, str):
            expected_pattern = self._expected_version_pattern_for_branch(branch)
            if expected_pattern and not re.match(expected_pattern, manifest_version):
                self.add_message(
                    "invalid-manifest-version-for-branch",
                    node=version_node or dict_node,
                    args=(manifest_version, branch, expected_pattern),
                )


def register(linter) -> None:
    linter.register_checker(ManifestChecker(linter))
