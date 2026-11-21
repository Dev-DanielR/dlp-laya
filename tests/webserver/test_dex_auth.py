import pytest

from webserver.auth.dex import DexAuthError


def test_valid_token(dex_validator, mint_token):
    token = mint_token("bruno.media")
    assert dex_validator.username_from_token(token) == "bruno.media"
    assert (
        dex_validator.username_from_authorization(f"Bearer {token}") == "bruno.media"
    )


def test_expired(dex_validator, mint_token):
    token = mint_token("ana.alta", exp_delta=-120)
    with pytest.raises(DexAuthError):
        dex_validator.username_from_token(token)


def test_wrong_audience(dex_validator, mint_token):
    token = mint_token("ana.alta", aud="other-client")
    with pytest.raises(DexAuthError):
        dex_validator.username_from_token(token)


def test_missing_header(dex_validator):
    with pytest.raises(DexAuthError):
        dex_validator.username_from_authorization(None)


def test_issuer_requires_http_scheme():
    from webserver.auth.dex import DexValidator

    with pytest.raises(ValueError, match="absolute http"):
        DexValidator(issuer="dex.local/dex", client_id="x")
