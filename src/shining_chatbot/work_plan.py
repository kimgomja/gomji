"""Read a reviewed work schedule from the field dashboard Excel template."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from io import BytesIO

from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel


HEADERS = (
    "작업ID", "작업일", "시작", "종료", "동/구역", "세부 위치", "공종", "작업 내용",
    "주요 장비", "인원(명)", "협력업체", "작업책임자", "계획된 안전조치", "추가 확인",
    "검토 상태", "변경 사항",
)
REQUIRED = {"작업ID", "작업일", "시작", "종료", "동/구역", "작업 내용"}


@dataclass(frozen=True)
class WorkItem:
    work_id: str
    day: date
    start: time
    end: time
    area: str
    location: str
    trade: str
    activity: str
    equipment: str
    people: int | None
    contractor: str
    owner: str
    planned_controls: str
    follow_up: str
    review_status: str
    change_note: str
    sheet: str
    row: int


@dataclass(frozen=True)
class WorkPlan:
    site: str
    items: tuple[WorkItem, ...]
    issues: tuple[str, ...]


@dataclass(frozen=True)
class PlanChanges:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: tuple[str, ...]
    unchanged: tuple[str, ...]


def compare_plans(previous: WorkPlan, updated: WorkPlan) -> PlanChanges:
    """Compare source content by work ID, ignoring its location within the workbook."""
    old = {item.work_id: item for item in previous.items}
    new = {item.work_id: item for item in updated.items}
    def content(item: WorkItem) -> tuple:
        return (
            item.day, item.start, item.end, item.area, item.location, item.trade,
            item.activity, item.equipment, item.people, item.contractor, item.owner,
            item.planned_controls, item.follow_up, item.review_status, item.change_note,
        )
    shared = old.keys() & new.keys()
    return PlanChanges(
        tuple(sorted(new.keys() - old.keys())),
        tuple(sorted(old.keys() - new.keys())),
        tuple(sorted(work_id for work_id in shared if content(old[work_id]) != content(new[work_id]))),
        tuple(sorted(work_id for work_id in shared if content(old[work_id]) == content(new[work_id]))),
    )


def _string(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _day(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        converted = from_excel(value)
        if isinstance(converted, datetime):
            return converted.date()
    if isinstance(value, str):
        normalized = value.strip().rstrip(".").replace(".", "-").replace("/", "-")
        return date.fromisoformat(normalized.split()[0])
    raise ValueError("작업일 형식을 확인하세요")


def _time(value: object) -> time:
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
        if 0 <= seconds < 86400:
            return (datetime.min + value).time()
    if isinstance(value, (int, float)) and 0 <= value < 1:
        seconds = round(value * 86400)
        if seconds < 86400:
            return (datetime.min + timedelta(seconds=seconds)).time()
    if isinstance(value, str):
        return time.fromisoformat(value.strip())
    raise ValueError("시작·종료 시간 형식을 확인하세요")


def read_work_plan(content: bytes) -> WorkPlan:
    """Read the template; skip invalid rows and report their exact source location."""
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("파일 크기는 10MB 이하여야 합니다.")
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError("엑셀 파일을 읽을 수 없습니다. .xlsx 형식을 확인하세요.") from exc

    items: list[WorkItem] = []
    issues: list[str] = []
    seen: set[str] = set()
    site = "현장명 미입력"
    found_table = False
    try:
        for sheet in workbook:
            rows = sheet.iter_rows(values_only=True)
            header: dict[str, int] | None = None
            for row_number, values in enumerate(rows, start=1):
                cells = [_string(value) for value in values]
                if sheet.title == "현장정보" and cells and cells[0] == "현장명" and len(cells) > 1:
                    site = cells[1] or site
                if header is None:
                    candidate = {name: index for index, name in enumerate(cells) if name in HEADERS}
                    if REQUIRED.issubset(candidate):
                        header = candidate
                        found_table = True
                    continue
                if not any(value is not None and _string(value) for value in values):
                    continue
                def cell(name: str) -> object:
                    index = header.get(name)
                    return values[index] if index is not None and index < len(values) else None

                work_id = _string(cell("작업ID"))
                if not work_id:
                    # Notes below the table are not work rows.
                    continue
                source = f"{sheet.title} {row_number}행"
                if work_id in seen:
                    issues.append(f"{source}: 작업ID {work_id}가 중복되어 제외했습니다.")
                    continue
                try:
                    day = _day(cell("작업일"))
                    start = _time(cell("시작"))
                    end = _time(cell("종료"))
                    if end <= start:
                        raise ValueError("종료 시간은 시작 시간보다 늦어야 합니다")
                    area = _string(cell("동/구역"))
                    activity = _string(cell("작업 내용"))
                    if not area or not activity:
                        raise ValueError("동/구역과 작업 내용을 입력하세요")
                    people_value = cell("인원(명)")
                    if people_value in (None, ""):
                        people = None
                    else:
                        people = int(people_value)
                        if str(people) != str(people_value).strip() and float(people_value) != people:
                            raise ValueError("인원은 정수여야 합니다")
                    if people is not None and people < 0:
                        raise ValueError("인원은 0 이상이어야 합니다")
                except (ValueError, TypeError, OverflowError) as exc:
                    issues.append(f"{source}: {exc}. 이 작업은 제외했습니다.")
                    continue
                seen.add(work_id)
                items.append(WorkItem(
                    work_id, day, start, end, area, _string(cell("세부 위치")),
                    _string(cell("공종")), activity, _string(cell("주요 장비")), people,
                    _string(cell("협력업체")), _string(cell("작업책임자")),
                    _string(cell("계획된 안전조치")), _string(cell("추가 확인")),
                    _string(cell("검토 상태")), _string(cell("변경 사항")),
                    sheet.title, row_number,
                ))
    finally:
        workbook.close()
    if not found_table:
        raise ValueError("작업표를 찾지 못했습니다. 샘플 계획서의 열 이름을 확인하세요.")
    if not items:
        raise ValueError("사용 가능한 작업이 없습니다. 날짜·시간·작업 내용을 확인하세요.")
    return WorkPlan(site, tuple(sorted(items, key=lambda item: (item.day, item.start, item.work_id))), tuple(issues))


def overlapping_pairs(items: tuple[WorkItem, ...], day: date) -> tuple[tuple[WorkItem, WorkItem], ...]:
    """Flag potential coordination needs in the same broad area; no hazard verdict."""
    daily = [item for item in items if item.day == day]
    return tuple(
        (left, right)
        for index, left in enumerate(daily)
        for right in daily[index + 1:]
        if left.area == right.area and left.start < right.end and right.start < left.end
    )
