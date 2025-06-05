from rest_framework import  mixins, generics

class UpdateCreateAPIView(generics.GenericAPIView, mixins.CreateModelMixin, mixins.UpdateModelMixin):
    """
    A view that allows both creating and updating an object.
    """
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)