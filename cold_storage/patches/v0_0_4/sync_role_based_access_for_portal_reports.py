# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from cold_storage.setup.role_based_access import sync_role_based_access


def execute() -> None:
	"""Apply updated role/profile/report access matrix for portal report links."""
	sync_role_based_access()
