"""initial_schema

Revision ID: 43af7b1b4e7d
Revises: 8a62a740b821
Create Date: 2026-05-27 16:16:22.905114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43af7b1b4e7d'
down_revision: Union[str, Sequence[str], None] = '8a62a740b821'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_regions_id"), "regions", ["id"], unique=False)

    op.create_table(
        "settlement_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_settlement_types_id"), "settlement_types", ["id"], unique=False)

    op.create_table(
        "districts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("region_id", "name", name="uq_district_region_name"),
    )
    op.create_index(op.f("ix_districts_id"), "districts", ["id"], unique=False)
    op.create_index(op.f("ix_districts_region_id"), "districts", ["region_id"], unique=False)

    # 1. Добавляем новые поля как nullable=True,
    # чтобы PostgreSQL разрешил добавить их в таблицу со старыми городами.
    op.add_column("cities", sa.Column("district_id", sa.Integer(), nullable=True))
    op.add_column("cities", sa.Column("settlement_type_id", sa.Integer(), nullable=True))

    # 2. Создаём временную область, район и тип населённого пункта
    # для уже существующих старых городов.
    op.execute("""
        INSERT INTO regions (id, name)
        VALUES (1, 'Не указано')
        ON CONFLICT (name) DO NOTHING
    """)

    op.execute("""
        INSERT INTO settlement_types (id, name)
        VALUES (1, 'г.')
        ON CONFLICT (name) DO NOTHING
    """)

    op.execute("""
        INSERT INTO districts (id, region_id, name)
        VALUES (1, 1, 'Не указано')
        ON CONFLICT (region_id, name) DO NOTHING
    """)

    # 3. Проставляем старым городам временные значения.
    op.execute("""
        UPDATE cities
        SET district_id = 1
        WHERE district_id IS NULL
    """)

    op.execute("""
        UPDATE cities
        SET settlement_type_id = 1
        WHERE settlement_type_id IS NULL
    """)
    op.execute("""
    SELECT setval(
        pg_get_serial_sequence('regions', 'id'),
        COALESCE((SELECT MAX(id) FROM regions), 1),
        true
    )
""")

    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('settlement_types', 'id'),
            COALESCE((SELECT MAX(id) FROM settlement_types), 1),
            true
        )
    """)

    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('districts', 'id'),
            COALESCE((SELECT MAX(id) FROM districts), 1),
            true
        )
    """)

    # 4. Теперь можно делать поля NOT NULL.
    op.alter_column("cities", "district_id", nullable=False)
    op.alter_column("cities", "settlement_type_id", nullable=False)

    # 5. Удаляем старый unique только по name.
    op.drop_constraint("cities_name_key", "cities", type_="unique")

    # 6. Создаём индексы, FK и новый unique.
    op.create_index(op.f("ix_cities_district_id"), "cities", ["district_id"], unique=False)
    op.create_index(op.f("ix_cities_name"), "cities", ["name"], unique=False)
    op.create_index(op.f("ix_cities_settlement_type_id"), "cities", ["settlement_type_id"], unique=False)

    op.create_foreign_key(
        None,
        "cities",
        "districts",
        ["district_id"],
        ["id"],
    )
    op.create_foreign_key(
        None,
        "cities",
        "settlement_types",
        ["settlement_type_id"],
        ["id"],
    )

    op.create_unique_constraint(
        "uq_city_district_type_name",
        "cities",
        ["district_id", "settlement_type_id", "name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_city_district_type_name", "cities", type_="unique")

    op.drop_constraint(None, "cities", type_="foreignkey")
    op.drop_constraint(None, "cities", type_="foreignkey")

    op.drop_index(op.f("ix_cities_settlement_type_id"), table_name="cities")
    op.drop_index(op.f("ix_cities_name"), table_name="cities")
    op.drop_index(op.f("ix_cities_district_id"), table_name="cities")

    op.create_unique_constraint("cities_name_key", "cities", ["name"])

    op.drop_column("cities", "settlement_type_id")
    op.drop_column("cities", "district_id")

    op.drop_index(op.f("ix_districts_region_id"), table_name="districts")
    op.drop_index(op.f("ix_districts_id"), table_name="districts")
    op.drop_table("districts")

    op.drop_index(op.f("ix_settlement_types_id"), table_name="settlement_types")
    op.drop_table("settlement_types")

    op.drop_index(op.f("ix_regions_id"), table_name="regions")
    op.drop_table("regions")