from slowapi import Limiter
from slowapi.util import get_remote_address

# Single shared limiter — imported by all routers and main.py
limiter = Limiter(key_func=get_remote_address)
