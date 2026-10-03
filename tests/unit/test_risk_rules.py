from src.governance.models import RiskLevel
from src.governance.risk_rules import RiskRules


def test_type_text_dangerous_keyword():
    rules = RiskRules()
    assessment = rules.assess_action("type_text", {"text": "rm -rf /"})
    assert assessment.risk_level == RiskLevel.CRITICAL
    assert assessment.category == "data_loss"
    assert assessment.requires_confirmation is True


def test_type_text_auth():
    rules = RiskRules()
    assessment = rules.assess_action("type_text", {"text": "my password is 123"})
    assert assessment.risk_level == RiskLevel.HIGH
    assert assessment.category == "auth"


def test_type_text_financial():
    rules = RiskRules()
    assessment = rules.assess_action("type_text", {"text": "transfer $100"})
    assert assessment.risk_level == RiskLevel.MEDIUM
    assert assessment.category == "auth"


def test_type_text_safe():
    rules = RiskRules()
    assessment = rules.assess_action("type_text", {"text": "hello world"})
    assert assessment.risk_level == RiskLevel.SAFE


def test_click_dangerous_button():
    rules = RiskRules()
    assessment = rules.assess_action("click", {"button_text": "Delete all"})
    assert assessment.risk_level == RiskLevel.HIGH


def test_click_auth_button():
    rules = RiskRules()
    assessment = rules.assess_action("click", {"button_text": "Login"})
    assert assessment.risk_level == RiskLevel.MEDIUM


def test_click_safe_button():
    rules = RiskRules()
    assessment = rules.assess_action("click", {"button_text": "Cancel"})
    assert assessment.risk_level == RiskLevel.SAFE


def test_screenshot_is_medium():
    rules = RiskRules()
    assessment = rules.assess_action("screenshot", {})
    assert assessment.risk_level == RiskLevel.MEDIUM
    assert assessment.category == "ui_trap"


def test_press_hotkey_is_safe():
    rules = RiskRules()
    assessment = rules.assess_action("press_hotkey", {"keys": ("ctrl", "s")})
    assert assessment.risk_level == RiskLevel.SAFE


def test_scroll_is_safe():
    rules = RiskRules()
    assessment = rules.assess_action("scroll", {"amount": -3})
    assert assessment.risk_level == RiskLevel.SAFE


def test_mixed_category_type_text_takes_max():
    rules = RiskRules()
    assessment = rules.assess_action("type_text", {"text": "delete the password file"})
    assert assessment.risk_level == RiskLevel.CRITICAL


def test_low_keyword_before_high_keyword_escalates():
    rules = RiskRules()
    assessment = rules.assess_action("type_text", {"text": "transfer funds then rm -rf /data"})
    assert assessment.risk_level == RiskLevel.CRITICAL


def test_click_with_dangerous_and_financial_takes_highest():
    rules = RiskRules()
    assessment = rules.assess_action("click", {"button_text": "delete payment"})
    assert assessment.risk_level == RiskLevel.HIGH


def test_click_with_auth_and_financial_both_medium():
    rules = RiskRules()
    assessment = rules.assess_action("click", {"button_text": "login transfer"})
    assert assessment.risk_level == RiskLevel.MEDIUM
