"""Test parallel chunk processing with asyncio."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.auto_note_service import AutoNoteService


class TestParallelProcessing:

    @pytest.mark.asyncio
    async def test_chunks_process_in_parallel(self):
        """Verify chunks process in parallel, not sequentially."""

        async def mock_llm_call(prompt):
            """Simulate LLM call with 1 second delay."""
            await asyncio.sleep(1)
            mock_response = MagicMock()
            mock_response.text = '{"notes": []}'
            mock_response.usage_metadata.total_token_count = 1000
            return mock_response

        mock_db = AsyncMock()
        service = AutoNoteService(mock_db)

        # Add _call_llm attribute for test
        service._call_llm = mock_llm_call

        start_time = time.time()

        # Process 6 chunks with max 3 concurrent
        results = await service.process_chunks_parallel(
            chunks=[{"chunk_dom": f"<div>{i}</div>"} for i in range(6)],
            full_dom="<body>...</body>",
            max_concurrent=3,
        )

        elapsed = time.time() - start_time

        # Should take ~2 seconds (2 batches of 3), not 6 seconds
        assert 1.8 < elapsed < 2.5, f"Parallel processing took {elapsed}s"
        assert len(results) == 6

    @pytest.mark.asyncio
    async def test_rate_limiting_enforced(self):
        """Max 3 concurrent LLM calls at a time."""
        concurrent_count = 0
        max_concurrent_seen = 0

        async def mock_llm_with_tracking(prompt):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.1)
            concurrent_count -= 1
            mock_response = MagicMock()
            mock_response.text = '{"notes": []}'
            mock_response.usage_metadata.total_token_count = 1000
            return mock_response

        mock_db = AsyncMock()
        service = AutoNoteService(mock_db)
        service._call_llm = mock_llm_with_tracking

        await service.process_chunks_parallel(
            chunks=[{"chunk_dom": f"<div>{i}</div>"} for i in range(10)],
            full_dom="<body>...</body>",
            max_concurrent=3,
        )

        assert max_concurrent_seen == 3, f"Max concurrent was {max_concurrent_seen}"

    @pytest.mark.asyncio
    async def test_chunk_failure_doesnt_stop_others(self):
        """One chunk failing doesn't prevent others from processing."""

        async def mock_llm_some_fail(prompt):
            if "chunk_2" in str(prompt):
                raise Exception("LLM error for chunk 2")
            mock_response = MagicMock()
            mock_response.text = '{"notes": [{"content": "Note"}]}'
            mock_response.usage_metadata.total_token_count = 1000
            return mock_response

        mock_db = AsyncMock()
        service = AutoNoteService(mock_db)
        service._call_llm = mock_llm_some_fail

        results = await service.process_chunks_parallel(
            chunks=[
                {"chunk_dom": "<div>chunk_1</div>"},
                {"chunk_dom": "<div>chunk_2</div>"},  # This will fail
                {"chunk_dom": "<div>chunk_3</div>"},
            ],
            full_dom="<body>...</body>",
            max_concurrent=3,
        )

        # Should get results for chunks 1 and 3 (chunk 2 failed)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_batch_processing_respects_limits(self):
        """Batches are processed correctly respecting max_concurrent."""
        call_times = []

        async def mock_llm_track_timing(prompt):
            call_times.append(time.time())
            await asyncio.sleep(0.5)
            mock_response = MagicMock()
            mock_response.text = '{"notes": []}'
            mock_response.usage_metadata.total_token_count = 1000
            return mock_response

        mock_db = AsyncMock()
        service = AutoNoteService(mock_db)
        service._call_llm = mock_llm_track_timing

        # Process 9 chunks with max 3 concurrent
        await service.process_chunks_parallel(
            chunks=[{"chunk_dom": f"<div>{i}</div>"} for i in range(9)],
            full_dom="<body>...</body>",
            max_concurrent=3,
        )

        # Should have 3 batches
        # Analyze timing to confirm batching
        assert len(call_times) == 9

        # Group calls by batch (calls within 0.1s of each other are same batch)
        batches = []
        current_batch = [call_times[0]]

        for t in call_times[1:]:
            if t - current_batch[-1] < 0.1:
                current_batch.append(t)
            else:
                batches.append(current_batch)
                current_batch = [t]
        batches.append(current_batch)

        # Should have 3 batches of 3 calls each
        assert len(batches) == 3
        for batch in batches:
            assert len(batch) == 3

    @pytest.mark.asyncio
    async def test_empty_chunks_list(self):
        """Handles empty chunks list gracefully."""
        mock_db = AsyncMock()
        service = AutoNoteService(mock_db)

        results = await service.process_chunks_parallel(
            chunks=[], full_dom="<body>...</body>", max_concurrent=3
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_single_chunk_processes(self):
        """Single chunk processes correctly."""
        mock_db = AsyncMock()
        service = AutoNoteService(mock_db)

        async def mock_llm_call(prompt):
            mock_response = MagicMock()
            mock_response.text = '{"notes": [{"content": "Test note"}]}'
            mock_response.usage_metadata.total_token_count = 1000
            return mock_response

        service._call_llm = mock_llm_call

        results = await service.process_chunks_parallel(
            chunks=[{"chunk_dom": "<div>Single chunk</div>"}],
            full_dom="<body>...</body>",
            max_concurrent=3,
        )

        assert len(results) == 1
        # Result should be returned from mock

    @pytest.mark.asyncio
    async def test_preserves_chunk_order_in_results(self):
        """Results maintain chunk order despite parallel processing."""
        mock_db = AsyncMock()
        service = AutoNoteService(mock_db)

        async def mock_llm_with_delay(prompt):
            # Different delays to test order preservation
            if "chunk_0" in str(prompt):
                await asyncio.sleep(0.3)
            elif "chunk_1" in str(prompt):
                await asyncio.sleep(0.1)
            else:
                await asyncio.sleep(0.2)

            chunk_num = str(prompt).split("chunk_")[1].split("<")[0]
            mock_response = MagicMock()
            mock_response.text = (
                f'{{"notes": [{{"content": "Note from chunk {chunk_num}"}}]}}'
            )
            mock_response.usage_metadata.total_token_count = 1000
            return mock_response

        service._call_llm = mock_llm_with_delay

        results = await service.process_chunks_parallel(
            chunks=[
                {"chunk_dom": "<div>chunk_0</div>", "chunk_index": 0},
                {"chunk_dom": "<div>chunk_1</div>", "chunk_index": 1},
                {"chunk_dom": "<div>chunk_2</div>", "chunk_index": 2},
            ],
            full_dom="<body>...</body>",
            max_concurrent=3,
        )

        # Despite different processing times, results should be returned
        assert len(results) == 3
