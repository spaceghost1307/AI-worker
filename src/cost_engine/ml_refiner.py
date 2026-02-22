"""ML-based estimate refinement using gradient-boosted trees.

The ML layer refines assembly-based estimates — it never replaces them.
Trained on historical project data from JobTread, it detects patterns:
- Project types that consistently run over/under
- Material combinations correlating with higher change order rates
- Seasonal labor availability effects on actual costs

Uses XGBoost/LightGBM with SHAP for explainability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel


class MLRefinement(BaseModel):
    """Result of ML refinement on an assembly-based estimate."""

    original_total: float
    adjusted_total: float
    adjustment_pct: float  # positive = increase, negative = decrease
    confidence: float
    feature_importances: dict[str, float]  # SHAP values for top features
    explanation: str  # human-readable explanation of adjustment


class EstimateRefiner:
    """Refines assembly-based estimates using a trained ML model."""

    def __init__(self, model_path: Path | None = None) -> None:
        self.model = None
        self.model_path = model_path
        # TODO: Load trained model if path provided

    def train(self, historical_data_path: Path) -> None:
        """Train the refinement model on historical project data.

        Expected data format: CSV/Parquet with columns for project type,
        scope items, estimated costs, actual costs, region, season, etc.

        Args:
            historical_data_path: Path to historical project data export.
        """
        # TODO: Load historical data (JobTread export)
        # TODO: Feature engineering (project type, material mix, season, etc.)
        # TODO: Train XGBoost model (target = actual_cost / estimated_cost ratio)
        # TODO: Evaluate with cross-validation
        # TODO: Save model and SHAP explainer
        pass

    def refine(self, estimate: dict[str, Any]) -> MLRefinement:
        """Apply ML refinement to an assembly-based estimate.

        Args:
            estimate: Assembly-based estimate breakdown.

        Returns:
            ML refinement with adjusted total and explanation.
        """
        if self.model is None:
            return MLRefinement(
                original_total=estimate.get("total", 0.0),
                adjusted_total=estimate.get("total", 0.0),
                adjustment_pct=0.0,
                confidence=0.0,
                feature_importances={},
                explanation="No ML model loaded — returning assembly estimate as-is.",
            )

        # TODO: Extract features from estimate
        # TODO: Predict adjustment ratio
        # TODO: Compute SHAP values for explainability
        # TODO: Generate human-readable explanation
        return MLRefinement(
            original_total=0.0,
            adjusted_total=0.0,
            adjustment_pct=0.0,
            confidence=0.0,
            feature_importances={},
            explanation="",
        )
