"""Convert existing catalog prices from USD to KES.

Revision ID: c9317a9e4f20
Revises: bf7036db7373
Create Date: 2026-11-08 17:20:00

"""
from decimal import Decimal, ROUND_HALF_UP

from alembic import op
import sqlalchemy as sa


revision = "c9317a9e4f20"
down_revision = "bf7036db7373"
branch_labels = None
depends_on = None

USD_TO_KES = Decimal("129.920856")
WHOLE_SHILLING = Decimal("1")
ONE_CENT = Decimal("0.01")

products = sa.table(
    "products",
    sa.column("id", sa.Integer),
    sa.column("price", sa.Numeric(10, 2)),
    sa.column("compare_at", sa.Numeric(10, 2)),
)


def _convert(amount, rate, precision):
    if amount is None:
        return None
    return (Decimal(amount) * rate).quantize(precision, rounding=ROUND_HALF_UP)


def upgrade():
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(products.c.id, products.c.price, products.c.compare_at)
    ).mappings().all()
    for row in rows:
        connection.execute(
            products.update()
            .where(products.c.id == row["id"])
            .values(
                price=_convert(row["price"], USD_TO_KES, WHOLE_SHILLING),
                compare_at=_convert(row["compare_at"], USD_TO_KES, WHOLE_SHILLING),
            )
        )


def downgrade():
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(products.c.id, products.c.price, products.c.compare_at)
    ).mappings().all()
    for row in rows:
        connection.execute(
            products.update()
            .where(products.c.id == row["id"])
            .values(
                price=_convert(row["price"], Decimal("1") / USD_TO_KES, ONE_CENT),
                compare_at=_convert(
                    row["compare_at"], Decimal("1") / USD_TO_KES, ONE_CENT
                ),
            )
        )
