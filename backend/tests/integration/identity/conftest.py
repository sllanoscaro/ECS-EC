"""Identity fixtures are shared with contract suites through backend.tests.identity_fixtures.

The root plugin keeps PostgreSQL isolation, trusted clock, role factories and HTTP transport
identical across both suites; there are no public fixture or clock-control routes.
"""
