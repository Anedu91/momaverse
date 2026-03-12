from api.security import hash_password, verify_password


def test_hash_and_verify():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed)


def test_wrong_password_fails():
    hashed = hash_password("mypassword")
    assert not verify_password("wrongpassword", hashed)


def test_hash_is_not_plaintext():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert hashed.startswith("$2")


def test_different_hashes_for_same_password():
    h1 = hash_password("mypassword")
    h2 = hash_password("mypassword")
    assert h1 != h2
    assert verify_password("mypassword", h1)
    assert verify_password("mypassword", h2)
