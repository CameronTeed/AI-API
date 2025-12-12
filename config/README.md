# ScoringConfig - Dynamic Configuration System

## Overview
`ScoringConfig` is a centralized configuration system that replaces all hardcoded values with ML-learned, dynamic parameters.

## Quick Start

### Import
```python
from config.scoring_config import ScoringConfig
```

### Use in Code
```python
# Instead of: score += 25
score += ScoringConfig.VIBE_MATCH_BONUS

# Instead of: score -= 800
score -= ScoringConfig.WRONG_CUISINE_PENALTY

# Instead of: if 10 <= reviews <= 300
if ScoringConfig.HIDDEN_GEM_MIN_REVIEWS <= reviews <= ScoringConfig.HIDDEN_GEM_MAX_REVIEWS
```

## Learning from Data

```python
import pandas as pd
from config.scoring_config import ScoringConfig

# Load venue data
venues_df = pd.read_csv('venues.csv')

# Learn optimal parameters from data
ScoringConfig.learn_from_data(venues_df)

# Now ScoringConfig has learned:
# - Average rating distribution
# - Review count distribution
# - Price distribution
# - And more...
```

## Configuration Categories

### Vibe Matching
- `VIBE_MATCH_BONUS` - Points for matching target vibe
- `NEUTRAL_VIBE_BONUS` - Points for neutral vibes

### Rating & Reviews
- `BAYESIAN_AVERAGE_CONSTANT` - Average rating across venues
- `BAYESIAN_MIN_REVIEWS` - Min reviews to trust rating
- `RATING_MULTIPLIER` - Multiply rating by this

### Hidden Gems
- `HIDDEN_GEM_MIN_REVIEWS` - Min reviews for hidden gem
- `HIDDEN_GEM_MAX_REVIEWS` - Max reviews for hidden gem
- `HIDDEN_GEM_BONUS` - Bonus for hidden gems
- `HIDDEN_GEM_POPULARITY_PENALTY` - Penalty if too popular

### Type Matching
- `TYPE_MATCH_BONUS` - Bonus for matching type
- `WRONG_CUISINE_PENALTY` - Penalty for wrong cuisine
- `COMPLEMENTARY_VENUE_BONUS` - Bonus for diversity
- `REPEATED_TYPE_PENALTY` - Penalty for repeating type

### Distance
- `DISTANCE_PENALTY_MULTIPLIER` - Multiply distance penalty
- `DISTANCE_EXPONENT` - Exponential penalty (1.5)

### GA Parameters
- `POPULATION_SIZE` - GA population size
- `GENERATIONS` - GA generations
- `MUTATION_RATE` - GA mutation rate
- `CROSSOVER_RATE` - GA crossover rate
- `ELITISM_COUNT` - Keep top N itineraries
- `STAGNATION_LIMIT` - Stop if no improvement

### Defaults
- `DEFAULT_BUDGET` - Default budget limit
- `DEFAULT_DURATION_MINUTES` - Default duration
- `DEFAULT_ITINERARY_LENGTH` - Default stops
- `DEFAULT_VIBE` - Default vibe

## Runtime Adjustment

```python
# Get all configuration
config = ScoringConfig.get_config()

# Update specific values
ScoringConfig.update_config(
    VIBE_MATCH_BONUS=30,
    TYPE_MATCH_BONUS=600,
    DEFAULT_BUDGET=200
)
```

## Best Practices

1. **Always use ScoringConfig** instead of hardcoded values
2. **Call learn_from_data()** during system initialization
3. **Use get_config()** for debugging and monitoring
4. **Use update_config()** for A/B testing different parameters
5. **Document why** you're changing a parameter

## Adding New Parameters

1. Add to `ScoringConfig` class:
```python
NEW_PARAMETER = 100  # Default value
```

2. Use in code:
```python
score += ScoringConfig.NEW_PARAMETER
```

3. Update `learn_from_data()` if it should be learned:
```python
@classmethod
def learn_from_data(cls, venues_df) -> None:
    # Learn NEW_PARAMETER from data
    cls.NEW_PARAMETER = computed_value
```

## Monitoring

```python
# Log all configuration
import logging
logger = logging.getLogger(__name__)
logger.info(f"Configuration: {ScoringConfig.get_config()}")

# Track parameter changes
ScoringConfig.update_config(VIBE_MATCH_BONUS=30)
# Logs: "Updated VIBE_MATCH_BONUS = 30"
```

## Files Using ScoringConfig

- `ai_orchestrator/final/heuristic_planner.py`
- `ai_orchestrator/final/ga_planner.py`
- `ai_orchestrator/final/spacy_parser.py`
- `ai_orchestrator/server/llm/engine.py`

## See Also

- `HARDCODED_VALUES_ANALYSIS.md` - Detailed analysis of all hardcoded values
- `HARDCODED_VALUES_REFACTORING_COMPLETE.md` - Refactoring summary

