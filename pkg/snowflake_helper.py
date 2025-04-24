from snowflake import SnowflakeGenerator

# 创建一个 SnowflakeGenerator 实例，传入 node_id
snowflake_generator = SnowflakeGenerator(1)


def generate_snowflake_id():
    return next(snowflake_generator)
