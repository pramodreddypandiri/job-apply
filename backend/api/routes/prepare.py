"""Prepare page routes — daily skill building sessions."""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from backend.api.middleware.auth import get_current_user
from backend.db import queries as db
from backend.models.prepare import (
    PrepTodayResponse,
    PrepQuestion,
    PrepAnswerResponse,
    RateRequest,
    RateResponse,
    TopicsResponse,
)
from loguru import logger

router = APIRouter()


@router.get("/today", response_model=PrepTodayResponse)
async def get_today_session(user: dict = Depends(get_current_user)):
    """Returns today's topic and session items."""
    today = date.today().isoformat()

    # Check if session already exists
    session = db.get_prep_session(user["id"], today)
    if session:
        return PrepTodayResponse(
            topic=session["topic"],
            category=session["category"],
            current_depth=session.get("depth_before", 1),
            brief="",  # TODO: load from cache
            questions=[
                PrepQuestion(id=item["id"], question=item["question"], type="conceptual")
                for item in session.get("prep_items", [])
            ],
        )

    # Generate new session
    skills = db.get_skill_graph(user["id"])
    profile = db.get_user_profile(user["id"])

    # Pick topic: prioritise gaps (low depth), then spaced repetition items
    due_items = db.get_due_prep_items(user["id"], today)
    if due_items:
        # Review session
        topic = due_items[0].get("question", "Review")
        category = "review"
    else:
        # New topic — pick lowest depth skill related to target role
        weak_skills = sorted(
            [s for s in skills if s.get("depth", 0) < 3],
            key=lambda s: s.get("depth", 0),
        )
        if weak_skills:
            topic = weak_skills[0]["skill_name"]
            category = weak_skills[0].get("category", "stack")
        else:
            topic = "System Design Review"
            category = "system_design"

    # Generate questions using LLM
    from backend.llm.client import generate
    questions_text = generate(
        prompt=f"Generate 3 practice questions about '{topic}' for a senior backend engineer interview. "
               f"Mix conceptual and applied questions. Return as JSON array: "
               f'[{{"question": "...", "type": "conceptual"|"applied"}}]',
        system="You are an interview prep coach. Return only valid JSON.",
        max_tokens=500,
    )

    import json
    from backend.llm.structured import extract_json_block
    try:
        questions_data = extract_json_block(questions_text)
        if isinstance(questions_data, dict):
            questions_data = questions_data.get("questions", [])
    except Exception:
        questions_data = [{"question": f"Explain {topic} in detail.", "type": "conceptual"}]

    # Create session
    session = db.create_prep_session({
        "user_id": user["id"],
        "session_date": today,
        "topic": topic,
        "category": category,
        "depth_before": next((s["depth"] for s in skills if s["skill_name"] == topic), 1),
    })

    # Create prep items
    items = db.create_prep_items([
        {
            "session_id": session["id"],
            "user_id": user["id"],
            "question": q["question"],
            "next_review": (date.today() + timedelta(days=1)).isoformat(),
        }
        for q in questions_data[:5]
    ])

    return PrepTodayResponse(
        topic=topic,
        category=category,
        current_depth=session.get("depth_before", 1),
        brief=f"Today we'll focus on {topic}.",
        questions=[
            PrepQuestion(id=item["id"], question=item["question"], type="conceptual")
            for item in items
        ],
    )


@router.get("/today/answer/{question_id}", response_model=PrepAnswerResponse)
async def get_answer(question_id: str, user: dict = Depends(get_current_user)):
    """Returns model answer for a question."""
    from backend.llm.client import generate
    from backend.db.client import supabase

    result = supabase.table("prep_items").select("*").eq("id", question_id).maybe_single().execute()
    item = result.data
    if not item or item["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Question not found")

    if item.get("model_answer"):
        return PrepAnswerResponse(answer=item["model_answer"])

    answer = generate(
        prompt=f"Provide a clear, detailed answer to this interview question:\n\n{item['question']}",
        system="You are an expert software engineer giving a model answer for an interview. Be concise but thorough.",
        max_tokens=1000,
    )

    db.update_prep_item(question_id, {"model_answer": answer})
    return PrepAnswerResponse(answer=answer)


@router.post("/today/rate", response_model=RateResponse)
async def rate_session(body: RateRequest, user: dict = Depends(get_current_user)):
    """Submits self-ratings for today's session."""
    today = date.today()

    for rating in body.ratings:
        # Calculate next review date based on spaced repetition
        if rating.rating == "got_it":
            next_review = today + timedelta(days=7)
        elif rating.rating == "unsure":
            next_review = today + timedelta(days=2)
        else:  # missed
            next_review = today + timedelta(days=1)

        db.update_prep_item(rating.question_id, {
            "self_rating": rating.rating,
            "next_review": next_review.isoformat(),
            "review_count": 1,  # TODO: increment
        })

    # Update skill depth if appropriate
    skills = db.get_skill_graph(user["id"])
    current_depth = next((s["depth"] for s in skills if s["skill_name"] == body.topic), 1)

    got_it_count = sum(1 for r in body.ratings if r.rating == "got_it")
    new_depth = current_depth
    if got_it_count == len(body.ratings) and current_depth < 5:
        new_depth = current_depth + 1
        db.upsert_skill(user["id"], body.topic, {"depth": new_depth})

    due_tomorrow = db.get_due_prep_items(user["id"], (today + timedelta(days=1)).isoformat())

    return RateResponse(
        depth_updated={"from": current_depth, "to": new_depth},
        next_review_items=len(due_tomorrow),
        message=f"Good session. {len(due_tomorrow)} items due for review tomorrow.",
    )


@router.get("/topics", response_model=TopicsResponse)
async def get_topics(user: dict = Depends(get_current_user)):
    """Returns all topics grouped by category with progress."""
    skills = db.get_skill_graph(user["id"])

    categories: dict[str, list] = {}
    for skill in skills:
        cat = skill.get("category", "other")
        categories.setdefault(cat, []).append({
            "name": skill["skill_name"],
            "depth": skill.get("depth", 1),
            "last_practiced": skill.get("updated_at"),
            "next_review": None,
            "status": "strong" if skill.get("depth", 0) >= 4 else "new" if skill.get("depth", 0) < 2 else "upcoming",
        })

    label_map = {
        "cs_fundamentals": "CS Fundamentals",
        "system_design": "System Design",
        "stack": "Tech Stack",
        "behavioural": "Behavioural",
        "other": "Other",
    }

    return TopicsResponse(
        categories=[
            {"name": cat, "label": label_map.get(cat, cat.title()), "topics": topics}
            for cat, topics in categories.items()
        ]
    )
