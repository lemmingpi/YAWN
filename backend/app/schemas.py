"""Pydantic schemas for API request/response models.

This module defines all the data validation and serialization schemas
used by the FastAPI endpoints for the Web Notes API.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    """Permission levels for sharing resources."""

    VIEW = "view"  # Read-only access
    EDIT = "edit"  # Read and write access
    ADMIN = "admin"  # Full access including sharing and deletion


# Base schemas
class TimestampSchema(BaseModel):
    """Base schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


# User schemas
class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: str = Field(
        ..., min_length=3, max_length=320, description="User email address"
    )
    display_name: str = Field(
        ..., min_length=1, max_length=255, description="User display name"
    )
    is_admin: bool = Field(False, description="Whether the user has admin privileges")
    is_active: bool = Field(True, description="Whether the user account is active")


class UserCreate(BaseModel):
    """Schema for creating a new user with Chrome Identity token."""

    chrome_token: str = Field(..., min_length=1, description="Chrome Identity token")
    display_name: Optional[str] = Field(
        None, max_length=255, description="Optional display name override"
    )


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase, TimestampSchema):
    """Schema for user API responses."""

    id: int
    chrome_user_id: str = Field(..., description="Chrome user ID")

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login with Chrome Identity token."""

    chrome_token: str = Field(..., min_length=1, description="Chrome Identity token")


class TokenResponse(BaseModel):
    """Schema for authentication token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")


class TokenData(BaseModel):
    """Schema for token data validation."""

    user_id: Optional[int] = None
    chrome_user_id: Optional[str] = None
    email: Optional[str] = None


# Site schemas
class SiteBase(BaseModel):
    """Base site schema with common fields."""

    domain: str = Field(..., min_length=1, max_length=255, description="Domain name")
    user_context: Optional[str] = Field(
        None, description="User-defined context for this site"
    )
    is_active: bool = Field(True, description="Whether the site is active")


class SiteCreate(SiteBase):
    """Schema for creating a new site."""

    pass


class SiteUpdate(BaseModel):
    """Schema for updating an existing site."""

    domain: Optional[str] = Field(None, min_length=1, max_length=255)
    user_context: Optional[str] = None
    is_active: Optional[bool] = None


class SiteResponse(SiteBase, TimestampSchema):
    """Schema for site API responses."""

    id: int
    user_id: int = Field(..., description="ID of the site owner")
    pages_count: Optional[int] = Field(
        None, description="Number of pages associated with this site"
    )
    notes_count: Optional[int] = Field(
        None, description="Number of notes associated with this site"
    )

    class Config:
        from_attributes = True


# Page schemas
class PageBase(BaseModel):
    """Base page schema with common fields."""

    url: str = Field(
        ..., min_length=1, max_length=2048, description="Full URL of the page"
    )
    title: Optional[str] = Field(None, max_length=500, description="Page title")
    page_summary: Optional[str] = Field(
        None, description="AI-generated summary of the page"
    )
    user_context: Optional[str] = Field(
        None, description="User-defined context for this page"
    )
    is_active: bool = Field(True, description="Whether the page is active")


class PageCreate(PageBase):
    """Schema for creating a new page."""

    site_id: int = Field(..., description="ID of the associated site")


class PageCreateWithURL(BaseModel):
    """Schema for creating a new page with URL (auto-creates site if needed)."""

    url: str = Field(..., min_length=1, max_length=2048, description="Page URL")
    title: Optional[str] = Field(None, max_length=500, description="Page title")


class PageUpdate(BaseModel):
    """Schema for updating an existing page."""

    url: Optional[str] = Field(None, min_length=1, max_length=2048)
    title: Optional[str] = Field(None, max_length=500)
    page_summary: Optional[str] = None
    user_context: Optional[str] = None
    is_active: Optional[bool] = None
    site_id: Optional[int] = None


