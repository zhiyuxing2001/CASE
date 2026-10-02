"""附件上传与读取。

文件本体存于 ``data/attachments/``（gitignored），库中只记路径与哈希。
图片经后端接口读取，不把 data/ 直接暴露为静态目录。
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ulid import ULID

from .. import schemas
from ..config import settings
from ..models import Attachment
from ..ocr import check_quality
from .deps import get_db

router = APIRouter(prefix="/api/attachments", tags=["attachments"])

_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


@router.post("", response_model=schemas.AttachmentCreated, status_code=201)
def upload_attachment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> schemas.AttachmentCreated:
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")

    mime = (file.content_type or "image/jpeg").lower()
    ext = _EXT.get(mime)
    if ext is None:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的图片格式 {mime}，请使用 JPEG / PNG / WebP",
        )

    attach_id = str(ULID())
    settings.attachments_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{attach_id}.{ext}"
    (settings.attachments_dir / filename).write_bytes(data)

    quality = check_quality(str(settings.attachments_dir / filename))
    sha256 = hashlib.sha256(data).hexdigest()

    db.add(Attachment(
        attach_id=attach_id,
        file_path=f"attachments/{filename}",
        file_type=0,
        mime_type=mime,
        file_size=len(data),
        width=quality["width"],
        height=quality["height"],
        sha256=sha256,
    ))
    db.commit()

    return schemas.AttachmentCreated(
        attach_id=attach_id,
        quality=schemas.QualityReport(**quality),
    )


@router.get("/{attach_id}/file")
def get_file(attach_id: str, db: Session = Depends(get_db)) -> FileResponse:
    attachment = db.get(Attachment, attach_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    path = settings.data_dir / attachment.file_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件已丢失")
    return FileResponse(path, media_type=attachment.mime_type or "image/jpeg")
