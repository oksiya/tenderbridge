"""
Redis caching utilities for API responses
"""
import json
import redis
import hashlib
from typing import Optional, Callable, Any
from functools import wraps
from fastapi import Request
import os

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "redis")  # Use 'redis' for container networking
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

# Cache TTL (Time To Live) in seconds
DEFAULT_CACHE_TTL = 300  # 5 minutes


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a unique cache key based on function arguments
    
    Args:
        prefix: Cache key prefix (usually endpoint name)
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Unique cache key string
    """
    # Create a string representation of all arguments
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)
    
    # Hash if too long
    if len(key_string) > 100:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    return f"{prefix}:{key_string}" if key_string else prefix


def get_cached(key: str) -> Optional[Any]:
    """
    Get value from cache
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found
    """
    try:
        value = redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        print(f"Cache get error: {e}")
        return None


def set_cached(key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """
    Set value in cache with TTL
    
    Args:
        key: Cache key
        value: Value to cache (must be JSON serializable)
        ttl: Time to live in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        print(f"Cache set error: {e}")
        return False


def invalidate_cache(pattern: str) -> int:
    """
    Invalidate all cache keys matching pattern
    
    Args:
        pattern: Redis key pattern (supports wildcards *)
        
    Returns:
        Number of keys deleted
    """
    try:
        keys = redis_client.keys(pattern)
        if keys:
            return redis_client.delete(*keys)
        return 0
    except Exception as e:
        print(f"Cache invalidation error: {e}")
        return 0


def cache_response(
    prefix: str,
    ttl: int = DEFAULT_CACHE_TTL,
    key_builder: Optional[Callable] = None
):
    """
    Decorator to cache API responses
    
    Usage:
        @cache_response("tenders:list", ttl=300)
        def list_tenders(skip: int = 0, limit: int = 50):
            ...
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_builder: Optional custom function to build cache key
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default: use function arguments
                cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = get_cached(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call original function
            result = await func(*args, **kwargs)
            
            # Cache the result
            set_cached(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = get_cached(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call original function
            result = func(*args, **kwargs)
            
            # Cache the result
            set_cached(cache_key, result, ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Cache invalidation helpers for specific resources
def invalidate_tender_cache(tender_id: Optional[str] = None):
    """Invalidate tender-related cache"""
    if tender_id:
        invalidate_cache(f"tenders:*{tender_id}*")
        invalidate_cache(f"documents:tenders:{tender_id}*")
        invalidate_cache(f"qa:tenders:{tender_id}*")
    else:
        invalidate_cache("tenders:*")


def invalidate_bid_cache(bid_id: Optional[str] = None, tender_id: Optional[str] = None):
    """Invalidate bid-related cache"""
    if bid_id:
        invalidate_cache(f"bids:*{bid_id}*")
        invalidate_cache(f"documents:bids:{bid_id}*")
    if tender_id:
        invalidate_cache(f"bids:tender:{tender_id}*")


def invalidate_notification_cache(user_id: str):
    """Invalidate notification cache for a user"""
    invalidate_cache(f"notifications:user:{user_id}*")


def invalidate_document_cache(tender_id: Optional[str] = None, bid_id: Optional[str] = None):
    """Invalidate document cache"""
    if tender_id:
        invalidate_cache(f"documents:tenders:{tender_id}*")
    if bid_id:
        invalidate_cache(f"documents:bids:{bid_id}*")


# Middleware to add cache headers
def add_cache_headers(response, max_age: int = 300):
    """Add cache-control headers to response"""
    response.headers["Cache-Control"] = f"public, max-age={max_age}"
    response.headers["X-Cache-Status"] = "MISS"
    return response


# Health check for Redis
def redis_health_check() -> bool:
    """Check if Redis is accessible"""
    try:
        redis_client.ping()
        return True
    except:
        return False