class PageResponse(PageBase, TimestampSchema):
    """Schema for page API responses."""

    id: int
    site_id: int
    user_id: int = Field(..., description="ID of the page owner")
    notes_count: Optional[int] = Field(None, description="Number of notes on this page")
    sections_count: Optional[int] = Field(
        None, description="Number of sections extracted from this page"
    )

    class Config:
        from_attributes = True


# Note schemas
class NoteBase(BaseModel):
    """Base note schema with common fields."""

    content: str = Field(..., min_length=1, description="Note content")
    position_x: Optional[int] = Field(
        None, description="X coordinate for note positioning"
    )
    position_y: Optional[int] = Field(
        None, description="Y coordinate for note positioning"
    )
    anchor_data: Optional[Dict[str, Any]] = Field(
        None, description="DOM anchoring data as JSON"
    )
    is_active: bool = Field(True, description="Whether the note is active")
    server_link_id: Optional[str] = Field(
        None, max_length=100, description="External reference ID"
    )


class NoteCreate(NoteBase):
    """Schema for creating a new note."""

    page_id: int = Field(..., description="ID of the associated page")


class NoteCreateWithURL(NoteBase):
    """Schema for creating a new note with URL (auto-creates page/site)."""

    url: str = Field(..., description="URL of the page for this note")
    page_title: Optional[str] = Field(None, description="Title of the page (optional)")


class NoteUpdate(BaseModel):
    """Schema for updating an existing note."""

    content: Optional[str] = Field(None, min_length=1)
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    anchor_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    server_link_id: Optional[str] = Field(None, max_length=100)
    page_id: Optional[int] = None


class NoteResponse(NoteBase, TimestampSchema):
    """Schema for note API responses."""

    id: int
    page_id: int
    user_id: int = Field(..., description="ID of the note owner")
    artifacts_count: Optional[int] = Field(
        None, description="Number of artifacts generated for this note"
    )

    class Config:
        from_attributes = True


# LLM Provider schemas
class LLMProviderBase(BaseModel):
    """Base LLM provider schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Provider name")
    provider_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Provider type (e.g., 'claude', 'gemini')",
    )
    api_endpoint: Optional[str] = Field(
        None, max_length=255, description="API endpoint URL"
    )
    model_name: str = Field(..., min_length=1, max_length=100, description="Model name")
    max_tokens: int = Field(
        4096, gt=0, le=100000, description="Maximum tokens for generation"
    )
    temperature: float = Field(
        0.7, ge=0.0, le=2.0, description="Generation temperature"
    )
    is_active: bool = Field(True, description="Whether the provider is active")
    configuration: Optional[Dict[str, Any]] = Field(
        None, description="Additional provider configuration"
    )


class LLMProviderCreate(LLMProviderBase):
    """Schema for creating a new LLM provider."""

    pass


class LLMProviderUpdate(BaseModel):
    """Schema for updating an existing LLM provider."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider_type: Optional[str] = Field(None, min_length=1, max_length=50)
    api_endpoint: Optional[str] = Field(None, max_length=255)
    model_name: Optional[str] = Field(None, min_length=1, max_length=100)
    max_tokens: Optional[int] = Field(None, gt=0, le=100000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    is_active: Optional[bool] = None
    configuration: Optional[Dict[str, Any]] = None


class LLMProviderResponse(LLMProviderBase, TimestampSchema):
    """Schema for LLM provider API responses."""

    id: int
    artifacts_count: Optional[int] = Field(
        None, description="Number of artifacts generated by this provider"
    )

    class Config:
        from_attributes = True


# Note Artifact schemas
class NoteArtifactBase(BaseModel):
    """Base note artifact schema with common fields."""

    artifact_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of artifact (e.g., 'summary', 'expansion')",
    )
    content: str = Field(..., min_length=1, description="Generated content")
    prompt_used: Optional[str] = Field(None, description="Prompt used for generation")
    generation_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Metadata about the generation process"
    )
    is_active: bool = Field(True, description="Whether the artifact is active")


