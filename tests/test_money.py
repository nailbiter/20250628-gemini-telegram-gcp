import pytest
from unittest.mock import MagicMock

import common
from _actor import add_money, CURRENCY_RATES


def make_mocks():
    messages = []

    async def send(msg):
        messages.append(msg)

    docs = []
    mongo = MagicMock()
    mongo[common.MONGO_COLL_NAME]["alex.money"].insert_one.side_effect = docs.append
    return send, mongo, messages, docs


async def test_no_rmb_amount_unchanged():
    send, mongo, _, docs = make_mocks()
    await add_money("100 #food lunch", send_message_cb=send, mongo_client=mongo)
    assert docs[0]["amount"] == 100.0


async def test_rmb_converts_to_yen():
    send, mongo, _, docs = make_mocks()
    await add_money("10 #fun #rmb tea", send_message_cb=send, mongo_client=mongo)
    assert docs[0]["amount"] == pytest.approx(10 * CURRENCY_RATES["rmb_to_yen"])


async def test_rmb_stored_in_tags():
    send, mongo, _, docs = make_mocks()
    await add_money("10 #fun #rmb tea", send_message_cb=send, mongo_client=mongo)
    assert "rmb" in docs[0]["tags"]


async def test_rmb_with_math_expression():
    send, mongo, _, docs = make_mocks()
    await add_money("5+5 #food #rmb noodles", send_message_cb=send, mongo_client=mongo)
    assert docs[0]["amount"] == pytest.approx(10 * CURRENCY_RATES["rmb_to_yen"])


async def test_hkd_converts_to_yen():
    send, mongo, _, docs = make_mocks()
    await add_money("10 #fun #hkd tea", send_message_cb=send, mongo_client=mongo)
    assert docs[0]["amount"] == pytest.approx(10 * CURRENCY_RATES["hkd_to_yen"])


async def test_hkd_stored_in_tags():
    send, mongo, _, docs = make_mocks()
    await add_money("10 #fun #hkd tea", send_message_cb=send, mongo_client=mongo)
    assert "hkd" in docs[0]["tags"]
