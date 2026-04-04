"""
core/metadata.py — Date extraction from video (pymediainfo) and image (EXIF via Pillow) files.
"""

import os

# Check for optional HEIC support at import time
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

# Video extensions handled by pymediainfo
_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.wmv', '.flv', '.webm', '.m4v'}
# Image extensions handled by Pillow EXIF
_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.bmp', '.tiff', '.gif'}


def get_video_date(filepath: str) -> 'str | None':
    """
    Extract creation date from video/animation file metadata using pymediainfo.
    Returns 'YYYY-MM-DD' string or None.
    """
    try:
        from pymediainfo import MediaInfo
        info = MediaInfo.parse(filepath, parse_speed=0.5)
        for track in info.tracks:
            for attr in ('encoded_date', 'tagged_date', 'recorded_date', 'mastered_date'):
                value = getattr(track, attr, None)
                if not value:
                    continue
                result = _parse_date_string(value)
                if result:
                    return result
    except Exception:
        pass
    return None


def get_image_date(filepath: str) -> 'str | None':
    """
    Extract creation date from image EXIF data using Pillow.
    Tries DateTimeOriginal (36867) → DateTimeDigitized (36868) → DateTime (306).
    Returns 'YYYY-MM-DD' string or None.
    """
    try:
        from PIL import Image
        from datetime import datetime

        with Image.open(filepath) as img:
            # Try modern API first (Pillow 6+)
            try:
                exif = img.getexif()
                if exif:
                    for tag_id in (36867, 36868, 306):
                        value = exif.get(tag_id)
                        if value:
                            return _parse_exif_datetime(value)
            except Exception:
                pass

            # Fallback for older Pillow or formats without getexif()
            try:
                raw = img._getexif()  # type: ignore
                if raw:
                    for tag_id in (36867, 36868, 306):
                        value = raw.get(tag_id)
                        if value:
                            return _parse_exif_datetime(value)
            except Exception:
                pass

    except Exception:
        pass
    return None


def get_file_date(filepath: str, priority: list) -> tuple:
    """
    Attempt to extract a date from a file using the given priority order.

    priority is a list of strings: 'metadata', 'filename', 'null'

    Returns (date_str_or_None, source_name) where source_name is one of
    'metadata', 'filename', or 'null'.
    """
    ext = os.path.splitext(filepath)[1].lower()

    for source in priority:
        if source == 'metadata':
            if ext in _VIDEO_EXTENSIONS or ext == '.gif':
                date = get_video_date(filepath)
            elif ext in _IMAGE_EXTENSIONS:
                date = get_image_date(filepath)
            else:
                date = None
            if date:
                return date, 'metadata'

        elif source == 'filename':
            date = extract_date_from_filename(os.path.basename(filepath))
            if date:
                return date, 'filename'

        elif source == 'null':
            return None, 'null'

    return None, 'null'


def extract_date_from_filename(fname: str) -> 'str | None':
    """
    Try to find a YYYY-MM-DD date embedded in a filename.
    Returns the date string or None.
    """
    import re
    m = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', fname)
    if m:
        return m.group(1)
    m = re.search(r'(\d{4}-\d{2}-\d{2})', fname)
    if m:
        return m.group(1)
    return None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_date_string(value: str) -> 'str | None':
    """Parse a MediaInfo date string into YYYY-MM-DD. Returns None on failure."""
    from datetime import datetime
    value = value.replace('UTC ', '').strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%SZ'):
        try:
            dt = datetime.strptime(value[:19], fmt[:len(value[:19])])
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def _parse_exif_datetime(value: str) -> 'str | None':
    """Parse an EXIF datetime string 'YYYY:MM:DD HH:MM:SS' into YYYY-MM-DD."""
    from datetime import datetime
    try:
        dt = datetime.strptime(value.strip()[:19], '%Y:%m:%d %H:%M:%S')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        pass
    # Some cameras write YYYY-MM-DD
    try:
        dt = datetime.strptime(value.strip()[:10], '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        pass
    return None
