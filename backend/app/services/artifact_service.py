"""Artifact generation service.

This module provides services for generating artifacts from notes
and page content using LLM providers.
"""

import time
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import Note, NoteArtifact, LLMProvider, Page
from ..llm.provider_manager import provider_manager
from ..llm.base import LLMRequest, LLMProviderError


class ArtifactGenerationService:
    """Service for generating artifacts from notes and content."""

    def __init__(self, db: AsyncSession):
        """Initialize the artifact generation service.

        Args:
            db: Database session
        """
        self.db = db

    async def generate_note_artifact(
        self,
        note_id: int,
        llm_provider_id: int,
        artifact_type: str,
        custom_prompt: Optional[str] = None,
        generation_options: Optional[Dict[str, Any]] = None
    ) -> NoteArtifact:
        """Generate an artifact for a note.

        Args:
            note_id: ID of the note to generate artifact for
            llm_provider_id: ID of the LLM provider to use
            artifact_type: Type of artifact to generate
            custom_prompt: Optional custom prompt to use
            generation_options: Optional generation options

        Returns:
            Generated note artifact

        Raises:
            ValueError: If note or provider not found
            LLMProviderError: If generation fails
        """
        # Get the note
        note_result = await self.db.execute(select(Note).where(Note.id == note_id))
        note = note_result.scalar_one_or_none()
        if not note:
            raise ValueError(f"Note with ID {note_id} not found")

        # Get the LLM provider
        provider_result = await self.db.execute(
            select(LLMProvider).where(LLMProvider.id == llm_provider_id)
        )
        llm_provider = provider_result.scalar_one_or_none()
        if not llm_provider:
            raise ValueError(f"LLM provider with ID {llm_provider_id} not found")

        if not llm_provider.is_active:
            raise ValueError(f"LLM provider '{llm_provider.name}' is not active")

        # Get the provider instance from manager
        provider = provider_manager.get_provider(llm_provider.name)
        if not provider:
            raise LLMProviderError(f"Provider '{llm_provider.name}' not loaded")

        # Prepare context with note and page information
        context = {
            "note_id": note_id,
            "note_content": note.content,
            "artifact_type": artifact_type,
            "generation_options": generation_options or {},
        }

        # Add page context if available
        if note.page_id:
            page_result = await self.db.execute(select(Page).where(Page.id == note.page_id))
            page = page_result.scalar_one_or_none()
            if page:
                context.update({
                    "page_url": page.url,
                    "page_title": page.title,
                    "page_summary": page.page_summary,
                })

        start_time = time.time()

        # Generate the artifact
        try:
            llm_response = await provider_manager.generate_artifact(
                provider_name=llm_provider.name,
                artifact_type=artifact_type,
                content=note.content,
                custom_prompt=custom_prompt,
                context=context
            )
        except Exception as e:
            raise LLMProviderError(f"Failed to generate artifact: {e}")

        end_time = time.time()
        generation_time_ms = int((end_time - start_time) * 1000)

        # Create the artifact record
        artifact = NoteArtifact(
            artifact_type=artifact_type,
            content=llm_response.content,
            prompt_used=custom_prompt or f"Auto-generated prompt for {artifact_type}",
            generation_metadata={
                "llm_response": {
                    "tokens_used": llm_response.tokens_used,
                    "model_name": llm_response.model_name,
                    "provider_name": llm_response.provider_name,
                    "generation_time_ms": llm_response.generation_time_ms,
                },
                "service_metadata": {
                    "generation_time_ms": generation_time_ms,
                    "context": context,
                    "generation_options": generation_options,
                },
            },
            note_id=note_id,
            llm_provider_id=llm_provider_id,
        )

        # Save to database
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)

        return artifact

    async def generate_page_summary(
        self,
        page_id: int,
        llm_provider_id: int,
        summary_type: str = "general",
        custom_prompt: Optional[str] = None
    ) -> str:
        """Generate a summary for a page.

        Args:
            page_id: ID of the page to summarize
            llm_provider_id: ID of the LLM provider to use
            summary_type: Type of summary to generate
            custom_prompt: Optional custom prompt to use

        Returns:
            Generated summary text

        Raises:
            ValueError: If page or provider not found
            LLMProviderError: If generation fails
        """
        # Get the page
        page_result = await self.db.execute(select(Page).where(Page.id == page_id))
        page = page_result.scalar_one_or_none()
        if not page:
            raise ValueError(f"Page with ID {page_id} not found")

        # Get the LLM provider
        provider_result = await self.db.execute(
            select(LLMProvider).where(LLMProvider.id == llm_provider_id)
        )
        llm_provider = provider_result.scalar_one_or_none()
        if not llm_provider:
            raise ValueError(f"LLM provider with ID {llm_provider_id} not found")

        if not llm_provider.is_active:
            raise ValueError(f"LLM provider '{llm_provider.name}' is not active")

        # Get the provider instance from manager
        provider = provider_manager.get_provider(llm_provider.name)
        if not provider:
            raise LLMProviderError(f"Provider '{llm_provider.name}' not loaded")

        # Prepare content for summarization
        content_parts = []
        if page.title:
            content_parts.append(f"Title: {page.title}")
        if page.url:
            content_parts.append(f"URL: {page.url}")
        if page.user_context:
            content_parts.append(f"User Context: {page.user_context}")

        # Get notes for this page to include in summary
        notes_result = await self.db.execute(
            select(Note).where(Note.page_id == page_id, Note.is_active == True)
        )
        notes = notes_result.scalars().all()

        if notes:
            content_parts.append("Notes:")
            for i, note in enumerate(notes, 1):
                content_parts.append(f"{i}. {note.content}")

        content = "\n\n".join(content_parts)

        # Prepare context
        context = {
            "page_id": page_id,
            "page_url": page.url,
            "page_title": page.title,
            "summary_type": summary_type,
            "notes_count": len(notes),
        }

        # Generate summary
        try:
            if custom_prompt:
                request = LLMRequest(
                    prompt=custom_prompt,
                    context=context
                )
                llm_response = await provider.generate(request)
            else:
                llm_response = await provider.generate_summary(content, context)

            # Update page with generated summary
            page.page_summary = llm_response.content
            await self.db.commit()

            return llm_response.content

        except Exception as e:
            raise LLMProviderError(f"Failed to generate page summary: {e}")

    async def bulk_generate_artifacts(
        self,
        note_ids: list[int],
        llm_provider_id: int,
        artifact_type: str,
        custom_prompt: Optional[str] = None,
        generation_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate artifacts for multiple notes.

        Args:
            note_ids: List of note IDs to generate artifacts for
            llm_provider_id: ID of the LLM provider to use
            artifact_type: Type of artifact to generate
            custom_prompt: Optional custom prompt to use
            generation_options: Optional generation options

        Returns:
            Dictionary containing results and any errors

        Raises:
            ValueError: If provider not found
        """
        # Verify provider exists
        provider_result = await self.db.execute(
            select(LLMProvider).where(LLMProvider.id == llm_provider_id)
        )
        llm_provider = provider_result.scalar_one_or_none()
        if not llm_provider:
            raise ValueError(f"LLM provider with ID {llm_provider_id} not found")

        results = {
            "successful": [],
            "failed": [],
            "total_processed": 0,
            "total_time_ms": 0,
        }

        start_time = time.time()

        for note_id in note_ids:
            try:
                artifact = await self.generate_note_artifact(
                    note_id=note_id,
                    llm_provider_id=llm_provider_id,
                    artifact_type=artifact_type,
                    custom_prompt=custom_prompt,
                    generation_options=generation_options
                )
                results["successful"].append({
                    "note_id": note_id,
                    "artifact_id": artifact.id,
                    "content_length": len(artifact.content),
                })
            except Exception as e:
                results["failed"].append({
                    "note_id": note_id,
                    "error": str(e),
                })

            results["total_processed"] += 1

        end_time = time.time()
        results["total_time_ms"] = int((end_time - start_time) * 1000)

        return results

    async def get_artifact_types_for_note(self, note_id: int) -> list[str]:
        """Get available artifact types for a note.

        Args:
            note_id: Note ID

        Returns:
            List of artifact types that can be generated

        Raises:
            ValueError: If note not found
        """
        # Verify note exists
        note_result = await self.db.execute(select(Note).where(Note.id == note_id))
        note = note_result.scalar_one_or_none()
        if not note:
            raise ValueError(f"Note with ID {note_id} not found")

        # Return standard artifact types
        # These could be configurable or determined by note content
        return [
            "summary",
            "expansion",
            "questions",
            "action_items",
            "analysis",
        ]

    async def regenerate_artifact(
        self,
        artifact_id: int,
        custom_prompt: Optional[str] = None,
        generation_options: Optional[Dict[str, Any]] = None
    ) -> NoteArtifact:
        """Regenerate an existing artifact.

        Args:
            artifact_id: ID of the artifact to regenerate
            custom_prompt: Optional custom prompt to use
            generation_options: Optional generation options

        Returns:
            Regenerated artifact

        Raises:
            ValueError: If artifact not found
            LLMProviderError: If generation fails
        """
        # Get the existing artifact
        artifact_result = await self.db.execute(
            select(NoteArtifact).where(NoteArtifact.id == artifact_id)
        )
        existing_artifact = artifact_result.scalar_one_or_none()
        if not existing_artifact:
            raise ValueError(f"Artifact with ID {artifact_id} not found")

        # Generate new artifact
        new_artifact = await self.generate_note_artifact(
            note_id=existing_artifact.note_id,
            llm_provider_id=existing_artifact.llm_provider_id,
            artifact_type=existing_artifact.artifact_type,
            custom_prompt=custom_prompt,
            generation_options=generation_options
        )

        # Optionally deactivate the old artifact
        existing_artifact.is_active = False
        await self.db.commit()

        return new_artifact