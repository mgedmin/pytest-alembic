import os
import re

import pytest
from _pytest import fixtures


def collect_all_tests():
    from pytest_alembic import tests

    all_tests = {}
    for name in dir(tests):
        if name.startswith("test_"):
            all_tests[name[5:]] = getattr(tests, name)

    return all_tests


def parse_raw_test_names(raw_test_names):
    test_names = re.split(r"[,\n]", raw_test_names)

    result = []
    for test_name in test_names:
        test_name = test_name.strip()
        if not test_name:
            continue
        result.append(test_name)
    return result


def enabled_test_names(all_test_names, raw_included_tests, raw_excluded_tests):
    if raw_included_tests:
        included_tests = set(parse_raw_test_names(raw_included_tests))
        invalid_tests = included_tests - all_test_names
        if invalid_tests:
            invalid_str = ", ".join(sorted(invalid_tests))
            raise ValueError(f"The following tests were unrecognized: {invalid_str}")

        return included_tests

    excluded_tests = set(parse_raw_test_names(raw_excluded_tests))
    invalid_tests = excluded_tests - all_test_names
    if invalid_tests:
        invalid_str = ", ".join(sorted(invalid_tests))
        raise ValueError(f"The following tests were unrecognized: {invalid_str}")

    return all_test_names - excluded_tests


def collect_tests(session, config):
    cli_enabled = config.option.pytest_alembic_enabled
    config_enabled = config.getini("pytest_alembic_enabled")
    if not cli_enabled and config_enabled:
        return []

    raw_included_tests = config.getini("pytest_alembic_include")
    raw_excluded_tests = config.getini("pytest_alembic_exclude")

    all_tests = collect_all_tests()
    test_names = enabled_test_names(set(all_tests), raw_included_tests, raw_excluded_tests)

    result = []
    for test_name in sorted(test_names):
        test = all_tests[test_name]
        result.append(
            PytestAlembicItem(os.path.join("pytest_alembic", "tests", test_name), session, test)
        )

    return result


class PytestAlembicItem(pytest.Item):
    obj = None

    def __init__(self, name, parent, test_fn):
        super().__init__(name, parent)

        self.test_fn = test_fn
        self.funcargs = {}

        self.add_marker("alembic")

    def runtest(self):
        fm = self.session._fixturemanager
        self._fixtureinfo = fm.getfixtureinfo(node=self, func=self.test_fn, cls=None)

        fixture_request = fixtures.FixtureRequest(self)
        fixture_request._fillfixtures()

        params = {arg: self.funcargs[arg] for arg in self._fixtureinfo.argnames}

        self.test_fn(**params)

    def reportinfo(self):
        return (self.fspath, 0, f"[pytest-alembic] {self.name}")