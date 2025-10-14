# app/services/chain_queue.py
import os
import redis
from rq import Queue

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_conn = redis.from_url(REDIS_URL)
chain_queue = Queue("blockchain", connection=redis_conn)
