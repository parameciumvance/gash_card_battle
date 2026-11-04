"""同一個瀏覽器兩個分頁分別當對局的兩方,重新整理後各自的身分不變(battle-ui「分頁的對局身分」)。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_session_identity_ui.py -q
"""


def open_tab(context, server):
    tab = context.new_page()
    tab.goto(server)
    wait(tab, "Object.keys(CARDS).length > 0")
    return tab


def wait(tab, expr):
    """多個分頁時背景分頁的 requestAnimationFrame 會暫停,以固定間隔輪詢。"""
    tab.wait_for_function(expr, polling=100)


def identity(tab):
    return tab.evaluate("[SESSION.viewer, SESSION.tokens.me]")


def reload_into_room(tab, code):
    tab.reload()
    wait(tab, f"SESSION && SESSION.code === '{code}' && R && R.started")


def test_two_tabs_keep_their_own_identity_after_reload(page, server):
    a = page
    a.evaluate("createRoom()")
    wait(a, "SESSION && SESSION.viewer === 0")
    code = a.evaluate("SESSION.code")
    b = open_tab(a.context, server)                                             # 同一個瀏覽器(共用 localStorage)
    b.evaluate("(code) => joinRoom(code)", code)
    wait(b, "SESSION && SESSION.viewer === 1 && R && R.started")
    wait(a, "R && R.started")
    a_id, b_id = identity(a), identity(b)
    assert a_id[0] == 0 and b_id[0] == 1 and a_id[1] != b_id[1]
    reload_into_room(a, code)
    assert identity(a) == a_id                                                  # 修正前:變成 B 的身分
    reload_into_room(b, code)
    assert identity(b) == b_id
    assert a.evaluate("myViewer()") == 0 and b.evaluate("myViewer()") == 1


def test_new_tab_resumes_from_landing(page, server):
    a = page
    a.evaluate("createRoom()")
    wait(a, "SESSION && SESSION.viewer === 0")
    code = a.evaluate("SESSION.code")
    c = open_tab(a.context, server)                                             # 新分頁沒有自己的身分:照舊用瀏覽器記得的
    c.goto(f"{server}/?room={code}")
    wait(c, f"SESSION && SESSION.code === '{code}'")
    assert identity(c) == identity(a)
