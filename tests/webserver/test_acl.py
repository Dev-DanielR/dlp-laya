from pathlib import Path

from webserver.acl import AclStore

ACL = Path(__file__).resolve().parents[2] / "src" / "webserver" / "defaults" / "acl_paths.yaml"


def test_longest_prefix_wins():
    store = AclStore.load(ACL)
    assert store.resolve("bruno.media@knowsyn.dev", "/files/clientes") == "media"
    assert (
        store.resolve(
            "bruno.media@knowsyn.dev",
            "/files/clientes/banco_andino/confidencial/x.csv",
        )
        == "baja"
    )


def test_ana_root_alta():
    store = AclStore.load(ACL)
    assert (
        store.resolve("ana.alta@knowsyn.dev", "/files/casos/caso01_informe_sensible.docx")
        == "alta"
    )


def test_carla_caso01():
    store = AclStore.load(ACL)
    assert (
        store.resolve(
            "carla.baja@knowsyn.dev", "/files/casos/caso01_informe_sensible.docx"
        )
        == "baja"
    )


def test_acl_miss():
    store = AclStore.load(ACL)
    assert (
        store.resolve(
            "carla.baja@knowsyn.dev", "/files/interno/rrhh/planilla_parcial_marzo.csv"
        )
        is None
    )
    assert store.resolve("nobody", "/files/publico/x.txt") is None
