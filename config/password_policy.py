# Copyright 2019 The Matrix.org Foundation C.I.C.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import Any, Dict, Optional

from synapse.config._base import Config

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = """
# Password policy configuration
password_config:
  # Whether to enable password policy enforcement
  enabled: true
  
  # Minimum password length
  minimum_length: 8
  
  # Maximum password length (0 = no limit)
  maximum_length: 0
  
  # Require at least one lowercase letter
  require_lowercase: true
  
  # Require at least one uppercase letter
  require_uppercase: true
  
  # Require at least one digit
  require_digit: true
  
  # Require at least one symbol/special character
  require_symbol: true
  
  # List of forbidden passwords (common passwords, etc.)
  forbidden_passwords:
    - "password"
    - "123456"
    - "password123"
    - "admin"
    - "root"
    - "guest"
    - "user"
    - "test"
    - "demo"
    - "synapse"
    - "matrix"
  
  # Whether to check against common password lists
  check_common_passwords: true
  
  # Whether to prevent passwords that contain the username
  prevent_username_in_password: true
  
  # Whether to prevent passwords that contain the server name
  prevent_server_name_in_password: true
  
  # Minimum password strength score (0-4, based on zxcvbn if available)
  minimum_strength_score: 2
"""


class PasswordPolicyConfig(Config):
    """Configuration for password policy enforcement."""
    
    section = "password_policy"
    
    def __init__(self, root_config: Optional[Dict[str, Any]] = None):
        super().__init__(root_config)
        
        # Default values
        self.enabled = True
        self.minimum_length = 8
        self.maximum_length = 0  # No limit
        self.require_lowercase = True
        self.require_uppercase = True
        self.require_digit = True
        self.require_symbol = True
        self.forbidden_passwords = [
            "password", "123456", "password123", "admin", "root",
            "guest", "user", "test", "demo", "synapse", "matrix"
        ]
        self.check_common_passwords = True
        self.prevent_username_in_password = True
        self.prevent_server_name_in_password = True
        self.minimum_strength_score = 2
        
    def read_config(self, config: Dict[str, Any], **kwargs: Any) -> None:
        """Read password policy configuration from config dict."""
        password_config = config.get("password_config", {})
        
        self.enabled = password_config.get("enabled", True)
        self.minimum_length = password_config.get("minimum_length", 8)
        self.maximum_length = password_config.get("maximum_length", 0)
        self.require_lowercase = password_config.get("require_lowercase", True)
        self.require_uppercase = password_config.get("require_uppercase", True)
        self.require_digit = password_config.get("require_digit", True)
        self.require_symbol = password_config.get("require_symbol", True)
        
        # Forbidden passwords list
        self.forbidden_passwords = password_config.get("forbidden_passwords", [
            "password", "123456", "password123", "admin", "root",
            "guest", "user", "test", "demo", "synapse", "matrix"
        ])
        
        self.check_common_passwords = password_config.get("check_common_passwords", True)
        self.prevent_username_in_password = password_config.get("prevent_username_in_password", True)
        self.prevent_server_name_in_password = password_config.get("prevent_server_name_in_password", True)
        self.minimum_strength_score = password_config.get("minimum_strength_score", 2)
        
        # Validate configuration
        self._validate_config()
        
    def _validate_config(self) -> None:
        """Validate the password policy configuration."""
        if self.minimum_length < 1:
            raise ValueError("minimum_length must be at least 1")
            
        if self.maximum_length > 0 and self.maximum_length < self.minimum_length:
            raise ValueError("maximum_length must be greater than minimum_length")
            
        if not isinstance(self.forbidden_passwords, list):
            raise ValueError("forbidden_passwords must be a list")
            
        if self.minimum_strength_score < 0 or self.minimum_strength_score > 4:
            raise ValueError("minimum_strength_score must be between 0 and 4")
            
    def generate_config_section(self, data_dir_path: str, **kwargs: Any) -> str:
        """Generate the password policy configuration section."""
        return DEFAULT_CONFIG
        
    def validate_password(self, password: str, username: str = None, 
                         server_name: str = None) -> tuple[bool, str]:
        """Validate a password against the configured policy.
        
        Args:
            password: The password to validate.
            username: The username (optional).
            server_name: The server name (optional).
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not self.enabled:
            return True, ""
            
        # Check minimum length
        if len(password) < self.minimum_length:
            return False, f"Password must be at least {self.minimum_length} characters long"
            
        # Check maximum length
        if self.maximum_length > 0 and len(password) > self.maximum_length:
            return False, f"Password must be no more than {self.maximum_length} characters long"
            
        # Check character requirements
        if self.require_lowercase and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
            
        if self.require_uppercase and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
            
        if self.require_digit and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
            
        if self.require_symbol and password.isalnum():
            return False, "Password must contain at least one symbol or special character"
            
        # Check forbidden passwords
        if password.lower() in [p.lower() for p in self.forbidden_passwords]:
            return False, "This password is not allowed"
            
        # Check username in password
        if (self.prevent_username_in_password and username and 
            username.lower() in password.lower()):
            return False, "Password must not contain the username"
            
        # Check server name in password
        if (self.prevent_server_name_in_password and server_name and 
            server_name.lower() in password.lower()):
            return False, "Password must not contain the server name"
            
        # Check common passwords (basic implementation)
        if self.check_common_passwords:
            common_passwords = [
                "password", "123456", "123456789", "qwerty", "abc123",
                "password123", "admin", "letmein", "welcome", "monkey",
                "1234567890", "dragon", "master", "hello", "freedom"
            ]
            if password.lower() in common_passwords:
                return False, "This password is too common"
                
        # Check password strength (basic implementation)
        strength_score = self._calculate_strength_score(password)
        if strength_score < self.minimum_strength_score:
            return False, f"Password is too weak (strength: {strength_score}/{4})"
            
        return True, ""
        
    def _calculate_strength_score(self, password: str) -> int:
        """Calculate a basic password strength score (0-4).
        
        Args:
            password: The password to score.
            
        Returns:
            A strength score from 0 (weakest) to 4 (strongest).
        """
        score = 0
        
        # Length bonus
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
            
        # Character variety bonus
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = not password.isalnum()
        
        char_variety = sum([has_lower, has_upper, has_digit, has_symbol])
        if char_variety >= 3:
            score += 1
        if char_variety >= 4:
            score += 1
            
        return min(score, 4)
        
    def get_policy_description(self) -> str:
        """Get a human-readable description of the password policy.
        
        Returns:
            A description of the current password policy.
        """
        if not self.enabled:
            return "No password policy enforced"
            
        requirements = []
        
        if self.minimum_length > 0:
            requirements.append(f"at least {self.minimum_length} characters")
            
        if self.maximum_length > 0:
            requirements.append(f"no more than {self.maximum_length} characters")
            
        if self.require_lowercase:
            requirements.append("at least one lowercase letter")
            
        if self.require_uppercase:
            requirements.append("at least one uppercase letter")
            
        if self.require_digit:
            requirements.append("at least one digit")
            
        if self.require_symbol:
            requirements.append("at least one symbol")
            
        policy_desc = "Password must contain: " + ", ".join(requirements)
        
        if self.minimum_strength_score > 0:
            policy_desc += f". Minimum strength score: {self.minimum_strength_score}/4"
            
        return policy_desc