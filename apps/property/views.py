from rest_framework import views, status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.db.models import F, Avg, Q
from django.http import JsonResponse
from django.conf import settings
from .models import *
import uuid

from apps.auth.utils import format_serializer_errors
from .models import Property, Favourites
from .serializers import (
    PropertyDetailSerializer, PropertyListSerializer, PropertySerializer, GallerySerializer, ReportsSerializer
)   
from apps.booking.models import Booking

def apply_property_filters(properties, query_params):
    search = query_params.get('search')
    if search:
        properties = properties.filter(Q(name__icontains=search) | Q(address__icontains=search))
        
    bed = query_params.get('bed')
    if bed:
        properties = properties.filter(bedroom=bed)
        
    bath = query_params.get('bath')
    if bath:
        properties = properties.filter(bathroom=bath)
        
    p_type = query_params.get('type', 'ANY')
    if p_type != 'ANY':
        properties = properties.filter(type=p_type)
        
    sea_view = query_params.get('sea_view')
    if sea_view and str(sea_view).lower() in ("true", "1"):
        properties = properties.filter(sea_view=True)
        
    from datetime import datetime
    start_date = query_params.get('start_date')
    end_date = query_params.get('end_date')
    status_param = query_params.get('status') or query_params.get('availability')
    if status_param:
        status_param = status_param.upper()
    else:
        status_param = 'ANY'
    
    start_d = None
    end_d = None
    if start_date and end_date:
        try:
            start_d = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_d = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            pass
            
    if start_d and end_d:
        booked_property_ids = Booking.objects.filter(
            status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN'],
            check_in__lt=end_d,
            check_out__gt=start_d
        ).values_list('property_id', flat=True)
        
        if status_param == "BOOKED":
            properties = properties.filter(id__in=booked_property_ids)
        elif status_param == "AVAILABLE":
            properties = properties.exclude(id__in=booked_property_ids).exclude(status="CLOSED")
        else:
            properties = properties.exclude(status="CLOSED")
    else:
        if status_param == "BOOKED":
            booked_property_ids = Booking.objects.filter(
                status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN']
            ).values_list('property_id', flat=True)
            properties = properties.filter(id__in=booked_property_ids)
        elif status_param == "AVAILABLE":
            properties = properties.filter(status="AVAILABLE")
        else:
            properties = properties.exclude(status="CLOSED")
            
    return properties

class PropertyGuestViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] # Originally IsAuthenticated in Bolt
    serializer_class = PropertyListSerializer
    
    def get_queryset(self):
        properties = Property.objects.all()
        properties = apply_property_filters(properties, self.request.query_params)
            
        # Proximity filtering / sorting
        lat = self.request.query_params.get('latitude')
        lng = self.request.query_params.get('longitude')
        radius_param = self.request.query_params.get('radius')
        
        self.distances = {}
        
        if lat and lng:
            import math
            def haversine_distance(lat1, lon1, lat2, lon2):
                lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                r = 6371 # Radius of earth in kilometers
                return c * r

            try:
                user_lat = float(lat)
                user_lng = float(lng)
                
                # Fetch queryset evaluated list
                property_list = list(properties)
                valid_properties = []
                for p in property_list:
                    if p.latitude is not None and p.longitude is not None:
                        dist = haversine_distance(user_lat, user_lng, p.latitude, p.longitude)
                        p.distance = dist
                        valid_properties.append(p)
                
                # Filter by radius if specified
                if radius_param:
                    try:
                        max_radius = float(radius_param)
                        valid_properties = [p for p in valid_properties if p.distance <= max_radius]
                    except ValueError:
                        pass
                
                # Sort closest first
                valid_properties.sort(key=lambda p: p.distance)
                
                # Populate distances map
                self.distances = {p.id: p.distance for p in valid_properties}
                
                # Convert back to sorted queryset
                sorted_ids = [p.id for p in valid_properties]
                if sorted_ids:
                    from django.db.models import Case, When
                    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(sorted_ids)])
                    properties = Property.objects.filter(id__in=sorted_ids).order_by(preserved)
                else:
                    properties = Property.objects.none()
            except ValueError:
                pass

        return properties.annotate(avg_rating=Avg('reviews__rating'))

    @extend_schema(
        parameters=[
            OpenApiParameter('type', OpenApiTypes.STR, description='Property type (ANY, HOUSE, etc.)', required=False),
            OpenApiParameter('search', OpenApiTypes.STR, required=False),
            OpenApiParameter('start_date', OpenApiTypes.STR, required=False),
            OpenApiParameter('end_date', OpenApiTypes.STR, required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Availability status (AVAILABLE, BOOKED, ANY)', required=False),
            OpenApiParameter('availability', OpenApiTypes.STR, description='Availability status (AVAILABLE, BOOKED, ANY)', required=False),
            OpenApiParameter('latitude', OpenApiTypes.FLOAT, description='Latitude for proximity search', required=False),
            OpenApiParameter('longitude', OpenApiTypes.FLOAT, description='Longitude for proximity search', required=False),
            OpenApiParameter('radius', OpenApiTypes.FLOAT, description='Search radius in kilometers', required=False),
            OpenApiParameter('sea_view', OpenApiTypes.BOOL, required=False),
            OpenApiParameter('bed', OpenApiTypes.INT, required=False),
            OpenApiParameter('bath', OpenApiTypes.INT, required=False),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request, 'view': self})
        return Response({
            "status": 200, "message": "Properties fetched successfully", 
            "success": True, "data": serializer.data
        })

    @extend_schema(
        parameters=[
            OpenApiParameter('latitude', OpenApiTypes.FLOAT, description='Latitude of user to calculate distance', required=False),
            OpenApiParameter('longitude', OpenApiTypes.FLOAT, description='Longitude of user to calculate distance', required=False),
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        property_id = kwargs.get('pk')
        prop = Property.objects.select_related('owner').filter(id=property_id).first()
        if not prop:
            return Response({"status": 404, "success": False, "message": "Property not found"}, status=status.HTTP_404_NOT_FOUND)
        
        Property.objects.filter(id=property_id).update(views=F('views') + 1)
        prop.refresh_from_db()
        
        lat = request.query_params.get('latitude')
        lng = request.query_params.get('longitude')
        if lat and lng:
            try:
                import math
                user_lat = float(lat)
                user_lng = float(lng)
                if prop.latitude is not None and prop.longitude is not None:
                    lat1, lon1, lat2, lon2 = map(math.radians, [user_lat, user_lng, float(prop.latitude), float(prop.longitude)])
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                    c = 2 * math.asin(math.sqrt(a))
                    prop.distance = c * 6371
            except ValueError:
                pass
        
        serializer = PropertyDetailSerializer(prop, context={'request': request, 'view': self})
        return Response(serializer.data)

class PropertyHomeView(views.APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyListSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter('type', OpenApiTypes.STR, description='Property type (ANY, HOUSE, etc.)', required=False),
            OpenApiParameter('search', OpenApiTypes.STR, required=False),
            OpenApiParameter('start_date', OpenApiTypes.STR, required=False),
            OpenApiParameter('end_date', OpenApiTypes.STR, required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Availability status (AVAILABLE, BOOKED, ANY)', required=False),
            OpenApiParameter('availability', OpenApiTypes.STR, description='Availability status (AVAILABLE, BOOKED, ANY)', required=False),
            OpenApiParameter('latitude', OpenApiTypes.FLOAT, description='Latitude for proximity search', required=False),
            OpenApiParameter('longitude', OpenApiTypes.FLOAT, description='Longitude for proximity search', required=False),
            OpenApiParameter('radius', OpenApiTypes.FLOAT, description='Search radius in kilometers', required=False),
            OpenApiParameter('sea_view', OpenApiTypes.BOOL, required=False),
            OpenApiParameter('bed', OpenApiTypes.INT, required=False),
            OpenApiParameter('bath', OpenApiTypes.INT, required=False),
        ]
    )
    def get(self, request):
        # Apply base filters first
        base_qs = Property.objects.all()
        base_qs = apply_property_filters(base_qs, request.query_params)

        # 1. Fetch recommended properties (sorted by views and avg_rating descending)
        recommended_qs = base_qs.annotate(
            avg_rating=Avg('reviews__rating')
        ).order_by('-views', '-avg_rating')[:10]
        
        # 2. Fetch popular nearby properties
        lat = request.query_params.get('latitude')
        lng = request.query_params.get('longitude')
        radius_param = request.query_params.get('radius')
        
        # Default fallback for popular nearby if lat/lng are not provided
        popular_nearby_qs = base_qs.annotate(
            avg_rating=Avg('reviews__rating')
        ).order_by('-avg_rating', '-views')[:10]
        
        self.distances = {}
        
        if lat and lng:
            try:
                user_lat = float(lat)
                user_lng = float(lng)
                import math
                def haversine_distance(lat1, lon1, lat2, lon2):
                    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                    c = 2 * math.asin(math.sqrt(a))
                    return c * 6371 # km

                all_avail = list(base_qs)
                valid_props = []
                for p in all_avail:
                    if p.latitude is not None and p.longitude is not None:
                        p.distance = haversine_distance(user_lat, user_lng, p.latitude, p.longitude)
                        valid_props.append(p)
                
                # Filter by radius if specified
                if radius_param:
                    try:
                        max_radius = float(radius_param)
                        valid_props = [p for p in valid_props if p.distance <= max_radius]
                    except ValueError:
                        pass

                # Sort closest first
                valid_props.sort(key=lambda p: p.distance)
                
                self.distances = {p.id: p.distance for p in valid_props}
                
                # Convert back to queryset preserving order
                sorted_ids = [p.id for p in valid_props[:10]]
                if sorted_ids:
                    from django.db.models import Case, When
                    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(sorted_ids)])
                    popular_nearby_qs = Property.objects.filter(id__in=sorted_ids).order_by(preserved).annotate(
                        avg_rating=Avg('reviews__rating')
                    )
                else:
                    popular_nearby_qs = Property.objects.none()
            except ValueError:
                pass
        
        # Serialize recommended
        rec_serializer = PropertyListSerializer(recommended_qs, many=True, context={'request': request, 'view': self})
        
        # Serialize popular nearby
        near_serializer = PropertyListSerializer(popular_nearby_qs, many=True, context={'request': request, 'view': self})
        
        return Response({
            "status": 200,
            "success": True,
            "message": "Home sections fetched successfully",
            "data": {
                "recommended": rec_serializer.data,
                "popular_nearby": near_serializer.data
            }
        })

class RecommendedPropertiesView(views.APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyListSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter('type', OpenApiTypes.STR, description='Property type (ANY, HOUSE, etc.)', required=False),
            OpenApiParameter('search', OpenApiTypes.STR, required=False),
            OpenApiParameter('start_date', OpenApiTypes.STR, required=False),
            OpenApiParameter('end_date', OpenApiTypes.STR, required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Availability status (AVAILABLE, BOOKED, ANY)', required=False),
            OpenApiParameter('availability', OpenApiTypes.STR, description='Availability status (AVAILABLE, BOOKED, ANY)', required=False),
            OpenApiParameter('sea_view', OpenApiTypes.BOOL, required=False),
            OpenApiParameter('bed', OpenApiTypes.INT, required=False),
            OpenApiParameter('bath', OpenApiTypes.INT, required=False),
        ]
    )
    def get(self, request):
        properties = Property.objects.all()
        properties = apply_property_filters(properties, request.query_params)
        
        properties = properties.annotate(
            avg_rating=Avg('reviews__rating')
        ).order_by('-views', '-avg_rating')
        
        serializer = PropertyListSerializer(properties, many=True, context={'request': request, 'view': self})
        return Response({
            "status": 200,
            "success": True,
            "message": "Recommended properties fetched successfully",
            "data": serializer.data
        })

class PopularNearbyPropertiesView(views.APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyListSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter('type', OpenApiTypes.STR, description='Property type (ANY, HOUSE, etc.)', required=False),
            OpenApiParameter('search', OpenApiTypes.STR, required=False),
            OpenApiParameter('start_date', OpenApiTypes.STR, required=False),
            OpenApiParameter('end_date', OpenApiTypes.STR, required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Availability status (AVAILABLE, BOOKED, ANY)', required=False),
            OpenApiParameter('availability', OpenApiTypes.STR, description='Availability status (AVAILABLE, BOOKED, ANY)', required=False),
            OpenApiParameter('sea_view', OpenApiTypes.BOOL, required=False),
            OpenApiParameter('bed', OpenApiTypes.INT, required=False),
            OpenApiParameter('bath', OpenApiTypes.INT, required=False),
            OpenApiParameter('latitude', OpenApiTypes.FLOAT, description='Latitude for proximity search', required=False),
            OpenApiParameter('longitude', OpenApiTypes.FLOAT, description='Longitude for proximity search', required=False),
            OpenApiParameter('radius', OpenApiTypes.FLOAT, description='Search radius in kilometers', required=False),
        ]
    )
    def get(self, request):
        properties = Property.objects.all()
        properties = apply_property_filters(properties, request.query_params)
        
        lat = request.query_params.get('latitude')
        lng = request.query_params.get('longitude')
        radius_param = request.query_params.get('radius')
        
        self.distances = {}
        
        if lat and lng:
            try:
                user_lat = float(lat)
                user_lng = float(lng)
                import math
                def haversine_distance(lat1, lon1, lat2, lon2):
                    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                    c = 2 * math.asin(math.sqrt(a))
                    return c * 6371 # km

                property_list = list(properties)
                valid_properties = []
                for p in property_list:
                    if p.latitude is not None and p.longitude is not None:
                        p.distance = haversine_distance(user_lat, user_lng, p.latitude, p.longitude)
                        valid_properties.append(p)
                
                if radius_param:
                    try:
                        max_radius = float(radius_param)
                        valid_properties = [p for p in valid_properties if p.distance <= max_radius]
                    except ValueError:
                        pass
                        
                valid_properties.sort(key=lambda p: p.distance)
                self.distances = {p.id: p.distance for p in valid_properties}
                
                sorted_ids = [p.id for p in valid_properties]
                if sorted_ids:
                    from django.db.models import Case, When
                    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(sorted_ids)])
                    properties = Property.objects.filter(id__in=sorted_ids).order_by(preserved)
                else:
                    properties = Property.objects.none()
            except ValueError:
                pass
        else:
            properties = properties.order_by('-views')

        properties = properties.annotate(avg_rating=Avg('reviews__rating'))
        serializer = PropertyListSerializer(properties, many=True, context={'request': request, 'view': self})
        return Response({
            "status": 200,
            "success": True,
            "message": "Popular nearby properties fetched successfully",
            "data": serializer.data
        })

