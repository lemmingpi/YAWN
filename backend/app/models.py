"""SQLAlchemy database models for Web Notes API."""

import enum
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    func,
    Index,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import Integer

from .database import Base


class PermissionLevel(enum.Enum):
    """Permission levels for sharing resources."""

    VIEW = "view"  # Read-only access
    EDIT = "edit"  # Read and write access
    ADMIN = "admin"  # Full access including sharing and deletion


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    """User model for multi-user Web Notes application with Chrome Identity integration."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chrome_user_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )  # RFC 5321 maximum email length
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # OAuth token management
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    oauth_scopes: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # Comma-separated scopes

    # Relationships to owned resources
    sites: Mapped[List["Site"]] = relationship(
        "Site", back_populates="user", cascade="all, delete-orphan"
    )
    pages: Mapped[List["Page"]] = relationship(
        "Page", back_populates="user", cascade="all, delete-orphan"
    )
    notes: Mapped[List["Note"]] = relationship(
        "Note", back_populates="user", cascade="all, delete-orphan"
    )

    # Relationships to shared resources
    site_shares: Mapped[List["UserSiteShare"]] = relationship(
        "UserSiteShare", back_populates="user", cascade="all, delete-orphan"
    )
    page_shares: Mapped[List["UserPageShare"]] = relationship(
        "UserPageShare", back_populates="user", cascade="all, delete-orphan"
    )

    # Create explicit index for performance
    __table_args__ = (
        Index("idx_user_chrome_id", "chrome_user_id"),
        Index("idx_user_email", "email"),
        Index("idx_user_active", "is_active"),
    )


class Site(Base, TimestampMixin):
    """Site model representing a domain and its user context."""

    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    domain: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False
    )  # Unique per user, not globally
    user_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sites")
    pages: Mapped[List["Page"]] = relationship(
        "Page", back_populates="site", cascade="all, delete-orphan"
    )
    shared_with: Mapped[List["UserSiteShare"]] = relationship(
        "UserSiteShare", back_populates="site", cascade="all, delete-orphan"
    )

    # Add index for user_id for performance and composite unique constraint
    __table_args__ = (
        Index("idx_site_user_id", "user_id"),
        Index("idx_site_domain_user", "domain", "user_id"),
        Index("ix_sites_domain_user_unique", "domain", "user_id", unique=True),
    )


class Page(Base, TimestampMixin):
    """Page model representing a specific URL and its metadata."""

    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), index=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    page_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Paywall support for auto-note generation
    is_paywalled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the page content is behind a paywall",
    )
    page_source: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Alternate page source text for paywalled content"
    )

    # Foreign Keys
    site_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="pages")
    user: Mapped["User"] = relationship("User", back_populates="pages")
    notes: Mapped[List["Note"]] = relationship(
        "Note", back_populates="page", cascade="all, delete-orphan"
    )
    page_sections: Mapped[List["PageSection"]] = relationship(
        "PageSection", back_populates="page", cascade="all, delete-orphan"
    )
    shared_with: Mapped[List["UserPageShare"]] = relationship(
        "UserPageShare", back_populates="page", cascade="all, delete-orphan"
    )

    # Add indexes for performance
    __table_args__ = (
        Index("idx_page_user_id", "user_id"),
        Index("idx_page_site_user", "site_id", "user_id"),
        Index("idx_page_url_user", "url", "user_id"),
    )


class Note(Base, TimestampMixin):
    """Extended note model with page relationship and server link."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    position_x: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position_y: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    anchor_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the note has been archived (soft delete for auto-generated batches)",
    )
    server_link_id: Mapped[Optional[str]] = mapped_column(
        String(100), index=True, nullable=True
    )

    # Context fields for artifact generation
    highlighted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_section_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Auto-generation tracking for batch operations
    generation_batch_id: Mapped[Optional[str]] = mapped_column(
        String(100), index=True, nullable=True
    )

    # Foreign Keys
    page_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    page: Mapped["Page"] = relationship("Page", back_populates="notes")
    user: Mapped["User"] = relationship("User", back_populates="notes")
    artifacts: Mapped[List["NoteArtifact"]] = relationship(
        "NoteArtifact", back_populates="note", cascade="all, delete-orphan"
    )

    # Add indexes for performance
    __table_args__ = (
        Index("idx_note_user_id", "user_id"),
        Index("idx_note_page_user", "page_id", "user_id"),
    )


