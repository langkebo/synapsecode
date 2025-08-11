# Friends Configuration Documentation

## Overview

The friends functionality in Synapse provides a complete social networking layer for Matrix users, including friend requests, friendship management, user blocking, and friend discovery features.

## Configuration

The friends functionality is configured through the `friends` section in your `homeserver.yaml` file.

### Basic Configuration

```yaml
friends:
  # Enable or disable the entire friends functionality
  enabled: true
  
  # Rate limiting configuration
  rate_limiting:
    # Maximum number of friend requests per user per hour
    max_requests_per_hour: 10
    # Time window for rate limiting in seconds
    rate_limit_window: 3600  # 1 hour
```

### Friend Requests Configuration

```yaml
friends:
  requests:
    # Enable or disable friend requests
    enabled: true
    # Require mutual consent for friendships (both users must accept)
    require_mutual_consent: true
    # Automatically accept friend requests (not recommended for production)
    auto_accept: false
    # Maximum length of friend request messages
    message_max_length: 500
    # Friend request expiry time in hours
    expiry_hours: 168  # 7 days
```

### Friends List Configuration

```yaml
friends:
  friends_list:
    # Maximum number of friends per user
    max_friends_per_user: 1000
    # Enable friend suggestions based on mutual connections
    enable_suggestions: false
    # Show online status in friends list
    show_online_status: true
```

### User Blocking Configuration

```yaml
friends:
  blocking:
    # Enable or disable user blocking
    enabled: true
    # Maximum number of blocked users per user
    max_blocked_users: 500
    # Automatically block mutual friends when a user is blocked
    block_mutual_friends: false
```

### Privacy Settings

```yaml
friends:
  privacy:
    # Allow other users to discover this user through friend connections
    allow_friend_discovery: true
    # Show friends list on user profile
    show_friends_in_profile: true
    # Allow friend requests from users who are not already connected
    enable_requests_from_strangers: true
```

### User Search Configuration

```yaml
friends:
  search:
    # Enable user search functionality
    enabled: true
    # Maximum number of search results to return
    result_limit: 20
    # Minimum number of characters required for search
    min_characters: 2
```

### Notification Settings

```yaml
friends:
  notifications:
    # Enable email notifications for friend activities
    email_enabled: true
    # Enable push notifications for friend activities
    push_enabled: true
    # Notify user when they receive a friend request
    on_friend_request: true
    # Notify user when their friend request is accepted
    on_request_accepted: true
    # Notify user when a friend removes them
    on_friend_removed: false
```

## Complete Configuration Example

```yaml
friends:
  enabled: true
  
  rate_limiting:
    max_requests_per_hour: 10
    rate_limit_window: 3600
    
  requests:
    enabled: true
    require_mutual_consent: true
    auto_accept: false
    message_max_length: 500
    expiry_hours: 168
    
  friends_list:
    max_friends_per_user: 1000
    enable_suggestions: false
    show_online_status: true
    
  blocking:
    enabled: true
    max_blocked_users: 500
    block_mutual_friends: false
    
  privacy:
    allow_friend_discovery: true
    show_friends_in_profile: true
    enable_requests_from_strangers: true
    
  search:
    enabled: true
    result_limit: 20
    min_characters: 2
    
  notifications:
    email_enabled: true
    push_enabled: true
    on_friend_request: true
    on_request_accepted: true
    on_friend_removed: false
```

## Database Schema

The friends functionality uses the following database tables:

### user_friendships
Stores friendship relationships between users.

- `user1_id` (TEXT): First user in the friendship
- `user2_id` (TEXT): Second user in the friendship
- `status` (TEXT): Status of the friendship ('active', 'blocked')
- `created_ts` (BIGINT): Timestamp when the friendship was created

### friend_requests
Stores friend requests between users.

- `request_id` (TEXT): Unique identifier for the request
- `sender_user_id` (TEXT): User who sent the request
- `target_user_id` (TEXT): User who received the request
- `message` (TEXT): Optional message with the request
- `status` (TEXT): Status of the request ('pending', 'accepted', 'rejected')
- `created_ts` (BIGINT): Timestamp when the request was created
- `updated_ts` (BIGINT): Timestamp when the request was last updated

