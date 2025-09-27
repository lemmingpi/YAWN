"""Pydantic schemas for API request/response models.

This module defines all the data validation and serialization schemas
used by the FastAPI endpoints for the Web Notes API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Base schemas
class TimestampSchema(BaseModel):
    """Base schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


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
    pages_count: Optional[int] = Field(
        None, description="Number of pages associated with this site"
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


# Bulk operation schemas
class BulkNoteCreate(BaseModel):
    """Schema for bulk note creation."""

    notes: List[NoteCreate] = Field(
        ..., min_length=1, max_length=100, description="List of notes to create"
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
