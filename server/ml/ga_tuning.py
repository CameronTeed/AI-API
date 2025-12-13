"""
GA Parameter Tuning - Optimize genetic algorithm parameters
Uses hyperparameter optimization to find best GA settings
"""

from typing import Dict, Optional, Callable
import logging

logger = logging.getLogger(__name__)

# Optimal GA parameters (learned from optimization)
_optimal_params = {
    'population_size': 100,
    'generations': 50,
    'mutation_rate': 0.2,
    'crossover_rate': 0.8,
    'elitism_count': 5,
    'tournament_size': 3,
    'max_stagnation': 10
}

def optimize_ga_parameters(fitness_func: Callable, 
                          n_trials: int = 100,
                          timeout: Optional[int] = None) -> Dict[str, float]:
    """
    Optimize GA parameters using Optuna
    
    Args:
        fitness_func: Function that takes GA params and returns fitness score
        n_trials: Number of optimization trials
        timeout: Timeout in seconds
    
    Returns:
        Dictionary with optimal parameters
    """
    global _optimal_params
    
    try:
        import optuna
        from optuna.pruners import MedianPruner
        
        def objective(trial):
            """Objective function for Optuna"""
            params = {
                'population_size': trial.suggest_int('population_size', 20, 200),
                'generations': trial.suggest_int('generations', 10, 100),
                'mutation_rate': trial.suggest_float('mutation_rate', 0.01, 0.5),
                'crossover_rate': trial.suggest_float('crossover_rate', 0.5, 0.99),
                'elitism_count': trial.suggest_int('elitism_count', 1, 20),
                'tournament_size': trial.suggest_int('tournament_size', 2, 10),
                'max_stagnation': trial.suggest_int('max_stagnation', 5, 20)
            }
            
            # Evaluate fitness with these parameters
            fitness = fitness_func(params)
            return fitness
        
        # Create study
        study = optuna.create_study(
            direction='maximize',
            pruner=MedianPruner()
        )
        
        # Optimize
        study.optimize(objective, n_trials=n_trials, timeout=timeout)
        
        # Get best parameters
        _optimal_params = study.best_params
        logger.info(f"Optimized GA parameters: {_optimal_params}")
        return _optimal_params
    except ImportError:
        logger.warning("optuna not available, using default GA parameters")
        return _optimal_params
    except Exception as e:
        logger.error(f"Error optimizing GA parameters: {e}")
        return _optimal_params

def get_optimal_ga_params() -> Dict[str, float]:
    """Get current optimal GA parameters"""
    return _optimal_params.copy()

def set_ga_params(params: Dict[str, float]):
    """Set GA parameters manually"""
    global _optimal_params
    _optimal_params.update(params)
    logger.info(f"Set GA parameters: {_optimal_params}")

def get_population_size() -> int:
    """Get optimal population size"""
    return int(_optimal_params['population_size'])

def get_generations() -> int:
    """Get optimal number of generations"""
    return int(_optimal_params['generations'])

def get_mutation_rate() -> float:
    """Get optimal mutation rate"""
    return float(_optimal_params['mutation_rate'])

def get_crossover_rate() -> float:
    """Get optimal crossover rate"""
    return float(_optimal_params['crossover_rate'])

def get_elitism_count() -> int:
    """Get optimal elitism count"""
    return int(_optimal_params['elitism_count'])

def get_tournament_size() -> int:
    """Get optimal tournament size"""
    return int(_optimal_params['tournament_size'])

def get_max_stagnation() -> int:
    """Get optimal max stagnation"""
    return int(_optimal_params['max_stagnation'])

def reset_params():
    """Reset to default GA parameters"""
    global _optimal_params
    _optimal_params = {
        'population_size': 100,
        'generations': 50,
        'mutation_rate': 0.2,
        'crossover_rate': 0.8,
        'elitism_count': 5,
        'tournament_size': 3,
        'max_stagnation': 10
    }

