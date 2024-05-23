from typing import Literal, get_args

Distribution = Literal['msem', 'penny_dreadful', 'fusion', 'default']
distributions: tuple[Distribution, ...] = get_args(Distribution)
distribution_rollback: dict[str, Distribution] = {
    'msem': 'msem', 'msem2': 'msem',
    'pd': 'penny_dreadful', 'penny_dreadful': 'penny_dreadful', 'dreadrise': 'penny_dreadful',
    'fusion': 'fusion'
}
distribution_localization: dict[Distribution, str] = {
    'penny_dreadful': 'Penny Dreadful',
    'msem': 'MSE Modern',
    'fusion': 'Fusion'
}
default_distribution: Distribution = 'penny_dreadful'
