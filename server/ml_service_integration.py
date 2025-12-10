"""
ML Service Integration Layer
Integrates the ML service (vibe prediction, date planning) with the main server
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import ML service components
try:
    ml_service_path = Path(__file__).parent.parent / 'ml_service'
    sys.path.insert(0, str(ml_service_path))
    
    import nlp_classifier
    import heuristic_planner
    import ga_planner
    import planner_utils
    
    ML_SERVICE_AVAILABLE = True
    logger.info("✅ ML Service loaded successfully")
except ImportError as e:
    ML_SERVICE_AVAILABLE = False
    logger.warning(f"⚠️  ML Service not available: {e}")


class MLServiceIntegration:
    """Integration layer for ML service components"""
    
    def __init__(self):
        """Initialize ML service integration"""
        self.available = ML_SERVICE_AVAILABLE
        if self.available:
            logger.info("ML Service Integration initialized")
    
    def predict_vibe(self, text: str) -> str:
        """Predict vibe from text using NLP classifier"""
        if not self.available:
            return "casual"
        
        try:
            vibes = nlp_classifier.get_keyword_vibes(text)
            return ", ".join(vibes) if vibes else "casual"
        except Exception as e:
            logger.warning(f"Error predicting vibe: {e}")
            return "casual"
    
    def predict_vibes_batch(self, texts: List[str]) -> List[str]:
        """Predict vibes for multiple texts"""
        return [self.predict_vibe(text) for text in texts]
    
    def plan_date_heuristic(self, preferences: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Plan a date using heuristic planner"""
        if not self.available:
            return None
        
        try:
            # Convert preferences to planner format
            result = heuristic_planner.plan_date(preferences)
            return result
        except Exception as e:
            logger.warning(f"Error planning date (heuristic): {e}")
            return None
    
    def plan_date_genetic(self, preferences: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Plan a date using genetic algorithm"""
        if not self.available:
            return None
        
        try:
            result = ga_planner.plan_date(preferences)
            return result
        except Exception as e:
            logger.warning(f"Error planning date (genetic): {e}")
            return None
    
    def learn_from_data(self, df) -> None:
        """Learn vibe mappings from data"""
        if not self.available:
            return
        
        try:
            planner_utils.initialize_from_data(df)
            logger.info("✅ Learned from data")
        except Exception as e:
            logger.warning(f"Error learning from data: {e}")


# Global instance
ml_service = MLServiceIntegration()


def get_ml_service() -> MLServiceIntegration:
    """Get ML service instance"""
    return ml_service

