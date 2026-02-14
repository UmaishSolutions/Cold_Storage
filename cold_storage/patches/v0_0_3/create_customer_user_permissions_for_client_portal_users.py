# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

def execute() -> None:
	"""Create missing Customer User Permissions for cold-storage client portal users."""
	from cold_storage.setup.client_portal_user_permissions import (
		sync_customer_user_permissions_for_client_portal_users,
	)

	sync_customer_user_permissions_for_client_portal_users()
