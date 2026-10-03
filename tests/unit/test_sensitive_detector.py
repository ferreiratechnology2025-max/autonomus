import pytest

from src.governance.sensitive_detector import SensitiveDataDetector


def test_detects_password():
    detector = SensitiveDataDetector()
    results = detector.detect("my password = secret123")
    assert len(results) >= 1
    assert results[0]["type"] == "password"


def test_detects_email():
    detector = SensitiveDataDetector()
    results = detector.detect("contact me at test@example.com")
    assert any(r["type"] == "email" for r in results)


def test_detects_credit_card():
    detector = SensitiveDataDetector()
    results = detector.detect("card: 4111-1111-1111-1111")
    assert any(r["type"] == "credit_card" for r in results)


def test_detects_ssn():
    detector = SensitiveDataDetector()
    results = detector.detect("SSN: 123-45-6789")
    assert any(r["type"] == "ssn" for r in results)


def test_detects_api_key():
    detector = SensitiveDataDetector()
    results = detector.detect("api_key = sk-test1234567890")
    assert any(r["type"] == "api_key" for r in results)


def test_detects_jwt():
    detector = SensitiveDataDetector()
    results = detector.detect(
        "token: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjhN"
    )
    assert any(r["type"] == "jwt" for r in results)


def test_detects_phone():
    detector = SensitiveDataDetector()
    results = detector.detect("call me at (11) 91234-5678")
    assert any(r["type"] == "phone" for r in results)


def test_clean_text_returns_empty():
    detector = SensitiveDataDetector()
    results = detector.detect("hello world this is safe text")
    assert len(results) == 0


def test_has_sensitive_data_true():
    detector = SensitiveDataDetector()
    assert detector.has_sensitive_data("email: foo@bar.com") is True


def test_has_sensitive_data_false():
    detector = SensitiveDataDetector()
    assert detector.has_sensitive_data("how are you today?") is False


def test_detects_cpf():
    detector = SensitiveDataDetector()
    results = detector.detect("CPF: 123.456.789-09")
    assert any(r["type"] == "cpf" for r in results)


def test_detects_cnpj():
    detector = SensitiveDataDetector()
    results = detector.detect("CNPJ 12.345.678/0001-90")
    assert any(r["type"] == "cnpj" for r in results)


def test_detects_cep():
    detector = SensitiveDataDetector()
    results = detector.detect("CEP 01310-100")
    assert any(r["type"] == "cep" for r in results)


def test_detects_processo_juridico():
    detector = SensitiveDataDetector()
    results = detector.detect("Numero do processo: 1234567-89.2024.8.26.0100")
    assert any(r["type"] == "processo_juridico" for r in results)


def test_detects_cid():
    detector = SensitiveDataDetector()
    results = detector.detect("CID: J15.4")
    assert any(r["type"] == "cid" for r in results)


def test_detects_crm():
    detector = SensitiveDataDetector()
    results = detector.detect("CRM 12345 SP")
    assert any(r["type"] == "crm" for r in results)


def test_detects_prontuario():
    detector = SensitiveDataDetector()
    results = detector.detect("Prontuario: 2024-00589")
    assert any(r["type"] == "prontuario" for r in results)


def test_detects_conta_bancaria():
    detector = SensitiveDataDetector()
    results = detector.detect("Agencia: 1234 Conta: 56789-0")
    assert any(r["type"] == "conta_bancaria" for r in results)


def test_detects_pix():
    detector = SensitiveDataDetector()
    results = detector.detect("Chave Pix: user@email.com")
    assert any(r["type"] == "pix" for r in results)


def test_detects_cvv():
    detector = SensitiveDataDetector()
    results = detector.detect("CVV: 123")
    assert any(r["type"] == "cvv" for r in results)


def test_detects_passaporte():
    detector = SensitiveDataDetector()
    results = detector.detect("Passaporte: AB123456")
    assert any(r["type"] == "passaporte" for r in results)


def test_detects_cnh():
    detector = SensitiveDataDetector()
    results = detector.detect("CNH: 12345678901")
    assert any(r["type"] == "cnh" for r in results)


def test_detects_titulo_eleitor():
    detector = SensitiveDataDetector()
    results = detector.detect("Titulo: 1234.5678")
    assert any(r["type"] == "titulo_eleitor" for r in results)


@pytest.mark.asyncio
async def test_detect_in_image_returns_empty_on_error():
    detector = SensitiveDataDetector()
    results = await detector.detect_in_image(b"not a real image")
    assert results == []
