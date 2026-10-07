from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    original = response.data
    code = "request_error"
    message = "The request could not be completed."
    details = original
    if isinstance(original, dict) and "detail" in original:
        message = str(original["detail"])
        details = {}
        code = getattr(original["detail"], "code", code)
    response.data = {"error": {"code": str(code), "message": message, "details": details}}
    return response