class LLMProvider(Base, TimestampMixin):
    """LLM provider configuration model."""

    __tablename__ = "llm_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    provider_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'claude', 'gemini', etc.
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096, nullable=False)
    temperature: Mapped[float] = mapped_column(default=0.7, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    configuration: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    artifacts: Mapped[List["NoteArtifact"]] = relationship(
        "NoteArtifact", back_populates="llm_provider"
    )


class NoteArtifact(Base, TimestampMixin):
    """LLM-generated content artifacts for notes."""

    __tablename__ = "note_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artifact_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'summary', 'expansion', 'scene_image', 'other', etc.
    content: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Image and URL support
    artifact_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Cost tracking
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Generation source: 'app_supplied', 'user_pasted', 'user_api_key', 'browser_native'
    generation_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # For "Other" artifact type
    user_type_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifact_subtype: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Foreign Keys
    note_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    llm_provider_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("llm_providers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    note: Mapped["Note"] = relationship("Note", back_populates="artifacts")
    llm_provider: Mapped[Optional["LLMProvider"]] = relationship(
        "LLMProvider", back_populates="artifacts"
    )


class PageSection(Base, TimestampMixin):
    """Page sections for granular artifact generation."""

    __tablename__ = "page_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    section_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'header', 'paragraph', etc.
    content: Mapped[str] = mapped_column(Text, nullable=False)
    selector: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # CSS selector
    xpath: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    position_in_page: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Foreign Keys
    page_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    page: Mapped["Page"] = relationship("Page", back_populates="page_sections")


class UsageCost(Base, TimestampMixin):
    """Track aggregated usage costs per user/provider/day."""

    __tablename__ = "usage_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    llm_provider_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("llm_providers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    llm_provider: Mapped[Optional["LLMProvider"]] = relationship("LLMProvider")

    # Indexes for performance
    __table_args__ = (
        Index("idx_usage_costs_user_date", "user_id", "date"),
        Index("idx_usage_costs_provider", "llm_provider_id"),
    )


class OtherArtifactRequest(Base, TimestampMixin):
    """Track 'Other' artifact requests to inform future dropdown options."""

    __tablename__ = "other_artifact_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_description: Mapped[str] = mapped_column(Text, nullable=False)
    custom_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Analysis fields (populated manually or via LLM)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    should_add_to_dropdown: Mapped[Optional[bool]] = mapped_column(nullable=True)
    similar_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("note_artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    artifact: Mapped[Optional["NoteArtifact"]] = relationship("NoteArtifact")

    # Indexes for analysis
    __table_args__ = (
        Index("idx_other_requests_category", "category"),
        Index("idx_other_requests_user", "user_id"),
    )


class UserSiteShare(Base, TimestampMixin):
    """Model for sharing sites between users with granular permissions."""

    __tablename__ = "user_site_shares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    permission_level: Mapped[PermissionLevel] = mapped_column(
        Enum(PermissionLevel), nullable=False, default=PermissionLevel.VIEW
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    site_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="site_shares")
    site: Mapped["Site"] = relationship("Site", back_populates="shared_with")

    # Ensure unique sharing per user-site pair
    __table_args__ = (
        Index("idx_user_site_share_unique", "user_id", "site_id", unique=True),
        Index("idx_user_site_share_permission", "permission_level"),
    )


class UserPageShare(Base, TimestampMixin):
    """Model for sharing pages between users with granular permissions."""

    __tablename__ = "user_page_shares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    permission_level: Mapped[PermissionLevel] = mapped_column(
        Enum(PermissionLevel), nullable=False, default=PermissionLevel.VIEW
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="page_shares")
    page: Mapped["Page"] = relationship("Page", back_populates="shared_with")

    # Ensure unique sharing per user-page pair
    __table_args__ = (
        Index("idx_user_page_share_unique", "user_id", "page_id", unique=True),
        Index("idx_user_page_share_permission", "permission_level"),
    )
