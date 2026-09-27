"""卡片效果系統:registry 為引擎掛鉤介面,匯入各 handler 模組即完成註冊。"""

from . import registry  # noqa: F401
from . import primitives  # noqa: F401
from . import mamodo  # noqa: F401
from . import partners  # noqa: F401
from . import events  # noqa: F401
from . import spells  # noqa: F401
from . import tree  # noqa: F401
from . import tree_cards  # noqa: F401  卡片效果樹註冊檔(依卡號排序,每卡一個呼叫)
