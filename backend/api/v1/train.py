from fastapi import APIRouter


router = APIRouter(tags=["train"])


@router.get("/train/models")
def train_models() -> dict:
    return {
        "items": [
            {"key": "neural", "label": "Neural-BRDF"},
            {"key": "hyper", "label": "HyperBRDF"},
            {"key": "decoupled", "label": "DecoupledHyperBRDF"},
        ]
    }
