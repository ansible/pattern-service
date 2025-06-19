from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def ping(request):
    return Response(data={"status": "ok"}, status=200)


@api_view(["GET"])
def test(request):
    return Response(data={"hello": "world"}, status=200)
