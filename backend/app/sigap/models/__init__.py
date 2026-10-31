"""Model adapters for TUAI Sigap visual observations."""

from .base import DiseaseInference, DiseasePrediction, PestPrediction
from .disease import DiseaseAdapter
from .pest import PestAdapter
from .roboflow_pest import RoboflowPestAdapter

__all__ = [
    "DiseaseAdapter",
    "DiseaseInference",
    "DiseasePrediction",
    "PestAdapter",
    "PestPrediction",
    "RoboflowPestAdapter",
]
