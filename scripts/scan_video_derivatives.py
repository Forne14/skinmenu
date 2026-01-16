from pathlib import Path
from django.conf import settings
from wagtail.documents.models import Document
from media_derivatives.models import VideoDerivative

PROFILE = "hero_mobile_v1"

def run():
    media_root = Path(settings.MEDIA_ROOT)
    base = media_root / "derived" / "videos"

    print("MEDIA_ROOT =", media_root)
    print("Derived base =", base)
    print()

    for doc in Document.objects.order_by("id"):
        orig_rel = doc.file.name if doc.file else ""
        orig_abs = (media_root / orig_rel) if orig_rel else None

        expected_dir = base / str(doc.id) / PROFILE

        derivs = VideoDerivative.objects.filter(document_id=doc.id, profile_slug=PROFILE).order_by("kind")

        print(f"Document {doc.id}: {doc.title}")
        print(f"  original_rel: {orig_rel}")
        print(f"  original_abs: {orig_abs}  exists={orig_abs.exists() if orig_abs else False}")
        print(f"  expected_derived_dir: {expected_dir}  exists={expected_dir.exists()}")

        if expected_dir.exists():
            files = sorted([p.name for p in expected_dir.iterdir() if p.is_file()])
            print(f"  derived_dir_files: {files}")

        if derivs.exists():
            print("  derivatives_in_db:")
            for d in derivs:
                rel = d.file.name if d.file else ""
                abs_path = (media_root / rel) if rel else None
                print(
                    f"    - {d.profile_slug}/{d.kind}: "
                    f"status={d.status} progress={d.progress} file={rel or '(empty)'} "
                    f"exists={abs_path.exists() if abs_path else False} rq_job_id={d.rq_job_id or '(none)'}"
                )
        else:
            print("  derivatives_in_db: (none)")
        print()

if __name__ == "__main__":
    run()
