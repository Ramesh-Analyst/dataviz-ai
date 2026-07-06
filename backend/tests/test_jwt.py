from datetime import datetime, timedelta, UTC
from jose import jwt
import time

SECRET_KEY = "949f57d605175cf14e7a83d7350c37cf3a9f7e8b91c89f53e6b772bd2304910e"
ALGORITHM = "HS256"

# Create token
expire = datetime.now(UTC) + timedelta(minutes=30)
to_encode = {"exp": expire, "sub": "1"}
token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

print("Generated token:", token)

# Decode token
try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print("Decoded payload:", payload)
    print("Expires at:", datetime.fromtimestamp(payload["exp"], tz=UTC))
except Exception as e:
    print("Decoding failed:", e)
