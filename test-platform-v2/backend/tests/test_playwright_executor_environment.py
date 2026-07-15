from types import SimpleNamespace

from app.services import playwright_executor


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Db:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self, _query):
        return _Scalars(self._rows)


def test_resolve_environment_variables_decrypts_and_skips_invalid_keys(monkeypatch):
    rows = [
        SimpleNamespace(key="PROD_PHONE", value="cipher-phone", encrypted=True),
        SimpleNamespace(key="PLAIN_VALUE", value="visible", encrypted=False),
        SimpleNamespace(key="BAD-KEY", value="ignored", encrypted=False),
    ]
    monkeypatch.setattr("app.core.cipher.decrypt_value", lambda value: "decrypted" if value == "cipher-phone" else value)

    result = playwright_executor._resolve_environment_variables(_Db(rows), 2)

    assert result == {"PROD_PHONE": "decrypted", "PLAIN_VALUE": "visible"}
