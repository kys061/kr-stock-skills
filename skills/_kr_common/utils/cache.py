"""파일 기반 캐시 - 크롤링 부하 최소화."""

import os
import time
import hashlib
import pickle
import logging
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)


class FileCache:
    """일별 데이터 캐시.

    크롤링 부하 최소화를 위해 동일 데이터 반복 호출 방지.
    캐시 키: {method}_{args_hash}
    저장 형식: pickle
    기본 TTL: 당일 데이터 = 장 마감 후까지, 과거 데이터 = 영구
    """

    # 장 마감 시간 (15:30 KST)
    MARKET_CLOSE_HOUR = 15
    MARKET_CLOSE_MINUTE = 30

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = os.path.expanduser('~/.cache/kr-stock-skills/')
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _key_to_path(self, key: str) -> str:
        """캐시 키를 파일 경로로 변환."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f'{safe_key}.pkl')

    def _get_eod_ttl(self) -> float:
        """장 마감까지 남은 초. 이미 마감 후면 다음 날 마감까지."""
        now = datetime.now()
        close_time = now.replace(
            hour=self.MARKET_CLOSE_HOUR,
            minute=self.MARKET_CLOSE_MINUTE,
            second=0, microsecond=0,
        )
        if now >= close_time:
            # 이미 장 마감 후 → 내일 장 마감까지
            from datetime import timedelta
            close_time += timedelta(days=1)
            # 주말 건너뛰기
            while close_time.weekday() >= 5:
                close_time += timedelta(days=1)
        return (close_time - now).total_seconds()

    def get(self, key: str):
        """캐시에서 조회. 없거나 만료되면 None."""
        path = self._key_to_path(key)
        if not os.path.exists(path):
            return None

        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)

            expires_at = data.get('expires_at')
            if expires_at is not None and time.time() > expires_at:
                os.remove(path)
                return None

            return data.get('value')
        except Exception as e:
            logger.warning(f"Cache read error for {key}: {e}")
            return None

    def set(self, key: str, value, ttl: str = 'eod'):
        """캐시 저장.

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: 'eod' (장마감까지), 'permanent' (영구), 초 단위 int/float
        """
        path = self._key_to_path(key)

        if ttl == 'permanent':
            expires_at = None
        elif ttl == 'eod':
            expires_at = time.time() + self._get_eod_ttl()
        else:
            expires_at = time.time() + float(ttl)

        data = {
            'value': value,
            'expires_at': expires_at,
            'created_at': time.time(),
        }

        try:
            with open(path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.warning(f"Cache write error for {key}: {e}")

    def invalidate(self, pattern: str = None):
        """캐시 삭제.

        Args:
            pattern: None이면 전체 삭제
        """
        if pattern is None:
            # 전체 삭제
            for f in os.listdir(self.cache_dir):
                if f.endswith('.pkl'):
                    os.remove(os.path.join(self.cache_dir, f))
        else:
            # 패턴 매칭 삭제는 키 → 해시 변환 특성상 전체 스캔 필요
            # 간단히 전체 삭제로 대체
            self.invalidate()

    def cache_decorator(self, ttl: str = 'eod'):
        """메서드 데코레이터 버전.

        Usage:
            cache = FileCache()

            @cache.cache_decorator(ttl='eod')
            def get_price(ticker):
                ...
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 캐시 키 생성
                key_parts = [func.__name__] + [str(a) for a in args]
                key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
                key = '_'.join(key_parts)

                result = self.get(key)
                if result is not None:
                    logger.debug(f"Cache hit: {func.__name__}")
                    return result

                result = func(*args, **kwargs)
                if result is not None:
                    self.set(key, result, ttl=ttl)
                return result
            return wrapper
        return decorator
