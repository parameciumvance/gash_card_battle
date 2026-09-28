"""卡片效果系統:registry 為引擎掛鉤介面,匯入各 handler 模組即完成註冊。"""

from . import registry  # noqa: F401
from . import primitives  # noqa: F401
from . import tree  # noqa: F401
from . import cards  # noqa: F401  卡片效果樹登記(依卡片類別分檔,每檔依卡號排序)
