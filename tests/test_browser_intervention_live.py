import tempfile
import json
from pathlib import Path
from tools import LocalTools


def test_browser_intervention_and_input_locking_live():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        tools = LocalTools(workspace=workspace, headless=True)
        session_id = "test_intervention_session"
        
        # 1. 打开网页，验证默认独占锁定 (__damingAgentAllowsInput == False)
        open_res = tools.open_browser("https://example.com", session_id=session_id, show_window=False)
        assert "已在后台浏览器中打开网页" in open_res
        
        browser_session = tools._get_browser_session(session_id)
        assert browser_session is not None
        
        input_allowed_default = browser_session.page.evaluate("() => window.__damingAgentAllowsInput")
        assert input_allowed_default is False, "默认情况下人类操控必须处于锁定状态(False)"
        
        # 2. 调用 request_human_intervention，验证解禁人类操控 (__damingAgentAllowsInput == True)
        intervene_res = tools.request_human_intervention(reason="需要人工扫码", session_id=session_id)
        assert "已临时开启人类操作权限" in intervene_res
        
        input_allowed_after_intervene = browser_session.page.evaluate("() => window.__damingAgentAllowsInput")
        assert input_allowed_after_intervene is True, "触发人工干预后人类操控必须解禁(True)"
        
        # 3. 模拟按键 (press_key Escape / Enter)
        key_res = tools.press_key("Escape", session_id=session_id)
        assert "已成功在浏览器按键: Escape" in key_res
        
        # 4. 调用 resume_agent_control，验证恢复 AI 独占锁定 (__damingAgentAllowsInput == False)
        resume_res = tools.resume_agent_control(session_id=session_id)
        assert "AI 已重新接管控制权" in resume_res
        
        input_allowed_after_resume = browser_session.page.evaluate("() => window.__damingAgentAllowsInput")
        assert input_allowed_after_resume is False, "恢复 AI 控制后人类操控必须重加锁(False)"
        
        # 5. 关闭浏览器
        close_res = tools.close_browser(session_id=session_id)
        assert "已成功关闭当前会话的浏览器" in close_res
