from pydantic import BaseModel


class PrepQuestion(BaseModel):
    id: str
    question: str
    type: str  # "conceptual" | "applied"


class PrepTodayResponse(BaseModel):
    topic: str
    category: str
    current_depth: int
    brief: str
    questions: list[PrepQuestion]
    streak: int = 0
    sessions_this_week: int = 0


class PrepAnswerResponse(BaseModel):
    answer: str


class RatingItem(BaseModel):
    question_id: str
    rating: str  # "got_it" | "unsure" | "missed"


class RateRequest(BaseModel):
    topic: str
    ratings: list[RatingItem]


class RateResponse(BaseModel):
    depth_updated: dict  # {"from": int, "to": int}
    next_review_items: int
    message: str


class TopicProgress(BaseModel):
    name: str
    depth: int
    last_practiced: str | None = None
    next_review: str | None = None
    status: str  # "due" | "upcoming" | "strong" | "new"


class CategoryTopics(BaseModel):
    name: str
    label: str
    topics: list[TopicProgress]


class TopicsResponse(BaseModel):
    categories: list[CategoryTopics]
