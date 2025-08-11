/* Copyright 2024 OpenMarket Ltd
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

-- 好友关系表
CREATE TABLE IF NOT EXISTS user_friendships (
    user1_id TEXT NOT NULL,
    user2_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'blocked'
    created_ts BIGINT NOT NULL,
    PRIMARY KEY (user1_id, user2_id),
    CONSTRAINT friendship_order CHECK (user1_id < user2_id)
);

-- 为好友关系表创建索引
CREATE INDEX IF NOT EXISTS user_friendships_user1_idx ON user_friendships(user1_id);
CREATE INDEX IF NOT EXISTS user_friendships_user2_idx ON user_friendships(user2_id);
CREATE INDEX IF NOT EXISTS user_friendships_created_ts_idx ON user_friendships(created_ts);

-- 好友请求表
CREATE TABLE IF NOT EXISTS friend_requests (
    request_id TEXT PRIMARY KEY,
    sender_user_id TEXT NOT NULL,
    target_user_id TEXT NOT NULL,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'accepted', 'rejected'
    created_ts BIGINT NOT NULL,
    updated_ts BIGINT NOT NULL
);

-- 为好友请求表创建索引
CREATE INDEX IF NOT EXISTS friend_requests_sender_idx ON friend_requests(sender_user_id);
CREATE INDEX IF NOT EXISTS friend_requests_target_idx ON friend_requests(target_user_id);
CREATE INDEX IF NOT EXISTS friend_requests_status_idx ON friend_requests(status);
CREATE INDEX IF NOT EXISTS friend_requests_created_ts_idx ON friend_requests(created_ts);
CREATE UNIQUE INDEX IF NOT EXISTS friend_requests_sender_target_idx ON friend_requests(sender_user_id, target_user_id);

-- 用户屏蔽表
CREATE TABLE IF NOT EXISTS user_blocks (
    blocker_user_id TEXT NOT NULL,
    blocked_user_id TEXT NOT NULL,
    created_ts BIGINT NOT NULL,
    PRIMARY KEY (blocker_user_id, blocked_user_id)
);

-- 为用户屏蔽表创建索引
CREATE INDEX IF NOT EXISTS user_blocks_blocker_idx ON user_blocks(blocker_user_id);
CREATE INDEX IF NOT EXISTS user_blocks_blocked_idx ON user_blocks(blocked_user_id);
CREATE INDEX IF NOT EXISTS user_blocks_created_ts_idx ON user_blocks(created_ts);