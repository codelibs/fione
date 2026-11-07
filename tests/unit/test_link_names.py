"""Which column names of two tables may name the same key."""

import pytest

from fione.tools import link_names


@pytest.mark.parametrize(
    ("table_a", "column_a", "table_b", "column_b", "expected"),
    [
        ("orders", "Customer_ID", "customers", "customer_id", "same_name"),
        ("customers", "id", "orders", "customer_id", "table_id"),
        ("merchants", "ID", "historical.csv", "merchant_id", "table_id"),
        ("categories", "id", "items", "category_id", "table_id"),
        ("previous_application", "id", "pos", "PreviousApplicationId", "table_id"),
        ("bureau", "SK_ID_BUREAU", "bureau_balance", "bureau_id", "similar_name"),
        ("a", "cust_id", "b", "customer_id", "similar_name"),
        ("a", "merchant_id", "b", "merch_id", "similar_name"),
        ("customers", "id", "orders", "product_id", None),  # the id of another table
        ("a", "id", "b", "id2", None),
        ("items", "item_id", "item_categories", "item_category_id", None),  # another entity
        ("a", "shop_id", "b", "shop_item_id", None),
        ("a", "customer_id", "b", "customer_type_id", None),
        ("a", "user_id", "b", "item_id", None),
        ("a", "MONTHS_BALANCE", "b", "CNT_INSTALMENT", None),  # not id-like
        ("a", "amount", "b", "total_amount", None),  # similar but not id-like
        ("a", "id", "b", "id", "same_name"),
        ("order_items", "item_id", "items", "id", "table_id"),
        ("items", "id", "orders", "num_items", None),  # a count
        ("items", "id", "orders", "number_of_items", None),
        ("orders", "order_number", "payments", "order_id", "similar_name"),
    ],
)
def test_related(table_a, column_a, table_b, column_b, expected):
    assert link_names.related(table_a, column_a, table_b, column_b) == expected
    assert link_names.related(table_b, column_b, table_a, column_a) == expected


def test_is_id_like():
    assert all(
        map(
            link_names.is_id_like,
            ["id", "SK_ID_CURR", "storeNbr", "zip_code", "userId", "order_number"],
        )
    )
    assert not any(
        map(
            link_names.is_id_like,
            ["amount", "date", "identity", "notes", "num_items", "number_of_items"],
        )
    )
