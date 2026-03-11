from __future__ import annotations

from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Site

from catalog.models import (
    ClinicLocation,
    ContentBlock,
    ContentBlockItem,
    Treatment,
    TreatmentContentBlock,
    TreatmentFAQ,
    TreatmentMedia,
    TreatmentOption,
    TreatmentOptionContentBlock,
    TreatmentOptionFact,
    TreatmentPrice,
    TreatmentStep,
)
from pages.models import MenuSectionPage, TreatmentPage
from site_settings.models import GlobalSiteSettings


class Command(BaseCommand):
    help = "Backfill normalized catalog models from existing Wagtail pages."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--site-id", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **options):
        site_id = options.get("site_id")
        dry_run = options.get("dry_run")
        limit = options.get("limit")
        reset = options.get("reset")

        site = self._get_site(site_id)
        if site is None:
            self.stderr.write("No Site found. Aborting.")
            return

        with transaction.atomic():
            location = self._ensure_primary_location(site)
            self.stdout.write(f"Primary location: {location}")

            if reset:
                self._reset_catalog()

            self._backfill_treatments(limit=limit)
            self._backfill_options(limit=limit)

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write("Dry run enabled: rolled back changes.")

    def _get_site(self, site_id: Optional[int]) -> Optional[Site]:
        if site_id:
            return Site.objects.filter(pk=site_id).first()
        return Site.objects.filter(is_default_site=True).first() or Site.objects.first()

    def _ensure_primary_location(self, site: Site) -> ClinicLocation:
        existing = ClinicLocation.objects.filter(is_primary=True).first()
        if existing:
            return existing

        gs = GlobalSiteSettings.for_site(site)
        name = getattr(gs, "clinic_name", None) or "Primary location"

        location = ClinicLocation.objects.create(
            name=name,
            address=getattr(gs, "address", "") or "",
            email=getattr(gs, "email", "") or "",
            phone=getattr(gs, "phone", "") or "",
            map_url=getattr(gs, "google_maps_url", "") or "",
            map_embed_url=getattr(gs, "google_maps_embed_url", "") or "",
            is_primary=True,
        )
        return location

    def _reset_catalog(self) -> None:
        TreatmentOptionContentBlock.objects.all().delete()
        TreatmentOptionFact.objects.all().delete()
        TreatmentPrice.objects.all().delete()
        TreatmentMedia.objects.all().delete()
        TreatmentFAQ.objects.all().delete()
        TreatmentStep.objects.all().delete()
        TreatmentOption.objects.all().delete()
        TreatmentContentBlock.objects.all().delete()
        ContentBlockItem.objects.all().delete()
        ContentBlock.objects.all().delete()
        Treatment.objects.all().delete()

    def _backfill_treatments(self, limit: Optional[int] = None) -> None:
        qs = MenuSectionPage.objects.all().order_by("path")
        if limit:
            qs = qs[:limit]

        for idx, page in enumerate(qs, start=1):
            intro = getattr(page, "intro", "") or ""
            featured_image = getattr(page, "featured_image", None)
            treatment, created = Treatment.objects.get_or_create(
                slug=page.slug,
                defaults={
                    "name": page.title,
                    "summary": "",
                    "long_description": intro,
                    "featured_image": featured_image,
                    "sort_order": idx,
                },
            )

            updated = False
            if not created:
                if not treatment.name:
                    treatment.name = page.title
                    updated = True
                if not treatment.long_description and intro:
                    treatment.long_description = intro
                    updated = True
                if not treatment.featured_image and featured_image:
                    treatment.featured_image = featured_image
                    updated = True
                if treatment.sort_order == 0:
                    treatment.sort_order = idx
                    updated = True

            if updated:
                treatment.save()

            if page.treatment_id != treatment.id:
                page.treatment = treatment
                page.save(update_fields=["treatment"])

            self._migrate_treatment_sections(treatment, page)

            self.stdout.write(f"Treatment: {treatment.name} (page={page.id})")

    def _backfill_options(self, limit: Optional[int] = None) -> None:
        qs = TreatmentPage.objects.all().order_by("path")
        if limit:
            qs = qs[:limit]

        for idx, page in enumerate(qs, start=1):
            parent = page.get_parent().specific
            treatment = parent.treatment if isinstance(parent, MenuSectionPage) else None
            if treatment is None:
                continue

            summary = getattr(page, "summary", "") or ""
            featured_image = getattr(page, "featured_image", None)
            option, created = TreatmentOption.objects.get_or_create(
                treatment=treatment,
                name=page.title,
                defaults={
                    "summary": summary,
                    "featured_image": featured_image,
                    "sort_order": idx,
                },
            )

            updated = False
            if not created:
                if not option.summary and summary:
                    option.summary = summary
                    updated = True
                if not option.featured_image and featured_image:
                    option.featured_image = featured_image
                    updated = True
                if option.sort_order == 0:
                    option.sort_order = idx
                    updated = True

            if updated:
                option.save()

            if page.option_id != option.id:
                page.option = option
                page.save(update_fields=["option"])

            self._migrate_option_sections(option, page)
            self._migrate_option_media(option, page)

            self.stdout.write(f"Option: {option.name} (page={page.id})")

    def _migrate_option_media(self, option: TreatmentOption, page: TreatmentPage) -> None:
        featured_image = getattr(page, "featured_image", None)
        if featured_image and not option.media.filter(usage="hero").exists():
            TreatmentMedia.objects.create(
                option=option,
                usage="hero",
                image=featured_image,
                alt_text=featured_image.title if featured_image else "",
            )

    def _migrate_option_sections(self, option: TreatmentOption, page: TreatmentPage) -> None:
        sections = getattr(page, "sections", None) or []
        has_content_blocks = option.content_blocks.exists()

        for block_index, block in enumerate(sections, start=1):
            btype = block.block_type
            value = block.value

            if btype == "key_facts":
                for idx, fact in enumerate(value.get("facts", []), start=1):
                    label = (fact.get("label") or "").strip()
                    val = (fact.get("value") or "").strip()
                    if not label or not val:
                        continue
                    if option.facts.filter(label=label, value=val).exists():
                        continue
                    TreatmentOptionFact.objects.create(
                        option=option,
                        label=label,
                        value=val,
                        sort_order=idx,
                    )

            elif btype == "treatment_products":
                for idx, product in enumerate(value.get("products", []), start=1):
                    title = (product.get("title") or "").strip()
                    price = (product.get("price") or "").strip()
                    description = (product.get("description") or "").strip()
                    targets = product.get("targets") or []
                    targets_text = "\n".join([t.strip() for t in targets if t and t.strip()])

                    if option.prices.filter(label=title, price_text=price).exists():
                        continue

                    TreatmentPrice.objects.create(
                        option=option,
                        label=title,
                        price_text=price,
                        description=description,
                        targets=targets_text,
                        sort_order=idx,
                    )

            elif btype == "faq":
                for idx, item in enumerate(value.get("items", []), start=1):
                    question = (item.get("question") or "").strip()
                    answer = self._as_richtext(item.get("answer"))
                    if not question or not answer:
                        continue
                    if option.faqs.filter(question=question).exists():
                        continue
                    TreatmentFAQ.objects.create(
                        option=option,
                        question=question,
                        answer=answer,
                        sort_order=idx,
                    )

            elif btype == "steps":
                for idx, item in enumerate(value.get("steps", []), start=1):
                    title = (item.get("title") or "").strip()
                    text = self._as_richtext(item.get("text"))
                    if not title or not text:
                        continue
                    if option.steps.filter(title=title).exists():
                        continue
                    TreatmentStep.objects.create(
                        option=option,
                        title=title,
                        body=text,
                        sort_order=idx,
                    )

            elif btype in {"rich_text_section", "text_image", "cta"}:
                if has_content_blocks:
                    continue
                block_obj = self._create_content_block_from_section(btype, value)
                if block_obj:
                    if not TreatmentOptionContentBlock.objects.filter(
                        option=option, block=block_obj
                    ).exists():
                        TreatmentOptionContentBlock.objects.create(
                            option=option,
                            block=block_obj,
                            sort_order=block_index,
                        )

    def _migrate_treatment_sections(self, treatment: Treatment, page: MenuSectionPage) -> None:
        sections = getattr(page, "sections", None) or []
        if treatment.content_blocks.exists():
            return

        for block_index, block in enumerate(sections, start=1):
            btype = block.block_type
            value = block.value

            if btype in {"rich_text_section", "text_image", "cta"}:
                block_obj = self._create_content_block_from_section(btype, value)
                if block_obj:
                    TreatmentContentBlock.objects.create(
                        treatment=treatment,
                        block=block_obj,
                        sort_order=block_index,
                    )
                continue

            if btype in {"faq", "steps", "treatment_products"}:
                block_obj = self._create_list_block(btype, value)
                if block_obj:
                    TreatmentContentBlock.objects.create(
                        treatment=treatment,
                        block=block_obj,
                        sort_order=block_index,
                    )

    def _create_content_block_from_section(self, btype: str, value) -> Optional[ContentBlock]:
        eyebrow = (value.get("eyebrow") or "").strip()
        heading = (value.get("heading") or "").strip()
        body = value.get("body") or ""

        if not any([eyebrow, heading, body]):
            return None

        block = ContentBlock.objects.create(
            block_type=self._map_block_type(btype),
            eyebrow=eyebrow,
            heading=heading,
            body=body,
        )

        if btype == "text_image":
            media = value.get("media") or {}
            block.media_image = media.get("image") or value.get("image")
            block.media_video = media.get("video")
            block.media_position = value.get("image_position") or "right"

        if btype == "cta":
            primary = value.get("primary_cta") or {}
            secondary = value.get("secondary_cta") or {}
            block.primary_cta_label = (primary.get("label") or "").strip()
            block.primary_cta_url = (primary.get("url") or "").strip()
            block.secondary_cta_label = (secondary.get("label") or "").strip()
            block.secondary_cta_url = (secondary.get("url") or "").strip()

        block.save()
        return block

    def _create_list_block(self, btype: str, value) -> Optional[ContentBlock]:
        eyebrow = (value.get("eyebrow") or "").strip()
        heading = (value.get("heading") or "").strip()

        block = ContentBlock.objects.create(
            block_type=self._map_block_type(btype),
            eyebrow=eyebrow,
            heading=heading,
        )

        if btype == "faq":
            for idx, item in enumerate(value.get("items", []), start=1):
                question = (item.get("question") or "").strip()
                answer = self._as_richtext(item.get("answer"))
                if not question and not answer:
                    continue
                ContentBlockItem.objects.create(
                    block=block,
                    title=question,
                    body=answer,
                    sort_order=idx,
                )

        if btype == "steps":
            for idx, item in enumerate(value.get("steps", []), start=1):
                title = (item.get("title") or "").strip()
                text = self._as_richtext(item.get("text"))
                if not title and not text:
                    continue
                ContentBlockItem.objects.create(
                    block=block,
                    title=title,
                    body=text,
                    sort_order=idx,
                )

        if btype == "treatment_products":
            for idx, product in enumerate(value.get("products", []), start=1):
                title = (product.get("title") or "").strip()
                price = (product.get("price") or "").strip()
                description = (product.get("description") or "").strip()
                targets = product.get("targets") or []
                targets_text = "\n".join([t.strip() for t in targets if t and t.strip()])

                ContentBlockItem.objects.create(
                    block=block,
                    title=title,
                    price_text=price,
                    body=description,
                    value=targets_text,
                    sort_order=idx,
                )

        return block

    def _map_block_type(self, btype: str) -> str:
        return {
            "rich_text_section": "rich_text",
            "text_image": "text_media",
            "cta": "cta",
            "faq": "faq",
            "steps": "steps",
            "treatment_products": "products",
        }.get(btype, btype)

    def _as_richtext(self, value) -> str:
        if value is None:
            return ""
        if hasattr(value, "source"):
            return value.source or ""
        return str(value)