class NoteArtifactCreate(NoteArtifactBase):
    """Schema for creating a new note artifact."""

    note_id: int = Field(..., description="ID of the associated note")
    llm_provider_id: int = Field(..., description="ID of the LLM provider used")


class NoteArtifactUpdate(BaseModel):
    """Schema for updating an existing note artifact."""

    artifact_type: Optional[str] = Field(None, min_length=1, max_length=50)
    content: Optional[str] = Field(None, min_length=1)
    prompt_used: Optional[str] = None
    generation_metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class NoteArtifactResponse(NoteArtifactBase, TimestampSchema):
    """Schema for note artifact API responses."""

    id: int
    note_id: int
    llm_provider_id: int

    class Config:
        from_attributes = True


# Page Section schemas
class PageSectionBase(BaseModel):
    """Base page section schema with common fields."""

    section_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of section (e.g., 'header', 'paragraph')",
    )
    content: str = Field(..., min_length=1, description="Section content")
    selector: Optional[str] = Field(
        None, max_length=500, description="CSS selector for the section"
    )
    xpath: Optional[str] = Field(
        None, max_length=500, description="XPath for the section"
    )
    position_in_page: int = Field(
        ..., ge=0, description="Position of section within the page"
    )
    is_active: bool = Field(True, description="Whether the section is active")


class PageSectionCreate(PageSectionBase):
    """Schema for creating a new page section."""

    page_id: int = Field(..., description="ID of the associated page")


class PageSectionUpdate(BaseModel):
    """Schema for updating an existing page section."""

    section_type: Optional[str] = Field(None, min_length=1, max_length=50)
    content: Optional[str] = Field(None, min_length=1)
    selector: Optional[str] = Field(None, max_length=500)
    xpath: Optional[str] = Field(None, max_length=500)
    position_in_page: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class PageSectionResponse(PageSectionBase, TimestampSchema):
    """Schema for page section API responses."""

    id: int
    page_id: int

    class Config:
        from_attributes = True


# Artifact generation request schemas
class ArtifactGenerationRequest(BaseModel):
    """Schema for artifact generation requests."""

    note_id: int = Field(..., description="ID of the note to generate artifact for")
    artifact_type: str = Field(
        ..., min_length=1, max_length=50, description="Type of artifact to generate"
    )
    llm_provider_id: int = Field(..., description="ID of the LLM provider to use")
    custom_prompt: Optional[str] = Field(
        None, description="Custom prompt to use instead of default template"
    )
    generation_options: Optional[Dict[str, Any]] = Field(
        None, description="Additional generation options"
    )


class ArtifactGenerationResponse(BaseModel):
    """Schema for artifact generation responses."""

    artifact_id: int = Field(..., description="ID of the generated artifact")
    content: str = Field(..., description="Generated content")
    generation_time_ms: int = Field(
        ..., description="Time taken for generation in milliseconds"
    )
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")


class ArtifactPreviewRequest(BaseModel):
    """Schema for artifact preview requests (no generation)."""

    artifact_type: str = Field(
        ..., min_length=1, max_length=50, description="Type of artifact to preview"
    )
    custom_prompt: Optional[str] = Field(None, description="Custom user instructions")


class ArtifactPreviewResponse(BaseModel):
    """Schema for artifact preview responses."""

    prompt: str = Field(..., description="Full prompt that would be sent to LLM")
    estimated_input_tokens: int = Field(..., description="Estimated input token count")
    estimated_output_tokens: int = Field(
        default=1000, description="Estimated output token count (default assumption)"
    )
    estimated_cost_usd: float = Field(..., description="Estimated cost in USD")
    model: str = Field(..., description="Model that would be used")
    context_summary: dict = Field(..., description="Summary of available context")


