from werkzeug.middleware.proxy_fix import ProxyFix

from shared.helpers.logging import initlogger
from shared.helpers.util2 import update_distributions
from website import app

initlogger()
update_distributions()
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
application = app
