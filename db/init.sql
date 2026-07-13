
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS raw.users(
    user_id INT PRIMARY KEY,
    test_group VARCHAR(1) CHECK (test_group IN ('A','B')),
    date_registration TIMESTAMP DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS raw.events(
    event_id VARCHAR(50) PRIMARY KEY,
    user_id INT,
    type_event VARCHAR(20) CHECK (type_event IN ('view','click', 'add_to_cart', 'purchase')),
    time_event TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS mart.bi_ab_metrics(
    date DATE DEFAULT CURRENT_DATE,
    name_metrics VARCHAR(25),
    group_A FLOAT,
    group_B FLOAT,
    p_value FLOAT,
    significance_flag BOOLEAN,
    PRIMARY KEY (date, name_metrics)
);