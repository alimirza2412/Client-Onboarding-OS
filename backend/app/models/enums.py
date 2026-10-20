"""
Enums shared across models. Kept as plain Python str-enums mapped to
native Postgres ENUM types — simple and adequate for a demo; a production
build might make roles/statuses data-driven instead of fixed enums.
"""

import enum


class MemberRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    CLIENT = "CLIENT"


class ClientStatus(str, enum.Enum):
    LEAD = "LEAD"
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class OnboardingInstanceStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class DocumentRequestStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class DocumentReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    AUTO_APPROVED = "AUTO_APPROVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"


class IntegrationProvider(str, enum.Enum):
    GOOGLE = "GOOGLE"
    META = "META"


class IntegrationStatus(str, enum.Enum):
    NOT_CONNECTED = "NOT_CONNECTED"
    CONNECTED = "CONNECTED"
    ACTION_REQUIRED = "ACTION_REQUIRED"


class WorkflowExecutionStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
