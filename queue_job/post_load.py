import logging

from odoo.http import router

_logger = logging.getLogger(__name__)


def post_load():
    _logger.info(
        "Apply _set_session_and_dbname monkey patch to capture db"
        " from request with multiple databases"
    )
    _set_session_and_dbname_orig = router._set_session_and_dbname

    def _set_session_and_dbname(request):
        _set_session_and_dbname_orig(request)
        if (
            not request.db
            and request.httprequest.path == "/queue_job/runjob"
            and request.httprequest.args.get("db")
        ):
            request.db = request.httprequest.args["db"]

    router._set_session_and_dbname = _set_session_and_dbname