class FavouritePropertyView(views.APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyListSerializer
    
    def post(self, request, property_id):
        try:
            property_obj = Property.objects.get(id=property_id)
        except Property.DoesNotExist:
            return Response({"success": False, "message": "Property not found"}, status=status.HTTP_404_NOT_FOUND)
            
        obj, created = Favourites.objects.get_or_create(
            property=property_obj,
            user=request.user
        )
        
        if not created:
            obj.delete()
            message = "Property unfavourited successfully"
        else:
            message = "Property favourited successfully"
            
        return Response({"success": True, "message": message}, status=status.HTTP_200_OK)
        
    def get(self, request, property_id=None):
        if property_id is not None:
            is_fav = Favourites.objects.filter(user=request.user, property_id=property_id).exists()
            return Response({
                "status": 200,
                "success": True,
                "favourite": is_fav
            }, status=status.HTTP_200_OK)

        favourite_properties = Favourites.objects.filter(user=request.user).select_related('property')
        properties = [fav.property for fav in favourite_properties]
        # Annotate with avg_rating
        for p in properties:
            review_stats = p.reviews.aggregate(Avg('rating'))
            p.avg_rating = review_stats['rating__avg'] or 0.0
            
        serializer = PropertyListSerializer(properties, many=True, context={'request': request})
        return Response({
            "status": 200, "message": "Favourite properties fetched successfully",
            "success": True, "data": serializer.data
        })

class PropertyOwnerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PropertyDetailSerializer
        return PropertyListSerializer
        
    def get_queryset(self):
        properties = Property.objects.filter(owner=self.request.user)
        
        status_param = self.request.query_params.get('status', 'ANY')
        search = self.request.query_params.get('search')
        if search:
            properties = properties.filter(Q(name__icontains=search) | Q(address__icontains=search))
            
        bed = self.request.query_params.get('bed')
        if bed:
            properties = properties.filter(bedroom=bed)
            
        bath = self.request.query_params.get('bath')
        if bath:
            properties = properties.filter(bathroom=bath)
            
        p_type = self.request.query_params.get('type', 'ANY')
        if p_type != 'ANY':
            properties = properties.filter(type=p_type)
            
        sea_view = self.request.query_params.get('sea_view')
        if sea_view and str(sea_view).lower() in ("true", "1"):
            properties = properties.filter(sea_view=True)
            
        from datetime import datetime
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        start_d = None
        end_d = None
        if start_date and end_date:
            try:
                start_d = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_d = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        if start_d and end_d:
            booked_property_ids = Booking.objects.filter(
                status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN'],
                check_in__lt=end_d,
                check_out__gt=start_d
            ).values_list('property_id', flat=True)
            
            if status_param == "AVAILABLE":
                properties = properties.exclude(id__in=booked_property_ids).exclude(status="CLOSED")
            elif status_param == "BOOKED":
                properties = properties.filter(id__in=booked_property_ids)
            elif status_param == "CLOSED":
                properties = properties.filter(status="CLOSED")
        else:
            if status_param == "AVAILABLE":
                properties = properties.filter(status__in=["AVAILABLE", "OPEN", "ACTIVE"])
            elif status_param == "BOOKED":
                properties = properties.filter(status="BOOKED")
            elif status_param == "CLOSED":
                properties = properties.filter(status="CLOSED")
                
        from django.db.models import Count, Value, DecimalField
        from django.db.models.functions import Coalesce
        from decimal import Decimal
        return properties.annotate(
            avg_rating=Coalesce(Avg('reviews__rating'), Value(Decimal('0.0')), output_field=DecimalField()),
            booking_count=Count('booking', filter=~Q(booking__status='CANCELLED'))
        ).order_by('-booking_count', '-avg_rating')

    @extend_schema(
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, required=False),
            OpenApiParameter('type', OpenApiTypes.STR, required=False),
            OpenApiParameter('search', OpenApiTypes.STR, required=False),
            OpenApiParameter('start_date', OpenApiTypes.STR, required=False),
            OpenApiParameter('end_date', OpenApiTypes.STR, required=False),
            OpenApiParameter('sea_view', OpenApiTypes.BOOL, required=False),
            OpenApiParameter('bed', OpenApiTypes.INT, required=False),
            OpenApiParameter('bath', OpenApiTypes.INT, required=False),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Calculate overall metrics for the owner's properties
        owner_properties = Property.objects.filter(owner=request.user)
        num_properties = owner_properties.count()
        
        # 1. Occupancy Rate
        total_booked_days = 0
        if num_properties > 0:
            from datetime import date, timedelta
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            # Fetch overlapping bookings
            overlapping_bookings = Booking.objects.filter(
                property__owner=request.user,
                status__in=['CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT'],
                check_in__lt=end_date,
                check_out__gt=start_date
            )
            for booking in overlapping_bookings:
                overlap_start = max(booking.check_in, start_date)
                overlap_end = min(booking.check_out, end_date)
                overlap_days = (overlap_end - overlap_start).days
                if overlap_days > 0:
                    total_booked_days += overlap_days
            
            total_capacity_days = num_properties * 30
            occupancy_rate = (total_booked_days / total_capacity_days) * 100
        else:
            occupancy_rate = 0.0
            
        # 2. Total Bookings (non-cancelled)
        total_bookings = Booking.objects.filter(property__owner=request.user).exclude(status='CANCELLED').count()
        
        # 3. Pending Requests
        pending_requests = Booking.objects.filter(property__owner=request.user, status='PENDING').count()
        
        # 4. Avg. Rating
        reviews = Review.objects.filter(property__owner=request.user)
        reviews_count = reviews.count()
        if reviews_count > 0:
            avg_rating = sum(r.rating for r in reviews) / reviews_count
        else:
            avg_rating = 0.0

        # Build list of properties
        data = []
        for prop in queryset:
            avg = getattr(prop, 'avg_rating', 0.0) or 0.0
            data.append({
                "id": prop.id,
                "status": prop.status,
                "name": prop.name,
                "bedroom": prop.bedroom,
                "bathroom": prop.bathroom,
                "type": prop.type,
                "area": prop.area,
                "price_monthly": prop.price_monthly,
                "price_daily": prop.price_daily,
                "cover": prop.cover_image.url if prop.cover_image else "",
                "avg_rating": f"{avg:.1f}",
                "address": prop.address
            })
            
        return Response({
            "status": 200, 
            "message": "Properties fetched successfully",
            "success": True, 
            "occupancy_rate": f"{occupancy_rate:.0f}%",
            "total_bookings": total_bookings,
            "pending_requests": pending_requests,
            "avg_rating": f"{avg_rating:.1f}",
            "properties": data
        })

    def retrieve(self, request, *args, **kwargs):
        property_id = kwargs.get('pk')
        prop = Property.objects.select_related('owner').filter(id=property_id, owner=request.user).first()
        if not prop:
            return Response({"status": 404, "success": False, "message": "Property not found"}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = PropertyDetailSerializer(prop, context={'request': request})
        bookings = Booking.objects.filter(property=prop)
        total_bookings = bookings.exclude(status='CANCELLED').count()
        
        # Calculate occupancy rate for this property over the last 30 days
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Overlapping bookings
        overlapping_bookings = bookings.filter(
            status__in=['CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT'],
            check_in__lt=end_date,
            check_out__gt=start_date
        )
        total_booked_days = 0
        for booking in overlapping_bookings:
            overlap_start = max(booking.check_in, start_date)
            overlap_end = min(booking.check_out, end_date)
            overlap_days = (overlap_end - overlap_start).days
            if overlap_days > 0:
                total_booked_days += overlap_days
        
        occupancy_rate = (total_booked_days / 30.0) * 100
        
        # Avg stay
        non_cancelled_bookings = bookings.exclude(status='CANCELLED')
        nc_count = non_cancelled_bookings.count()
        if nc_count > 0:
            avg_stay = sum((b.check_out - b.check_in).days for b in non_cancelled_bookings) / nc_count
        else:
            avg_stay = 0.0

        # Avg rating
        reviews = prop.reviews.all()
        reviews_count = reviews.count()
        if reviews_count > 0:
            avg_rating = sum(r.rating for r in reviews) / reviews_count
        else:
            avg_rating = 0.0
        
        return Response({
            "status": 200, 
            "message": "Property details fetched successfully",
            "success": True, 
            "occupancy": f"{occupancy_rate:.0f}%",
            "occupancy_rate": f"{occupancy_rate:.0f}%",
            "total_bookings": total_bookings, 
            "avg_stay": f"{avg_stay:.1f} days",
            "avg_stay_duration": f"{avg_stay:.1f} days",
            "avg_rating": f"{avg_rating:.1f}",
            "total_views": prop.views,
            "property": serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        property_id = kwargs.get('pk')
        try:
            prop = Property.objects.get(id=property_id, owner=request.user)
            prop.delete()
            return Response({"status": 200, "success": True, "message": "Property deleted successfully"})
        except Property.DoesNotExist:
            return Response({"status": 404, "success": False, "message": "Property not found"}, status=status.HTTP_404_NOT_FOUND)

import json
class BasePropertyMutationView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def parse_json_field(self, val):
        if not val: return []
        if isinstance(val, str):
            try:
                loaded = json.loads(val)
                if isinstance(loaded, list): return loaded
                elif isinstance(loaded, dict): return [loaded]
            except Exception:
                return [val] if val else []
        if isinstance(val, list):
            res = []
            for item in val:
                if isinstance(item, dict): res.append(item)
                elif isinstance(item, str):
                    try:
                        loaded = json.loads(item)
                        if isinstance(loaded, dict): res.append(loaded)
                        elif isinstance(loaded, list): res.extend(loaded)
                        else: res.append(item)
                    except Exception:
                        res.append(item)
                else: res.append(item)
            return res
        return []

    def parse_single_json_field(self, val):
        if not val: return None
        if isinstance(val, dict): return val
        if isinstance(val, str):
            try:
                loaded = json.loads(val)
                if isinstance(loaded, dict): return loaded
                if isinstance(loaded, list) and len(loaded) > 0 and isinstance(loaded[0], dict): return loaded[0]
            except Exception:
                pass
        return None

    def safe_getlist(self, request, key):
        if hasattr(request.data, "getlist"):
            return request.data.getlist(key)
        val = request.data.get(key)
        if val is None: return []
        return val if isinstance(val, list) else [val]

class CreatePropertyDRF(BasePropertyMutationView):
    serializer_class = PropertySerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    
    @extend_schema(request=PropertySerializer, responses={200: dict})
    def post(self, request):


        gallery_raw = request.data.get("gallery") or self.safe_getlist(request, "gallery")
        gallery_parsed = self.parse_json_field(gallery_raw)
        gallery_files = request.FILES.getlist("gallery_files") or request.FILES.getlist("gallery")
        
        gallery = []
        if gallery_parsed not in (["string"], [""]):
            for index, item in enumerate(gallery_parsed):
                g_item = item.copy() if isinstance(item, dict) else {"type": item}
                if "file" not in g_item and index < len(gallery_files):
                    g_item["file"] = gallery_files[index]
                gallery.append(g_item)

        data = {k: v for k, v in request.data.items()}
        
        # Clean up Swagger defaults for Create just like Update
        for key in list(data.keys()):
            val = data[key]
            if val in ("", "string", ["string"], [""]) and key not in ["verified", "sea_view", "cover", "name", "address"]:
                del data[key]
            elif val == 0 and key in ["bathroom", "bedroom", "views", "latitude", "longitude", "discount"]:
                del data[key]
                
        cover = request.FILES.get("cover") or request.data.get("cover")
        if isinstance(cover, str) and cover in ("", "string"):
            cover = None

        def clean_prices(field_name):
            parsed = self.parse_json_field(request.data.get(field_name) or self.safe_getlist(request, field_name))
            if parsed and isinstance(parsed, list) and isinstance(parsed[0], str):
                return []
            return parsed

        data.update({
            "owner": request.user.id,
            "cover": cover,
            "gallery": gallery,
            "add_ons_prices": clean_prices("add_ons_prices"),
            "amenities": clean_prices("amenities"),
            "activities": clean_prices("activities"),
            "weekend_dates": self.parse_single_json_field(request.data.get("weekend_dates")),
            "vacations": self.parse_single_json_field(request.data.get("vacations")),
            "other_charges": clean_prices("other_charges"),
            "verified": str(request.data.get("verified", "true")).lower() in ("true", "1"),
            "sea_view": str(request.data.get("sea_view", "false")).lower() in ("true", "1")
        })
        
        # Remove keys that ended up as empty lists if they aren't required, so serializer doesn't complain if they are invalid
        for k in ["gallery", "add_ons_prices", "amenities", "activities", "weekend_dates", "vacations", "other_charges", "cover"]:
            if not data.get(k):
                data.pop(k, None)
        
        serializer = PropertySerializer(data=data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response({"status": 200, "success": True, "message": "Property created successfully"})
        return Response({"status": 400, "success": False, "message": "Invalid data", "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


class UpdatePropertyDRF(BasePropertyMutationView):
    serializer_class = PropertySerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    
    @extend_schema(request=PropertySerializer, responses={200: dict})
    def patch(self, request, property_id):
        try:
            property_obj = Property.objects.get(id=property_id, owner=request.user)
        except Property.DoesNotExist:
            return Response({"status": 404, "success": False, "message": "Property not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)

        data = {k: v for k, v in request.data.items()}
        
        # Clean up Swagger default values so partial=True works correctly
        for key in list(data.keys()):
            val = data[key]
            if val in ("", "string", ["string"], [""]) and key not in ["verified", "sea_view", "cover"]:
                del data[key]
            elif val == 0 and key in ["bathroom", "bedroom", "views", "latitude", "longitude", "discount"]:
                del data[key]
        
        # Prevent owner from being updated
        data.pop("owner", None)
            
        if "verified" in request.data: data["verified"] = str(request.data.get("verified")).lower() in ("true", "1")
        if "sea_view" in request.data: data["sea_view"] = str(request.data.get("sea_view")).lower() in ("true", "1")
        
        # Handle cover image properly (ignore string URLs or Swagger defaults)
        if "cover" in request.FILES: 
            data["cover"] = request.FILES.get("cover") 
        elif "cover" in data:
            data.pop("cover", None)



        if "gallery" in request.data or "gallery_files" in request.FILES:
            gallery_parsed = self.parse_json_field(request.data.get("gallery") or self.safe_getlist(request, "gallery"))
            if gallery_parsed in (["string"], [""]):
                data.pop("gallery", None)
            else:
                gallery_files = request.FILES.getlist("gallery_files") or request.FILES.getlist("gallery")
                gallery = []
                for index, item in enumerate(gallery_parsed):
                    g_item = item.copy() if isinstance(item, dict) else {"type": item}
                    if "file" not in g_item and index < len(gallery_files): g_item["file"] = gallery_files[index]
                    gallery.append(g_item)
                data["gallery"] = gallery

        for price_field in ["add_ons_prices", "other_charges", "amenities", "activities"]:
            if price_field in request.data:
                parsed = self.parse_json_field(request.data.get(price_field) or self.safe_getlist(request, price_field))
                if parsed and isinstance(parsed, list) and isinstance(parsed[0], str) and parsed[0] in ("string", ""):
                    data.pop(price_field, None)  # Ignore Swagger default ["string"]
                else:
                    data[price_field] = parsed

        for single_field in ["weekend_dates", "vacations"]:
            if single_field in request.data:
                parsed = self.parse_single_json_field(request.data.get(single_field))
                if parsed:
                    data[single_field] = parsed
                else:
                    data.pop(single_field, None)

        serializer = PropertySerializer(instance=property_obj, data=data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response({"status": 200, "success": True, "message": "Property updated successfully"})
        return Response({"status": 400, "success": False, "message": "Invalid data", "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)



class UpdateGallery(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = GallerySerializer

    @extend_schema(responses={200: dict})
    def delete(self, request, media_id):
        Gallery.objects.filter(id=media_id).delete()
        return Response({"status": 200, "success": True, "message": "Gallery deleted successfully"})

    @extend_schema(request=GallerySerializer, responses={200: dict})
    def patch(self, request, media_id):
        Gallery.objects.filter(id=media_id).update(file=request.FILES.get("file"))
        return Response({"status": 200, "success": True, "message": "Gallery updated successfully"})





class ReportPropertyView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(responses={200: dict})
    def get(self, request):
        reports = Reports.objects.filter(user=request.user)
        serializer = ReportsSerializer(reports, many=True)
        return Response(serializer.data)

    @extend_schema(request=ReportsSerializer, responses={200: dict})
    def post(self, request):
        serializer = ReportsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({"status": 200, "success": True, "message": "Report submitted successfully"})
        return Response({"status": 400, "success": False, "message": "Invalid data", "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)



class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "status": 200,
            "success": True,
            "message": "Top performing properties fetched successfully",
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "data": data
        })

class TopPerformingView(views.APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyListSerializer
    pagination_class = CustomPageNumberPagination

    @extend_schema(
        parameters=[
            OpenApiParameter('page', OpenApiTypes.INT, description='A page number within the paginated result set.', required=False),
            OpenApiParameter('page_size', OpenApiTypes.INT, description='Number of results to return per page.', required=False),
        ],
        responses={200: dict}
    )
    def get(self, request):
        from django.db.models import Avg
        properties = Property.objects.filter(status="AVAILABLE").annotate(
            avg_rating=Avg('reviews__rating')
        ).order_by('-views')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(properties, request, view=self)
        if page is not None:
            serializer = self.serializer_class(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
            
        serializer = self.serializer_class(properties, many=True, context={'request': request})
        return Response({
            "status": 200,
            "success": True,
            "message": "Top performing properties fetched successfully",
            "data": serializer.data
        })