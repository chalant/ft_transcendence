import asyncio

from django.test import SimpleTestCase

from common.game_server import GameServer


class RoomLockTests(SimpleTestCase):
	def setUp(self):
		self.server = GameServer(game_factory=None)

	def test_same_room_is_serialised(self):
		async def scenario():
			events = []
			release_first = asyncio.Event()

			async def first():
				async with self.server.room_lock("a"):
					events.append("first in")
					await release_first.wait()
					events.append("first out")

			async def second():
				async with self.server.room_lock("a"):
					events.append("second in")

			t1 = asyncio.create_task(first())
			await asyncio.sleep(0.05)
			t2 = asyncio.create_task(second())
			await asyncio.sleep(0.05)
			self.assertEqual(events, ["first in"])  # second is still waiting
			release_first.set()
			await asyncio.gather(t1, t2)
			return events

		self.assertEqual(
			asyncio.run(scenario()),
			["first in", "first out", "second in"])

	def test_other_rooms_are_not_blocked(self):
		async def scenario():
			async with self.server.room_lock("a"):
				async def enter_b():
					async with self.server.room_lock("b"):
						return True
				return await asyncio.wait_for(enter_b(), 0.5)

		self.assertTrue(asyncio.run(scenario()))

	def test_no_entry_left_after_release_or_error(self):
		async def scenario():
			async with self.server.room_lock("a"):
				pass
			try:
				async with self.server.room_lock("b"):
					raise RuntimeError("boom")
			except RuntimeError:
				pass
			return dict(self.server._room_locks)

		self.assertEqual(asyncio.run(scenario()), {})
