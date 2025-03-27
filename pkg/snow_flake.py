from snowflake import SnowflakeGenerator

snowflake_generator = SnowflakeGenerator(1)


def generate_snowflake_id():
    return next(snowflake_generator)
