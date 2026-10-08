-- CloudSentry PostgreSQL schema (generated from the SQLAlchemy models).
-- You do NOT need to run this: the backend creates these tables automatically on first start.

CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	"user" VARCHAR(64) NOT NULL, 
	event VARCHAR(300) NOT NULL, 
	source_ip VARCHAR(64) NOT NULL, 
	threat_type VARCHAR(24), 
	risk_score INTEGER, 
	severity VARCHAR(10), 
	action VARCHAR(10), 
	instance_id VARCHAR(32) NOT NULL, 
	event_id INTEGER, 
	source VARCHAR(12) NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_source ON audit_logs (source);
CREATE INDEX ix_audit_logs_threat_type ON audit_logs (threat_type);
CREATE INDEX ix_audit_logs_timestamp ON audit_logs (timestamp);

CREATE TABLE instances (
	id VARCHAR(32) NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	last_heartbeat TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	forced_down BOOLEAN NOT NULL, 
	mode VARCHAR(10) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE security_rules (
	id SERIAL NOT NULL, 
	key VARCHAR(32) NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	description TEXT NOT NULL, 
	category VARCHAR(16) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	toggleable BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (key)
);

CREATE TABLE simulation_state (
	id SERIAL NOT NULL, 
	active BOOLEAN NOT NULL, 
	run_id VARCHAR(36) NOT NULL, 
	scenario VARCHAR(24) NOT NULL, 
	phase INTEGER NOT NULL, 
	phases_total INTEGER NOT NULL, 
	current_rps INTEGER NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE traffic_events (
	id SERIAL NOT NULL, 
	request_id VARCHAR(36) NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	source_ip VARCHAR(64) NOT NULL, 
	endpoint VARCHAR(300) NOT NULL, 
	method VARCHAR(10) NOT NULL, 
	status_code INTEGER NOT NULL, 
	response_time FLOAT NOT NULL, 
	request_count INTEGER NOT NULL, 
	failed_logins INTEGER NOT NULL, 
	payload_size INTEGER NOT NULL, 
	payload TEXT NOT NULL, 
	user_role VARCHAR(16) NOT NULL, 
	username VARCHAR(64), 
	threat_type VARCHAR(24) NOT NULL, 
	risk_score INTEGER NOT NULL, 
	severity VARCHAR(10) NOT NULL, 
	action VARCHAR(10) NOT NULL, 
	reason TEXT NOT NULL, 
	instance_id VARCHAR(32) NOT NULL, 
	source VARCHAR(12) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (request_id)
);
CREATE INDEX ix_traffic_events_action ON traffic_events (action);
CREATE INDEX ix_traffic_events_source ON traffic_events (source);
CREATE INDEX ix_traffic_events_source_ip ON traffic_events (source_ip);
CREATE INDEX ix_traffic_events_threat_type ON traffic_events (threat_type);
CREATE INDEX ix_traffic_events_timestamp ON traffic_events (timestamp);

CREATE TABLE traffic_ticks (
	id SERIAL NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	rps INTEGER NOT NULL, 
	blocked_rps INTEGER NOT NULL, 
	throttled_rps INTEGER NOT NULL, 
	source VARCHAR(12) NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_traffic_ticks_timestamp ON traffic_ticks (timestamp);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	username VARCHAR(64) NOT NULL, 
	password_hash VARCHAR(128) NOT NULL, 
	role VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_username ON users (username);
