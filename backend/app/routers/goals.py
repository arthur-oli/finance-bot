from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from app.deps.auth import verify_api_key
from app.schemas.goal import Goal, GoalCreate, GoalUpdate
import app.services.goal_service as svc

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=list[Goal])
def list_goals(include_completed: bool = Query(False)):
    return svc.list_goals(include_completed)


@router.post("/", response_model=Goal, status_code=201)
def create_goal(body: GoalCreate):
    return svc.create_goal(body)


@router.get("/{id}", response_model=Goal)
def get_goal(id: UUID):
    goal = svc.get_goal(id)
    if not goal:
        raise HTTPException(404, "Goal not found")
    return goal


@router.patch("/{id}", response_model=Goal)
def update_goal(id: UUID, body: GoalUpdate):
    goal = svc.update_goal(id, body)
    if not goal:
        raise HTTPException(404, "Goal not found")
    return goal


@router.delete("/{id}", status_code=204)
def delete_goal(id: UUID):
    if not svc.delete_goal(id):
        raise HTTPException(404, "Goal not found")
