# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a custom fork of the Synapse Matrix homeserver with enhanced friends functionality. The project extends the standard Matrix protocol with additional social networking features including friend requests, friend lists, and cross-domain friend relationships.

## Development Commands

### Running the Server
```bash
# Start the homeserver
python -m synapse.app.homeserver

# Generate configuration
python -m synapse.app.homeserver --server-name=your.domain --config-path=homeserver.yaml --generate-config

# Control script (deprecated but available)
python -m synapse._scripts.synctl start/stop/restart
```

### Database Operations
```bash
# Upgrade database schema
python -m synapse._scripts.update_synapse_database

# Generate signing key
python -m synapse._scripts.generate_signing_key

# Hash password for config
python -m synapse._scripts.hash_password
```

### User Management
```bash
# Register new user
python -m synapse._scripts.register_new_matrix_user

# Generate config files
python -m synapse._scripts.generate_config
python -m synapse._scripts.generate_log_config
```

### Testing
The project uses pytest for testing. Tests are located in the `tests/` directory (not visible in current structure but standard for Synapse).

## Architecture

### Core Components

**Homeserver Application (`synapse/app/`)**
- `homeserver.py` - Main homeserver implementation
- `generic_worker.py` - Base worker implementation
- Various specialized workers (federation, sync, media, etc.)

**Request Handling (`synapse/handlers/`)**
- `friends.py` - Custom friends management functionality
- `room.py` - Room operations
- `sync.py` - Sync operations
- `federation.py` - Federation handling

**Storage Layer (`synapse/storage/`)**
- `databases/main/` - Main database tables and operations
- `friends.py` - Friends-specific database operations
- `engines/` - Database engine abstraction (PostgreSQL, SQLite)

**HTTP API (`synapse/rest/`)**
- `client/` - Client-server API endpoints
- `admin/` - Admin API endpoints
- `federation/` - Federation API endpoints
- `friends.py` - Friends-specific API endpoints

### Key Features

**Friends System**
- Friend requests with pending/accepted/rejected states
- Friend list management with active/blocked states
- Rate limiting for friend requests (10 per hour per user)
- Cross-domain friend support
- Database-backed persistence in `friends` table

**Configuration System**
- YAML-based configuration in `synapse/config/`
- Friends-specific configuration options
- Database, cache, and worker configuration

**Federation**
- Matrix federation protocol implementation
- Cross-server communication
- Event signing and verification

### Database Schema

The project uses a complex database schema with migration files in `storage/schema/main/delta/`. Key friends-related tables:
- `friends` - Stores friend relationships and requests
- Standard Matrix tables for rooms, events, users, etc.

### Configuration

Main configuration is in `homeserver.yaml`. Key friends-related settings:
```yaml
friends:
  enabled: true
  max_friends_per_user: 1000
  friend_request_timeout: 604800
  allow_cross_domain_friends: true
```

## Development Notes

### Dependencies
- Uses Poetry for dependency management (evident from deployment docs)
- Main dependencies: Twisted, PostgreSQL, psycopg2, various Python packages
- Optional dependencies for different features (SAML, OIDC, etc.)

### Code Style
- Follows standard Python conventions
- Extensive type hints throughout
- Async/await patterns for I/O operations
- Comprehensive error handling with custom exception types

### Testing
- Standard pytest setup (inferred from structure)
- Unit tests for handlers and storage
- Integration tests for API endpoints
- Performance testing for scalability

### Custom Extensions
The main customizations are:
1. Friends functionality in `handlers/friends.py`
2. Friends API in `rest/client/friends.py`
3. Friends storage in `storage/databases/main/friends.py`
4. Friends configuration options

### Deployment
The project includes Docker deployment configuration in `UBUNTU_DOCKER_DEPLOYMENT_MINIMAL.md` with:
- Docker Compose setup
- Nginx proxy configuration
- PostgreSQL database
- SSL/TLS configuration
- Environment-based configuration

## Important Files

- `synapse/app/homeserver.py` - Main homeserver entry point
- `synapse/handlers/friends.py` - Friends business logic
- `synapse/rest/client/friends.py` - Friends API endpoints
- `synapse/storage/databases/main/friends.py` - Friends data access
- `synapse/config/experimental.py` - Friends configuration
- `server.py` - Server startup script