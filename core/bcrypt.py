from passlib.context import CryptContext

# 初始化密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    对密码进行哈希加密。
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配。
    """
    return pwd_context.verify(plain_password, hashed_password)
