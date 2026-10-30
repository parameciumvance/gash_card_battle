"""新房間的行動記錄從空白開始(battle-ui「行動記錄」):同一分頁打完一局後再開房,
等待畫面進入的新對局不殘留上一局的記錄,且新對局的事件照常顯示。需要 playwright 與 Chromium。"""
from tests.test_tables_ui import api, finish_game


def host_friend_room(page, server):
    """經設定頁開好友房、對手以 API 加入,等進入對局;回傳 (房號, 雙方 token)。"""
    page.locator("#entry-friend").click()
    page.locator('#friend-mode [data-mode="create"]').click()
    page.locator("#friend-submit").click()
    page.wait_for_function("SESSION && SESSION.code !== (window.prevCode || null)"
                           " && !document.getElementById('waiting').classList.contains('hidden')")
    code = page.evaluate("SESSION.code")
    guest = api(server, f"/api/rooms/{code}/join", {"deck": {"preset": "level2"}, "name": "對手"})
    page.wait_for_function("S && !document.getElementById('layout').classList.contains('hidden')", timeout=15000)
    return code, [page.evaluate("SESSION.tokens.me"), guest["player_token"]]


def log_lines(page):
    return page.locator("#log .ev").all_text_contents()


def test_new_room_log_starts_empty(page, server):
    code, tokens = host_friend_room(page, server)
    finish_game(server, code, tokens)
    page.wait_for_function("S && S.phase === 'game_over'", timeout=15000)
    ended = page.evaluate("t('log.game_ended', {player: '', reason: ''})").strip()[:4]
    assert any(ended in line for line in log_lines(page))

    page.evaluate("window.prevCode = SESSION.code; goHome()")
    host_friend_room(page, server)
    page.wait_for_function("document.querySelectorAll('#log .ev').length > 0", timeout=15000)
    lines = log_lines(page)
    assert not any(ended in line for line in lines)                  # 上一局的記錄沒有殘留
    assert lines[0] == page.evaluate("t('log.game_started')")          # 新一局從開局事件開始