class ArtifactPasteRequest(BaseModel):
    """Schema for manually pasted artifact content."""

    note_id: int = Field(..., description="ID of the note this artifact is for")
    artifact_type: str = Field(
        ..., min_length=1, max_length=50, description="Type of artifact"
    )
    content: str = Field(..., min_length=1, description="Pasted artifact content")
    source_model: Optional[str] = Field(
        None, description="Model used (if known, e.g., 'ChatGPT', 'Claude', 'Gemini')"
    )
    prompt_used: Optional[str] = Field(
        None, description="Prompt that was used (if available)"
    )
    user_notes: Optional[str] = Field(
        None, max_length=500, description="Optional user notes about this artifact"
    )


class ArtifactPasteResponse(BaseModel):
    """Schema for pasted artifact response."""

    artifact_id: int = Field(..., description="ID of the created artifact")
    note_id: int = Field(..., description="ID of the associated note")
    artifact_type: str = Field(..., description="Type of artifact")
    generation_source: str = Field(
        default="user_pasted", description="Source of generation"
    )
    created_at: datetime = Field(..., description="When the artifact was created")


class UsageSummary(BaseModel):
    """Summary of artifact generation usage."""

    total_artifacts: int = Field(..., description="Total number of artifacts generated")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    total_input_tokens: int = Field(..., description="Total input tokens consumed")
    total_output_tokens: int = Field(..., description="Total output tokens generated")
    by_type: dict = Field(..., description="Breakdown by artifact type")
    by_source: dict = Field(..., description="Breakdown by generation source")
    by_model: dict = Field(..., description="Breakdown by LLM model")


class UsageResponse(BaseModel):
    """Response for usage endpoint."""

    period_start: Optional[datetime] = Field(
        None, description="Start of period queried"
    )
    period_end: Optional[datetime] = Field(None, description="End of period queried")
    summary: UsageSummary = Field(..., description="Usage summary")


class TypePopularity(BaseModel):
    """Popularity metrics for an artifact type."""

    artifact_type: str = Field(..., description="Type of artifact")
    count: int = Field(..., description="Number of artifacts")
    percentage: float = Field(..., description="Percentage of total")


