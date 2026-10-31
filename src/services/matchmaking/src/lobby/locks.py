from django.db import connection


def advisory_lock(key: str) -> None:
	"""Take a Postgres advisory lock that lives until the current transaction ends.

	Serialises every writer that uses the same key, across threads, processes and
	service replicas. Must be called inside `transaction.atomic()`; a second call
	with the same key from the same transaction does not block.
	"""
	with connection.cursor() as cursor:
		cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [key])