### user_blocks
Stores user blocking relationships.

- `blocker_user_id` (TEXT): User who is blocking
- `blocked_user_id` (TEXT): User who is blocked
- `created_ts` (BIGINT): Timestamp when the block was created

## API Endpoints

The friends functionality provides the following REST API endpoints:

### Friend Requests
- `POST /_matrix/client/r0/friends/requests` - Send a friend request
- `GET /_matrix/client/r0/friends/requests/sent` - Get sent friend requests
- `GET /_matrix/client/r0/friends/requests/received` - Get received friend requests
- `PUT /_matrix/client/r0/friends/requests/{request_id}/respond` - Respond to a friend request

### Friends Management
- `GET /_matrix/client/r0/friends` - Get friends list
- `DELETE /_matrix/client/r0/friends/{user_id}` - Remove a friend

### User Blocking
- `PUT /_matrix/client/r0/friends/block/{user_id}` - Block a user
- `DELETE /_matrix/client/r0/friends/block/{user_id}` - Unblock a user
- `GET /_matrix/client/r0/friends/blocked` - Get blocked users list

### User Search
- `GET /_matrix/client/r0/friends/search` - Search for users

## Rate Limiting

The friends functionality includes rate limiting to prevent abuse:

- **Friend requests**: Limited per user per hour (configurable)
- **Redis support**: Distributed rate limiting for multi-process deployments
- **Fallback**: Memory-based rate limiting if Redis is unavailable

## Privacy and Security

### Privacy Controls
- Users can control who can send them friend requests
- Users can block other users to prevent unwanted interactions
- Friends lists can be hidden from user profiles
- Friend discovery can be disabled for enhanced privacy

### Security Features
- Input validation on all user inputs
- Rate limiting to prevent abuse
- Authentication required for all operations
- Authorization checks to ensure users can only modify their own data

## Performance Considerations

### Database Optimization
- Proper indexing on frequently queried columns
- Pagination support for large friends lists
- Efficient queries for friend discovery

### Caching
- Redis-based rate limiting for distributed deployments
- Memory-based caching for frequently accessed data
- Configurable cache expiration times

### Scalability
- Designed to handle large numbers of users and friendships
- Efficient algorithms for friend discovery and suggestions
- Horizontal scaling support with Redis

## Migration

When enabling the friends functionality for the first time, ensure that:

1. The database schema is properly created
2. The configuration is correctly set up
3. All necessary services are running (Redis if used for rate limiting)
4. The friends functionality is enabled in the configuration

## Troubleshooting

### Common Issues

**Friend requests not being sent**
- Check if the friends functionality is enabled
- Verify that friend requests are enabled in the configuration
- Check rate limiting settings

**Rate limiting errors**
- Verify Redis configuration if using Redis for rate limiting
- Check rate limiting settings in the configuration
- Monitor Redis connection status

**Database errors**
- Ensure database schema is properly created
- Check database connection settings
- Verify database permissions

### Logging

The friends functionality includes comprehensive logging:

- INFO: Normal operations (friend requests, responses, etc.)
- WARNING: Potential issues (rate limiting, validation failures)
- ERROR: Critical errors (database failures, authentication issues)

Monitor the logs for troubleshooting and performance optimization.

## Testing

The friends functionality includes comprehensive unit tests covering:

- Configuration validation
- Database operations
- API endpoint functionality
- Rate limiting behavior
- Error handling
- Privacy controls

Run tests with:
```bash
python -m pytest tests/test_friends.py -v
```

## Dependencies

The friends functionality requires:

- Python 3.8+
- Synapse core components
- Redis (optional, for distributed rate limiting)
- Database (PostgreSQL or SQLite)

## Future Enhancements

Planned improvements include:

- Enhanced friend suggestion algorithms
- Group friends functionality
- Friend circles/categories
- Enhanced privacy controls
- Performance optimizations
- Additional API endpoints