from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class InspectRequest(BaseModel):
    endpoint: str = Field(min_length=1, max_length=300)
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET"
    payload: str = Field(default="", max_length=2000)
    request_count: int = Field(default=1, ge=0, le=100000)
    failed_logins: int = Field(default=0, ge=0, le=100000)
    source_ip: str | None = Field(default=None, max_length=64)


class AttackRequest(BaseModel):
    scenario: Literal["full", "rate_abuse", "brute_force", "sql_injection", "xss", "path_traversal"] = "full"


class LaunchSimulationRequest(BaseModel):
    attack_type: str = Field(default="BRUTE_FORCE", max_length=32)
    target_endpoint: str = Field(default="/login", max_length=300)
    intensity: Literal["LOW", "MEDIUM", "HIGH", "EXTREME"] = "MEDIUM"
    duration: int = Field(default=20, ge=5, le=60)


class InstanceFailureRequest(BaseModel):
    instance_id: str = Field(min_length=1, max_length=32)
    down: bool = True


class RuleUpdate(BaseModel):
    enabled: bool
