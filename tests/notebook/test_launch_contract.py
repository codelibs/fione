"""Fione's launch tokens are what the notebook image's Jupyter extension accepts."""

import pytest

from fione.auth.roles import Role, User
from fione.notebooks import launch
from fione.notebooks.launch import launch_key, sign_launch_token
from fione_notebook.auth import LAUNCH_PARAM, verify_launch_token

pytestmark = pytest.mark.notebook

SECRET = b"s" * 32


@pytest.mark.parametrize("role", list(Role))
def test_the_container_accepts_fiones_launch_token(role):
    user = User(7, "ed", role)
    token = sign_launch_token(launch_key(SECRET, 7, "nonce-1"), user=user)
    claims = verify_launch_token(launch_key(SECRET, 7, "nonce-1"), token, owner="7")
    assert claims is not None
    assert (claims["sub"], claims["name"], claims["role"]) == ("7", "ed", role.value)


def test_another_start_or_user_is_refused():
    token = sign_launch_token(launch_key(SECRET, 7, "nonce-1"), user=User(7, "ed", Role.EDITOR))
    assert verify_launch_token(launch_key(SECRET, 7, "nonce-2"), token, owner="7") is None
    assert verify_launch_token(launch_key(SECRET, 8, "nonce-1"), token, owner="8") is None
    assert verify_launch_token(launch_key(SECRET, 7, "nonce-1"), token, owner="8") is None


def test_an_expired_launch_token_is_refused():
    key = launch_key(SECRET, 7, "n")
    token = sign_launch_token(key, user=User(7, "ed", Role.EDITOR), now=1000)
    assert verify_launch_token(key, token, owner="7", now=1000 + 59) is not None
    assert verify_launch_token(key, token, owner="7", now=1000 + 60) is None


def test_the_launch_parameter_matches():
    assert launch.LAUNCH_PARAM == LAUNCH_PARAM
