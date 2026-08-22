from shared.release_checks import scan_text


def test_secret_scan_identifies_kind_without_returning_value():
    secret = "sk-" + "A" * 24

    findings = scan_text(f"safe\nkey={secret}")

    assert findings == [(2, "openai_key")]
    assert secret not in repr(findings)


def test_secret_scan_ignores_placeholders():
    assert scan_text("OPENAI_API_KEY=your-key-here\nghp_example") == []
