from typing import Dict, Literal, Tuple, get_args

Distribution = Literal['msem', 'penny_dreadful', 'default']
distributions: Tuple[Distribution, ...] = get_args(Distribution)
distribution_rollback: Dict[str, Distribution] = {
    'msem': 'msem', 'msem2': 'msem',
    'pd': 'penny_dreadful', 'penny_dreadful': 'penny_dreadful'
}
distribution_localization: Dict[Distribution, str] = {
    'penny_dreadful': 'Penny Dreadful',
    'msem': 'MSE Modern'
}
default_distribution = 'penny_dreadful'
