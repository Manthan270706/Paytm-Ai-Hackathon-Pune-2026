import tempfile
from pathlib import Path

from scripts.guard import (
    check_no_float_money,
    check_no_string_built_sql,
    check_tool_schemas_no_merchant_id,
)


def test_guard_catches_float_money() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        bad_domain_file = tmp_path / "bad_model.py"
        bad_domain_file.write_text(
            "class BadReconcile:\n    discrepancy: float = 0.0\n    amount: float = 100.0\n",
            encoding="utf-8",
        )
        errors = check_no_float_money(tmp_path)
        assert len(errors) >= 1
        assert any("uses float! Money must use Decimal" in e for e in errors)


def test_guard_catches_merchant_id_in_tool_schema() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        bad_schema_file = tmp_path / "schemas.py"
        bad_schema_file.write_text(
            "from pydantic import BaseModel\n\n"
            "class QueryTransactionsInput(BaseModel):\n"
            "    merchant_id: str\n"
            "    start_date: str\n",
            encoding="utf-8",
        )
        errors = check_tool_schemas_no_merchant_id(tmp_path)
        assert len(errors) >= 1
        assert any("contains 'merchant_id'" in e for e in errors)


def test_guard_catches_string_built_sql() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        bad_code_file = tmp_path / "bad_query.py"
        bad_code_file.write_text(
            'mid = "123"\nawait session.execute(f"SELECT * FROM transactions WHERE mid = {mid}")\n',
            encoding="utf-8",
        )
        errors = check_no_string_built_sql(tmp_path)
        assert len(errors) >= 1
        assert any("Potential SQL injection" in e for e in errors)
