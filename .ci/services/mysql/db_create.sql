CREATE SCHEMA IF NOT EXISTS 'pinocommtest' DEFAULT CHARACTER SET latin1 ;
GRANT ALL PRIVILEGES ON *.* To 'pinocommtest'@'%';

SET GLOBAL max_connections = 500;
SET GLOBAL wait_timeout = 60;
SET global thread_cache_size = 32;
