
from solar.interfaces.db.redis_db import RedisDB
from solar.interfaces.db.redis_db import FakeRedisDB

mapping = {
    'redis_db': RedisDB,
    'fakeredis_db': FakeRedisDB
}

DB = None


def get_db():
    # Should be retrieved from config
    global DB
    if DB is None:
        DB = mapping['redis_db']()
    return DB
