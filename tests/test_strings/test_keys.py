from scc.uinput import Keys
from scc.lib import IntEnum

class TestKeys(object):
    def test_up_str(self):
        assert isinstance(Keys.KEY_UP, IntEnum)
        assert Keys.KEY_UP.name == "KEY_UP"
        assert str(Keys.KEY_UP) == "Keys.KEY_UP"