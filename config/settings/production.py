from .base import *

DATABASES = {

    'default': dj_database_url.config(
        # Replace this value with your local database's connection string.
        default=config("DATABASE_URL"),
        conn_max_age=600
    )
}
