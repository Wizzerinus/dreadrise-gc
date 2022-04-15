from typing import Dict, Literal, Tuple, get_args

Distribution = Literal['msem', 'penny_dreadful', 'fusion', 'default']
distributions: Tuple[Distribution, ...] = get_args(Distribution)
distribution_rollback: Dict[str, Distribution] = {
    'msem': 'msem', 'msem2': 'msem',
    'pd': 'penny_dreadful', 'penny_dreadful': 'penny_dreadful',
    'fusion': 'fusion'
}
distribution_localization: Dict[Distribution, str] = {
    'penny_dreadful': 'Penny Dreadful',
    'msem': 'MSE Modern',
    'fusion': 'Fusion'
}
default_distribution: Distribution = 'penny_dreadful'
