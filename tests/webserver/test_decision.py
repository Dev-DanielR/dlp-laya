import pytest

from webserver.decision import decide


@pytest.mark.parametrize(
    "sensitivity,label,expected",
    [
        ("alta", "limpio", "completo"),
        ("media", "limpio", "completo"),
        ("baja", "limpio", "completo"),
        ("alta", "con_pii", "completo"),
        ("media", "con_pii", "sanitizado"),
        ("baja", "con_pii", "denegado"),
    ],
)
def test_matrix(sensitivity, label, expected):
    assert decide(sensitivity, label) == expected


def test_invalid():
    with pytest.raises(ValueError):
        decide("media", "unknown")
