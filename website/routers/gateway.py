from typing import Any, cast

from flask import Blueprint, make_response, request
from werkzeug import Response

from shared.core_enums import Distribution, default_distribution, distributions
from shared.helpers import configuration
from shared.helpers.util2 import get_dist_constants
from website.util import get_dist

b_gateway = Blueprint('gateway', __name__)


@b_gateway.route('/', methods=['POST'])
@b_gateway.route('/<dist_choice>', methods=['POST'])
def operate(dist_choice: str = '') -> Response:
    dist = dist_choice or get_dist()
    if dist not in distributions:
        dist = default_distribution
    dist_cast = cast(Distribution, dist)
    conf = get_dist_constants(dist_cast)
    if 'gateway' not in conf.EnabledModules:
        json = {'success': False, 'reason': f'Gateway is disabled for the chosen distribution ({dist}).'}
        return make_response(json, 400)

    json = cast(dict[str, Any], request.get_json())
    good = 'gateway_key' in json and json['gateway_key'] == configuration.get('gateway_key', dist_cast)
    if not good:
        json = {'success': False, 'reason': 'Gateway key does not match. '
                                            'The request JSON must include the `gateway_key` field.'}
        return make_response(json, 401)

    resp = conf.ParseGateway(json)
    status = 400 if not resp['success'] else 200
    return make_response(resp, status)