class DailyCost(BaseModel):
    """Daily cost metrics."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    cost: float = Field(..., description="Cost in USD")
    count: int = Field(..., description="Number of artifacts")


class AnalyticsSummary(BaseModel):
    """Analytics summary data."""

    total_artifacts: int = Field(..., description="Total artifacts generated")
    successful_generations: int = Field(
        ..., description="Number of successful API generations"
    )
    pasted_artifacts: int = Field(..., description="Number of user-pasted artifacts")
    success_rate: float = Field(
        ..., description="Success rate for API generations (percentage)"
    )
    popular_types: List[TypePopularity] = Field(
        ..., description="Most popular artifact types"
    )
    daily_costs: List[DailyCost] = Field(..., description="Daily cost trends")


class AnalyticsResponse(BaseModel):
    """Response for analytics endpoint."""

    period_start: Optional[datetime] = Field(
        None, description="Start of period queried"
    )
    period_end: Optional[datetime] = Field(None, description="End of period queried")
    analytics: AnalyticsSummary = Field(..., description="Analytics data")


# Page summarization request schemas
class PageSummarizationRequest(BaseModel):
    """Schema for page summarization requests."""

    page_id: int = Field(..., description="ID of the page to summarize")
    llm_provider_id: int = Field(..., description="ID of the LLM provider to use")
    summary_type: str = Field(
        "general",
        description="Type of summary (e.g., 'general', 'technical', 'key_points')",
    )
    custom_prompt: Optional[str] = Field(
        None, description="Custom prompt for summarization"
    )


class PageSummarizationResponse(BaseModel):
    """Schema for page summarization responses."""

    page_id: int = Field(..., description="ID of the summarized page")
    summary: str = Field(..., description="Generated summary")
    generation_time_ms: int = Field(
        ..., description="Time taken for generation in milliseconds"
    )
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")


class PageContextGenerationRequest(BaseModel):
    """Schema for AI-powered page context generation requests."""

    llm_provider_id: int = Field(..., description="ID of the LLM provider to use")
    custom_instructions: Optional[str] = Field(
        None,
        description="Optional custom instructions to guide context generation",
    )
    page_source: Optional[str] = Field(
        None,
        description="Optional alternate page source (for paywalled content)",
    )


class PageContextGenerationResponse(BaseModel):
    """Schema for page context generation responses."""

    user_context: str = Field(..., description="Generated context summary for the page")
    detected_content_type: str = Field(
        ..., description="Content type detected by the LLM"
    )
    tokens_used: int = Field(..., description="Total tokens consumed")
    cost_usd: float = Field(..., description="Generation cost in USD")
    generation_time_ms: int = Field(
        ..., description="Time taken for generation in milliseconds"
    )
    input_tokens: int = Field(..., description="Input token count")
    output_tokens: int = Field(..., description="Output token count")


class PageContextPreviewRequest(BaseModel):
    """Schema for preview prompt request."""

    custom_instructions: Optional[str] = Field(
        None,
        description="Optional custom instructions to include in preview",
    )
    page_source: Optional[str] = Field(
        None,
        description="Optional alternate page source",
    )


class PageContextPreviewResponse(BaseModel):
    """Schema for preview prompt response."""

    prompt: str = Field(
        ..., description="The full rendered prompt that would be sent to the LLM"
    )


# Bulk operation schemas
class BulkNoteCreate(BaseModel):
    """Schema for bulk note creation."""

    notes: List[NoteCreate] = Field(
        ..., min_length=1, max_length=100, description="List of notes to create"
    )


class BulkNoteCreateWithURL(BaseModel):
    """Schema for bulk note creation with URLs."""

    notes: List[NoteCreateWithURL] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of notes to create with URLs",
    )


class BulkNoteResponse(BaseModel):
    """Schema for bulk note creation response."""

    created_notes: List[NoteResponse] = Field(
        ..., description="Successfully created notes"
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list, description="Errors encountered during creation"
    )


# Health check schema
class HealthCheckResponse(BaseModel):
    """Schema for health check responses."""

    status: str = Field(..., description="Health status")
    message: str = Field(..., description="Health check message")
    timestamp: datetime = Field(..., description="Timestamp of the health check")
    database_connected: bool = Field(
        ..., description="Whether database connection is working"
    )


# Sharing schemas
class ShareCreate(BaseModel):
    """Schema for creating a new share with email-based user lookup."""

    user_email: str = Field(
        ...,
        min_length=3,
        max_length=320,
        description="Email address of the user to share with",
    )
    permission_level: PermissionLevel = Field(
        PermissionLevel.VIEW, description="Permission level for the share"
    )


class ShareUpdate(BaseModel):
    """Schema for updating an existing share."""

    permission_level: Optional[PermissionLevel] = Field(
        None, description="New permission level for the share"
    )
    is_active: Optional[bool] = Field(
        None, description="Whether the share should be active"
    )


class ShareResponse(BaseModel):
    """Schema for share API responses."""

    id: int
    user_id: int = Field(..., description="ID of the user the resource is shared with")
    user_email: str = Field(
        ..., description="Email of the user the resource is shared with"
    )
    user_display_name: str = Field(..., description="Display name of the user")
    permission_level: PermissionLevel = Field(..., description="Permission level")
    is_active: bool = Field(..., description="Whether the share is active")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SiteShareResponse(ShareResponse):
    """Schema for site share API responses."""

    site_id: int = Field(..., description="ID of the shared site")
    site_domain: str = Field(..., description="Domain of the shared site")


class PageShareResponse(ShareResponse):
    """Schema for page share API responses."""

    page_id: int = Field(..., description="ID of the shared page")
    page_url: str = Field(..., description="URL of the shared page")
    page_title: Optional[str] = Field(None, description="Title of the shared page")


class MySharesResponse(BaseModel):
    """Schema for user's own shares."""

    shared_sites: List[SiteShareResponse] = Field(
        default_factory=list, description="Sites shared with the user"
    )
    shared_pages: List[PageShareResponse] = Field(
        default_factory=list, description="Pages shared with the user"
    )


