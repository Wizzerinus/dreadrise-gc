class DreadriseError(Exception):
    pass


class ConfigurationError(DreadriseError):
    pass


class FetchError(DreadriseError):
    pass


class ScrapeError(DreadriseError):
    pass


class RisingDataError(DreadriseError):
    pass


class TokenizerError(DreadriseError):
    pass


class SearchDataError(DreadriseError):
    pass


class SearchSyntaxError(DreadriseError):
    pass


class InvalidArgumentError(DreadriseError):
    pass
