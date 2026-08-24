import tempfile
import unittest
from types import SimpleNamespace
from storage import SQLiteStorage

class StorageTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            s=SQLiteStorage(f"{d}/state.sqlite3")
            bot=SimpleNamespace(history={1:[{"title":"Song"}]},favorites={2:[{"title":"Fav"}]},playlists={2:{"mix":[{"title":"Song"}]}},warnings={(1,2):3},security_settings={1:{"spam_limit":5}},loop_mode={1:"song"},shuffle_mode={1:True},eq_presets={1:"rock"},song_skiplist={1:["x"]})
            s.save_from(bot)
            bot2=SimpleNamespace(history={},favorites={},playlists={},warnings={},security_settings={},loop_mode={},shuffle_mode={},eq_presets={},song_skiplist={})
            s.load_into(bot2)
            self.assertEqual(bot2.history[1][0]["title"],"Song")
            self.assertEqual(bot2.warnings[(1,2)],3)
            self.assertTrue(bot2.shuffle_mode[1])
            s.close()

if __name__ == "__main__":
    unittest.main()
