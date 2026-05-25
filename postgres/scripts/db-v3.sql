CREATE DATABASE cars;
GRANT ALL PRIVILEGES ON DATABASE cars TO program;

CREATE DATABASE rentals;
GRANT ALL PRIVILEGES ON DATABASE rentals TO program;

CREATE DATABASE payments;
GRANT ALL PRIVILEGES ON DATABASE payments TO program;

CREATE DATABASE identity;
GRANT ALL PRIVILEGES ON DATABASE identity TO program;

CREATE DATABASE statistics;
GRANT ALL PRIVILEGES ON DATABASE statistics TO program;

\connect cars
GRANT USAGE, CREATE ON SCHEMA public TO program;

\connect rentals
GRANT USAGE, CREATE ON SCHEMA public TO program;

\connect payments
GRANT USAGE, CREATE ON SCHEMA public TO program;

\connect identity
GRANT USAGE, CREATE ON SCHEMA public TO program;

\connect statistics
GRANT USAGE, CREATE ON SCHEMA public TO program;