class InviteCreate(BaseModel):
    """Schema for inviting a user by email (pre-registration)."""

    user_email: str = Field(
        ..., min_length=3, max_length=320, description="Email address to invite"
    )
    resource_type: str = Field(
        ...,
        pattern="^(site|page)$",
        description="Type of resource to share (site or page)",
    )
    resource_id: int = Field(..., description="ID of the resource to share")
    permission_level: PermissionLevel = Field(
        PermissionLevel.VIEW, description="Permission level for the share"
    )
    invitation_message: Optional[str] = Field(
        None, max_length=500, description="Optional invitation message"
    )


class InviteResponse(BaseModel):
    """Schema for invite responses."""

    invite_id: str = Field(..., description="Unique invite ID")
    user_email: str = Field(..., description="Email address invited")
    resource_type: str = Field(..., description="Type of resource shared")
    resource_id: int = Field(..., description="ID of the resource")
    permission_level: PermissionLevel = Field(..., description="Permission level")
    invitation_message: Optional[str] = Field(None, description="Invitation message")
    invited_by_email: str = Field(
        ..., description="Email of the user who sent the invite"
    )
    expires_at: Optional[datetime] = Field(None, description="When the invite expires")
    is_accepted: bool = Field(False, description="Whether the invite has been accepted")
    created_at: datetime


# Legacy sharing schemas for backward compatibility
class UserSiteShareBase(BaseModel):
    """Base schema for site sharing."""

    permission_level: PermissionLevel = Field(
        PermissionLevel.VIEW, description="Permission level for the share"
    )
    is_active: bool = Field(True, description="Whether the share is active")


class UserSiteShareCreate(BaseModel):
    """Schema for creating a new site share."""

    user_id: int = Field(..., description="ID of the user to share with")
    site_id: int = Field(..., description="ID of the site to share")
    permission_level: PermissionLevel = Field(
        PermissionLevel.VIEW, description="Permission level for the share"
    )


class UserSiteShareUpdate(BaseModel):
    """Schema for updating an existing site share."""

    permission_level: Optional[PermissionLevel] = None
    is_active: Optional[bool] = None


class UserSiteShareResponse(UserSiteShareBase, TimestampSchema):
    """Schema for site share API responses."""

    id: int
    user_id: int = Field(..., description="ID of the user the site is shared with")
    site_id: int = Field(..., description="ID of the shared site")
    user: Optional[UserResponse] = Field(None, description="User details")
    site: Optional[SiteResponse] = Field(None, description="Site details")

    class Config:
        from_attributes = True


class UserPageShareBase(BaseModel):
    """Base schema for page sharing."""

    permission_level: PermissionLevel = Field(
        PermissionLevel.VIEW, description="Permission level for the share"
    )
    is_active: bool = Field(True, description="Whether the share is active")


class UserPageShareCreate(BaseModel):
    """Schema for creating a new page share."""

    user_id: int = Field(..., description="ID of the user to share with")
    page_id: int = Field(..., description="ID of the page to share")
    permission_level: PermissionLevel = Field(
        PermissionLevel.VIEW, description="Permission level for the share"
    )


class UserPageShareUpdate(BaseModel):
    """Schema for updating an existing page share."""

    permission_level: Optional[PermissionLevel] = None
    is_active: Optional[bool] = None


class UserPageShareResponse(UserPageShareBase, TimestampSchema):
    """Schema for page share API responses."""

    id: int
    user_id: int = Field(..., description="ID of the user the page is shared with")
    page_id: int = Field(..., description="ID of the shared page")
    user: Optional[UserResponse] = Field(None, description="User details")
    page: Optional[PageResponse] = Field(None, description="Page details")

    class Config:
        from_attributes = True
