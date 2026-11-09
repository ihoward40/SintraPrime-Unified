"""Prevent the root/web security-update failures from returning.

Version floors come from GHSA-g3hv-75wg-m249, GHSA-mrwp-f3q8-3g9p,
and GHSA-rj75-hqrm-r3gf. Installed-consumer tests live beside this file.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
TARGETS = ("minimatch", "follow-redirects", "postcss-selector-parser")


def _read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _npm_versions():
    packages = _read_json("web/package-lock.json")["packages"]
    return {
        name: {
            package["version"]
            for path, package in packages.items()
            if path.rsplit("node_modules/", 1)[-1] == name
        }
        for name in TARGETS
    }


def _pnpm_versions():
    lock = yaml.safe_load((ROOT / "web/pnpm-lock.yaml").read_text(encoding="utf-8"))
    return {
        name: {
            key[len(name) + 1 :].split("(", 1)[0]
            for key in lock["packages"]
            if key.startswith(name + "@")
        }
        for name in TARGETS
    }


@pytest.mark.parametrize("section", ["dependencies", "devDependencies", "optionalDependencies"])
def test_root_lock_matches_actual_manifest(section):
    manifest = _read_json("package.json")
    lock_root = _read_json("package-lock.json")["packages"][""]
    assert lock_root.get(section, {}) == manifest.get(section, {})


@pytest.mark.parametrize("manager", ["npm", "pnpm"])
@pytest.mark.parametrize("name", TARGETS)
def test_web_locks_exclude_target_advisories(manager, name):
    versions = (_npm_versions() if manager == "npm" else _pnpm_versions())[name]
    assert versions, f"No installed dependency evidence for {manager}/{name}"
    for version in versions:
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), version
        number = tuple(map(int, version.split(".")))
        if name == "minimatch":
            # Legacy 3.x consumers use a different API and are outside this
            # advisory's >=7 range; do not force them onto the modern export.
            assert not ((7, 0, 0) <= number < (11, 0, 1)), (manager, name, version)
        elif name == "follow-redirects":
            assert number >= (1, 16, 2), (manager, name, version)
        else:
            assert number >= (6, 1, 5), (manager, name, version)
            assert not ((7, 0, 0) <= number < (7, 1, 6)), (manager, name, version)


@pytest.mark.parametrize("name", TARGETS)
def test_security_targets_agree_between_package_managers(name):
    assert _npm_versions()[name] == _pnpm_versions()[name]
