"""Ingestion service orchestrating the image processing pipeline."""

import uuid
from pathlib import Path
from typing import Optional

from db.models.knowledge import Knowledge, KnowledgeStatus
from db.repositories.knowledge_repo import KnowledgeRepository
from db.repositories.config_repo import ConfigRepository
from services.llm_service import LLMService
from services.embedding_service import EmbeddingService
from utils.image_utils import download_image, get_image_from_path, validate_image
from utils.retry_utils import with_retry, RetryConfig
from exceptions.ingestion_exceptions import (
    IngestionException,
    DatabaseError,
    RetryExhaustedError,
)


class IngestionService:
    """Service for orchestrating image ingestion pipeline."""

    def __init__(
        self,
        knowledge_repo: KnowledgeRepository | None = None,
        config_repo: ConfigRepository | None = None,
        llm_service: LLMService | None = None,
        embedding_service: EmbeddingService | None = None,
        llm_type: str = "web",
        llm_id: str = "gemini-3-flash-preview",
    ):
        """
        Initialize ingestion service with dependencies.

        Args:
            knowledge_repo: Repository for knowledge records
            config_repo: Repository for configuration
            llm_service: Service for LLM extraction
            embedding_service: Service for embedding generation
            llm_type: Type of LLM ("web" or "local")
            llm_id: LLM identifier
        """
        print(f"[IngestionService] Initializing with llm_type={llm_type}, llm_id={llm_id}")
        self.knowledge_repo = knowledge_repo or KnowledgeRepository()
        self.config_repo = config_repo or ConfigRepository()
        self.llm_service = llm_service or LLMService(llm_type=llm_type, llm_id=llm_id)
        self.embedding_service = embedding_service or EmbeddingService()
        print("[IngestionService] Initialized successfully")

    async def ingest_from_url(self, url: str) -> str:
        """
        Ingest single image from URL.

        If the URL already exists, the existing record will be reset and reprocessed.

        Args:
            url: Image URL

        Returns:
            Job ID (knowledge record ID)
        """
        print(f"[IngestionService] ingest_from_url: url={url}")

        # Check if URL already exists
        existing = await self.knowledge_repo.get_by_image(url)
        if existing:
            # Skip processing if already completed
            if existing.status == KnowledgeStatus.COMPLETED:
                print(f"[IngestionService] ingest_from_url: URL already exists with id={existing.id} and status=COMPLETED, skipping processing")
                return existing.id
            print(f"[IngestionService] ingest_from_url: URL already exists with id={existing.id}, resetting for reprocessing")
            await self.knowledge_repo.reset_for_reprocessing(existing.id)
            record_id = existing.id
        else:
            # Create pending record
            knowledge = Knowledge(
                image=url,
                url=url,
                category="",
                subcategory="",
                title="",
                raw_data="",
                paraphrased_data="",
                status=KnowledgeStatus.PENDING,
            )
            print("[IngestionService] ingest_from_url: creating new knowledge record")
            created = await self.knowledge_repo.create(knowledge)
            record_id = created.id
            print(f"[IngestionService] ingest_from_url: created record with id={record_id}")

        # Process asynchronously (in real implementation, this would be queued)
        print("[IngestionService] ingest_from_url: starting processing")
        success = await self._process_record(record_id)

        if success:
            print(f"[IngestionService] ingest_from_url: SUCCESS - returning id={record_id}")
        else:
            print(f"[IngestionService] ingest_from_url: FAILED - record {record_id} marked as failed")
        return record_id

    async def ingest_from_bytes(
        self,
        image_bytes: bytes,
        source_url: str,
        filename: str = "",
    ) -> str:
        """
        Ingest image from raw bytes (e.g., from Google Drive).

        If the source URL already exists, the existing record will be reset and reprocessed.

        Args:
            image_bytes: Raw image bytes
            source_url: Source URL for reference
            filename: Original filename

        Returns:
            Job ID (knowledge record ID)
        """
        print(f"[IngestionService] ingest_from_bytes: source_url={source_url}, filename={filename}, bytes={len(image_bytes)}")

        # Validate image first
        print("[IngestionService] ingest_from_bytes: validating image")
        validate_image(image_bytes)
        print("[IngestionService] ingest_from_bytes: image validation passed")

        # Check if source URL already exists
        existing = await self.knowledge_repo.get_by_image(source_url)
        if existing:
            # Skip processing if already completed
            if existing.status == KnowledgeStatus.COMPLETED:
                print(f"[IngestionService] ingest_from_bytes: URL already exists with id={existing.id} and status=COMPLETED, skipping processing")
                return existing.id
            print(f"[IngestionService] ingest_from_bytes: URL already exists with id={existing.id}, resetting for reprocessing")
            await self.knowledge_repo.reset_for_reprocessing(existing.id)
            record_id = existing.id
        else:
            # Create pending record
            knowledge = Knowledge(
                image=source_url,
                url=source_url,
                category="",
                subcategory="",
                title=filename or "",
                raw_data="",
                paraphrased_data="",
                status=KnowledgeStatus.PENDING,
            )
            print("[IngestionService] ingest_from_bytes: creating new knowledge record")
            created = await self.knowledge_repo.create(knowledge)
            record_id = created.id
            print(f"[IngestionService] ingest_from_bytes: created record with id={record_id}")

        # Process with pre-loaded bytes
        print("[IngestionService] ingest_from_bytes: starting processing with bytes")
        success = await self._process_record_with_bytes(record_id, image_bytes)

        if success:
            print(f"[IngestionService] ingest_from_bytes: SUCCESS - returning id={record_id}")
        else:
            print(f"[IngestionService] ingest_from_bytes: FAILED - record {record_id} marked as failed")
        return record_id

    async def ingest_from_local_folder(self, folder_path: str) -> list[str]:
        """
        Ingest all images from local folder.

        If an image path already exists, the existing record will be reset and reprocessed.

        Args:
            folder_path: Path to folder containing images

        Returns:
            List of job IDs
        """
        print(f"[IngestionService] ingest_from_local_folder: folder_path={folder_path}")

        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            print(f"[IngestionService] ingest_from_local_folder: ERROR - invalid folder path")
            raise IngestionException(f"Invalid folder path: {folder_path}")

        job_ids = []
        new_count = 0
        existing_count = 0
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

        files = list(folder.iterdir())
        print(f"[IngestionService] ingest_from_local_folder: found {len(files)} files in folder")

        for file_path in files:
            if file_path.suffix.lower() in image_extensions:
                image_path = str(file_path)
                print(f"[IngestionService] ingest_from_local_folder: processing {file_path.name}")

                # Check if image path already exists
                existing = await self.knowledge_repo.get_by_image(image_path)
                if existing:
                    # Skip processing if already completed
                    if existing.status == KnowledgeStatus.COMPLETED:
                        print(f"[IngestionService] ingest_from_local_folder: path already exists with id={existing.id} and status=COMPLETED, skipping")
                        continue
                    print(f"[IngestionService] ingest_from_local_folder: path already exists with id={existing.id}, resetting for reprocessing")
                    await self.knowledge_repo.reset_for_reprocessing(existing.id)
                    job_ids.append(existing.id)
                    existing_count += 1
                else:
                    # Create pending record
                    knowledge = Knowledge(
                        image=image_path,
                        url="",
                        category="",
                        subcategory="",
                        title="",
                        raw_data="",
                        paraphrased_data="",
                        status=KnowledgeStatus.PENDING,
                    )
                    created = await self.knowledge_repo.create(knowledge)
                    job_ids.append(created.id)
                    new_count += 1
                    print(f"[IngestionService] ingest_from_local_folder: created new record id={created.id}")

        print(f"[IngestionService] ingest_from_local_folder: prepared {len(job_ids)} records ({new_count} new, {existing_count} existing), starting processing")

        # Process all records, tracking success/failure
        success_count = 0
        failure_count = 0
        for i, job_id in enumerate(job_ids):
            print(f"[IngestionService] ingest_from_local_folder: processing job {i+1}/{len(job_ids)}")
            success = await self._process_record(job_id)
            if success:
                success_count += 1
            else:
                failure_count += 1

        print(f"[IngestionService] ingest_from_local_folder: COMPLETE - {success_count} succeeded, {failure_count} failed out of {len(job_ids)} images")
        return job_ids

    async def retry_record(self, record_id: str) -> bool:
        """
        Retry processing a failed record.

        Args:
            record_id: Knowledge record ID

        Returns:
            True if retry was initiated
        """
        print(f"[IngestionService] retry_record: record_id={record_id}")

        record = await self.knowledge_repo.get_by_id(record_id)
        if not record:
            print(f"[IngestionService] retry_record: ERROR - record not found")
            raise IngestionException(f"Record not found: {record_id}")

        if record.status != KnowledgeStatus.FAILED:
            print(f"[IngestionService] retry_record: ERROR - record not in failed status: {record.status}")
            raise IngestionException(f"Record is not in failed status: {record.status}")

        # Reset to pending and reprocess
        print("[IngestionService] retry_record: resetting to pending")
        await self.knowledge_repo.update_status(
            record_id, KnowledgeStatus.PENDING, error=None
        )
        print("[IngestionService] retry_record: starting reprocessing")
        await self._process_record(record_id)
        print("[IngestionService] retry_record: SUCCESS")
        return True

    async def retry_all_failed(self, category: str | None = None, limit: int = 100) -> int:
        """
        Retry all failed records.

        Args:
            category: Filter by category (optional)
            limit: Maximum records to retry

        Returns:
            Number of records queued for retry
        """
        print(f"[IngestionService] retry_all_failed: category={category}, limit={limit}")

        failed_records = await self.knowledge_repo.get_failed(limit=limit)
        print(f"[IngestionService] retry_all_failed: found {len(failed_records)} failed records")

        if category:
            failed_records = [r for r in failed_records if r.category == category]
            print(f"[IngestionService] retry_all_failed: filtered to {len(failed_records)} records for category={category}")

        success_count = 0
        failure_count = 0
        for record in failed_records:
            print(f"[IngestionService] retry_all_failed: retrying record {record.id}")
            await self.knowledge_repo.update_status(
                record.id, KnowledgeStatus.PENDING, error=None, comments=None
            )
            success = await self._process_record(record.id)
            if success:
                success_count += 1
            else:
                failure_count += 1

        print(f"[IngestionService] retry_all_failed: COMPLETE - {success_count} succeeded, {failure_count} failed out of {len(failed_records)} records")
        return success_count

    async def _process_record(self, record_id: str) -> bool:
        """
        Process a single knowledge record through the pipeline.

        Pipeline steps:
        1. Update status to processing
        2. Download/load image
        3. Validate image
        4. Extract content with LLM
        5. Generate embedding
        6. Update record with results

        Returns:
            True if processing succeeded, False if it failed (record marked as failed)
        """
        print(f"[IngestionService] _process_record: starting pipeline for record_id={record_id}")
        current_step = "initializing"

        try:
            # Update status to processing
            current_step = "updating status to processing"
            print("[IngestionService] _process_record: updating status to PROCESSING")
            await self.knowledge_repo.update_status(
                record_id, KnowledgeStatus.PROCESSING
            )

            # Get record
            current_step = "fetching record"
            print("[IngestionService] _process_record: fetching record")
            record = await self.knowledge_repo.get_by_id(record_id)
            if not record:
                print("[IngestionService] _process_record: ERROR - record not found")
                raise DatabaseError("fetch", "Record not found")

            print(f"[IngestionService] _process_record: image source={record.image}")

            # Get image bytes
            current_step = "downloading/loading image"
            if record.image.startswith(("http://", "https://")):
                print("[IngestionService] _process_record: downloading image from URL")
                image_bytes = await download_image(record.image)
                print(f"[IngestionService] _process_record: downloaded {len(image_bytes)} bytes")
            else:
                print("[IngestionService] _process_record: loading image from path")
                image_bytes = get_image_from_path(record.image)
                print(f"[IngestionService] _process_record: loaded {len(image_bytes)} bytes")

            # Validate image
            current_step = "validating image"
            print("[IngestionService] _process_record: validating image")
            validate_image(image_bytes)
            print("[IngestionService] _process_record: image validation passed")

            # Get available categories from config (as dict format for 3-level hierarchy)
            current_step = "fetching tags config"
            print("[IngestionService] _process_record: fetching tags config")
            tags_config = await self.config_repo.get_tags()
            categories = [cat.model_dump() for cat in tags_config.categories]
            print(f"[IngestionService] _process_record: found {len(categories)} categories")

            # Extract content
            current_step = "extracting content with LLM"
            print("[IngestionService] _process_record: extracting content with LLM")
            extraction = await self.llm_service.extract_content(
                image_bytes, available_categories=categories or None
            )
            print(f"[IngestionService] _process_record: extraction complete - title={extraction.title}, "
                  f"category={extraction.category}, subcategory={extraction.subcategory}, topic={extraction.topic}, "
                  f"is_new_cat={extraction.is_new_category}, is_new_subcat={extraction.is_new_subcategory}, "
                  f"is_new_topic={extraction.is_new_topic}")

            # Handle new categories/subcategories/topics - update config
            if extraction.is_new_category or extraction.is_new_subcategory or extraction.is_new_topic:
                current_step = "updating category hierarchy config"
                print(f"[IngestionService] _process_record: detected new hierarchy, updating config")
                cat_added, subcat_added, topic_added, _ = await self.config_repo.add_category_hierarchy(
                    extraction.category,
                    extraction.subcategory,
                    extraction.topic,
                )
                print(f"[IngestionService] _process_record: config updated - "
                      f"category_added={cat_added}, subcategory_added={subcat_added}, topic_added={topic_added}")

            # Generate embedding
            current_step = "generating embedding"
            print("[IngestionService] _process_record: generating embedding")
            embedding = await self.embedding_service.generate_embedding(
                extraction.raw_data
            )
            print(f"[IngestionService] _process_record: embedding generated - dimensions={len(embedding)}")

            # Update record with results
            current_step = "saving extraction results"
            print("[IngestionService] _process_record: updating record with results")
            await self.knowledge_repo.update_with_extraction(
                record_id,
                raw_data=extraction.raw_data,
                paraphrased_data=extraction.paraphrased_data,
                title=extraction.title,
                category=extraction.category,
                subcategory=extraction.subcategory,
                topic=extraction.topic,
                embedding=embedding,
            )

            print(f"[IngestionService] _process_record: SUCCESS - record {record_id} processed")
            return True

        except Exception as e:
            # Update status to failed with comments about which step failed
            error_message = str(e)
            comments = f"Failed at step: {current_step}"
            print(f"[IngestionService] _process_record: ERROR - {error_message}")
            print(f"[IngestionService] _process_record: {comments}")
            print("[IngestionService] _process_record: updating status to FAILED (continuing with next record)")
            try:
                await self.knowledge_repo.update_status(
                    record_id,
                    KnowledgeStatus.FAILED,
                    error=error_message,
                    comments=comments,
                    increment_retry=True,
                )
            except Exception as update_error:
                print(f"[IngestionService] _process_record: WARNING - failed to update status: {update_error}")
            return False

    async def _process_record_with_bytes(self, record_id: str, image_bytes: bytes) -> bool:
        """
        Process a knowledge record with pre-loaded image bytes.

        Used for Google Drive files where we already have the bytes.

        Returns:
            True if processing succeeded, False if it failed (record marked as failed)
        """
        print(f"[IngestionService] _process_record_with_bytes: starting pipeline for record_id={record_id}, bytes={len(image_bytes)}")
        current_step = "initializing"

        try:
            # Update status to processing
            current_step = "updating status to processing"
            print("[IngestionService] _process_record_with_bytes: updating status to PROCESSING")
            await self.knowledge_repo.update_status(
                record_id, KnowledgeStatus.PROCESSING
            )

            # Get record
            current_step = "fetching record"
            print("[IngestionService] _process_record_with_bytes: fetching record")
            record = await self.knowledge_repo.get_by_id(record_id)
            if not record:
                print("[IngestionService] _process_record_with_bytes: ERROR - record not found")
                raise DatabaseError("fetch", "Record not found")

            # Validate image (already validated, but double-check)
            current_step = "validating image"
            print("[IngestionService] _process_record_with_bytes: validating image")
            validate_image(image_bytes)
            print("[IngestionService] _process_record_with_bytes: image validation passed")

            # Get available categories from config (as dict format for 3-level hierarchy)
            current_step = "fetching tags config"
            print("[IngestionService] _process_record_with_bytes: fetching tags config")
            tags_config = await self.config_repo.get_tags()
            categories = [cat.model_dump() for cat in tags_config.categories]
            print(f"[IngestionService] _process_record_with_bytes: found {len(categories)} categories")

            # Extract content
            current_step = "extracting content with LLM"
            print("[IngestionService] _process_record_with_bytes: extracting content with LLM")
            extraction = await self.llm_service.extract_content(
                image_bytes, available_categories=categories or None
            )
            print(f"[IngestionService] _process_record_with_bytes: extraction complete - title={extraction.title}, "
                  f"category={extraction.category}, subcategory={extraction.subcategory}, topic={extraction.topic}, "
                  f"is_new_cat={extraction.is_new_category}, is_new_subcat={extraction.is_new_subcategory}, "
                  f"is_new_topic={extraction.is_new_topic}")

            # Handle new categories/subcategories/topics - update config
            if extraction.is_new_category or extraction.is_new_subcategory or extraction.is_new_topic:
                current_step = "updating category hierarchy config"
                print(f"[IngestionService] _process_record_with_bytes: detected new hierarchy, updating config")
                cat_added, subcat_added, topic_added, _ = await self.config_repo.add_category_hierarchy(
                    extraction.category,
                    extraction.subcategory,
                    extraction.topic,
                )
                print(f"[IngestionService] _process_record_with_bytes: config updated - "
                      f"category_added={cat_added}, subcategory_added={subcat_added}, topic_added={topic_added}")

            # Generate embedding
            current_step = "generating embedding"
            print("[IngestionService] _process_record_with_bytes: generating embedding")
            embedding = await self.embedding_service.generate_embedding(
                extraction.raw_data
            )
            print(f"[IngestionService] _process_record_with_bytes: embedding generated - dimensions={len(embedding)}")

            # Update record with results
            current_step = "saving extraction results"
            print("[IngestionService] _process_record_with_bytes: updating record with results")
            await self.knowledge_repo.update_with_extraction(
                record_id,
                raw_data=extraction.raw_data,
                paraphrased_data=extraction.paraphrased_data,
                title=extraction.title,
                category=extraction.category,
                subcategory=extraction.subcategory,
                topic=extraction.topic,
                embedding=embedding,
            )

            print(f"[IngestionService] _process_record_with_bytes: SUCCESS - record {record_id} processed")
            return True

        except Exception as e:
            # Update status to failed with comments about which step failed
            error_message = str(e)
            comments = f"Failed at step: {current_step}"
            print(f"[IngestionService] _process_record_with_bytes: ERROR - {error_message}")
            print(f"[IngestionService] _process_record_with_bytes: {comments}")
            print("[IngestionService] _process_record_with_bytes: updating status to FAILED (continuing with next record)")
            try:
                await self.knowledge_repo.update_status(
                    record_id,
                    KnowledgeStatus.FAILED,
                    error=error_message,
                    comments=comments,
                    increment_retry=True,
                )
            except Exception as update_error:
                print(f"[IngestionService] _process_record_with_bytes: WARNING - failed to update status: {update_error}")
            return False
