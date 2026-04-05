from fastapi import APIRouter


router = APIRouter(tags=["analysis"])


@router.get("/analysis/modules")
def analysis_modules() -> dict:
    return {
        "items": [
            {"key": "preview", "label": "图片预览"},
            {"key": "evaluate", "label": "量化评估"},
            {"key": "grid", "label": "网格拼图"},
            {"key": "comparison", "label": "对比拼图"},
        ]
    }
