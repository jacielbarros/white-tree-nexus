"""Regressão do GUC de tenant (RLS) — o módulo de contexto quebrava 100% no PostgreSQL.

O `SET` do PostgreSQL NÃO aceita bind parameters, então `SET LOCAL app.tenant_id = :tid`
falhava com "syntax error at or near $1". Como `_set_tenant_guc` roda em toda requisição que
usa `OrgContext`, todo endpoint `/context/*` (e os de membership/convite) estourava 500 no PG.
Os testes da suíte rodam em SQLite (onde a função é pulada), então o defeito passava batido.

Este teste mocka o dialect `postgresql` e garante que usamos `set_config(..., is_local=true)`
com o valor passado como bind param (equivalente ao SET LOCAL, e à prova de injeção).
"""
import uuid

from wtnapp.helpers.tenant_scope import _set_tenant_guc


class _Dialect:
    name = "postgresql"


class _Bind:
    dialect = _Dialect()


class _FakeDB:
    bind = _Bind()

    def __init__(self):
        self.sql = None
        self.params = None

    def execute(self, statement, params=None):
        self.sql = str(statement)
        self.params = params


def test_set_tenant_guc_usa_set_config_no_postgresql():
    db = _FakeDB()
    tid = uuid.uuid4()

    _set_tenant_guc(db, tid)

    sql = (db.sql or "").lower()
    assert "set_config" in sql, "deve usar set_config (SET parametrizado falha no PG)"
    assert "set local" not in sql, "a forma `SET LOCAL ... = :param` é inválida no PostgreSQL"
    assert db.params and str(tid) in db.params.values(), "tenant_id deve ir como bind param"


def test_set_tenant_guc_e_noop_fora_do_postgresql():
    class _Other(_FakeDB):
        bind = type("B", (), {"dialect": type("D", (), {"name": "sqlite"})()})()

    db = _Other()
    _set_tenant_guc(db, uuid.uuid4())
    assert db.sql is None  # nada é executado em SQLite
