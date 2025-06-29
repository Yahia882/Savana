from rest_framework import  mixins, generics

class UpdateCreateAPIView(generics.GenericAPIView, mixins.CreateModelMixin, mixins.UpdateModelMixin):
    """
    A view that allows both creating and updating an object.
    """
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
    

class ListRetrieveUpdate(generics.GenericAPIView, mixins.ListModelMixin, mixins.UpdateModelMixin,mixins.RetrieveModelMixin):
    """
    A view that allows both creating and updating an object.
    """
    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        if pk is not None:
            return self.retrieve(request, *args, **kwargs)
        return self.list(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)