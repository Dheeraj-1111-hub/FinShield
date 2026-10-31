import pytest
from app.core.security import get_password_hash, verify_password

def test_password_hashing():
    password = "MyStrongPassword123!"
    
    # 1. hash is generated
    pwd_hash = get_password_hash(password)
    assert pwd_hash is not None
    assert isinstance(pwd_hash, str)
    
    # 2. hash != original password
    assert pwd_hash != password
    
    # 3. same password can be verified
    assert verify_password(password, pwd_hash) is True
    
    # 4. incorrect password fails
    assert verify_password("WrongPassword123!", pwd_hash) is False
    assert verify_password(password + " ", pwd_hash) is False
    assert verify_password("myStrongPassword123!", pwd_hash) is False
    
def test_empty_password_fails():
    pwd_hash = get_password_hash("valid_pass")
    assert verify_password("", pwd_hash) is False
