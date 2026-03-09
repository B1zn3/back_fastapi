from passlib.hash import argon2

class HashService:
    ARGON2_MEMORY_COST = 65536  
    ARGON2_TIME_COST = 3        
    ARGON2_PARALLELISM = 4      
    ARGON2_HASH_LENGTH = 32     
    ARGON2_SALT_LENGTH = 22     
    
    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        try:
            return argon2.verify(plain_password, hashed_password)
        except Exception as e:
            print(f"Password verification error: {e}")
            return False
    
    @classmethod
    def get_password_hash(cls, password: str) -> str:
        return argon2.hash(
            password
        )