from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class PriorityCount(BaseModel):
    priority: str
    count: int


class GroupCount(BaseModel):
    group_name: str
    count: int


class DashboardSummary(BaseModel):
    total_tickets: int
    by_status: list[StatusCount]
    by_priority: list[PriorityCount]
    by_group: list[GroupCount]


class SlaMetrics(BaseModel):
    mtta_seconds: float | None
    mttr_seconds: float | None
    group_name: str | None = None
    priority: str | None = None
