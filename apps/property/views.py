from rest_framework import views, status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
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

class PropertyGuestViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] # Originally IsAuthenticated in Bolt
    serializer_class = PropertyListSerializer
    
    def get_queryset(self):
        properties = Property.objects.all()
        
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
            properties = properties.exclude(id__in=booked_property_ids).exclude(status="CLOSED")
        else:
            properties = properties.filter(status="AVAILABLE")
            
        return properties.annotate(avg_rating=Avg('reviews__rating'))

    @extend_schema(
        parameters=[
            OpenApiParameter('type', OpenApiTypes.STR, description='Property type (ANY, HOUSE, etc.)', required=False),
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
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response({
            "status": 200, "message": "Properties fetched successfully", 
            "success": True, "data": serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        property_id = kwargs.get('pk')
        prop = Property.objects.select_related('owner').filter(id=property_id).first()
        if not prop:
            return Response({"status": 404, "success": False, "message": "Property not found"}, status=status.HTTP_404_NOT_FOUND)
        
        Property.objects.filter(id=property_id).update(views=F('views') + 1)
        prop.refresh_from_db()
        
        serializer = PropertyDetailSerializer(prop, context={'request': request})
        return Response(serializer.data)

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
        
    def get(self, request):
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
                
        return properties.annotate(avg_rating=Avg('reviews__rating'))

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
        # The schema expected id, cover, name, address, avg_rating
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
                "cover": f"{settings.BACKEND_URI}{prop.cover_image.url}" if prop.cover_image else "",
                "avg_rating": f"{avg:.1f}",
                "address": prop.address
            })
        return Response({
            "status": 200, "message": "Properties fetched successfully",
            "success": True, "properties": data
        })

    def retrieve(self, request, *args, **kwargs):
        property_id = kwargs.get('pk')
        prop = Property.objects.select_related('owner').filter(id=property_id, owner=request.user).first()
        if not prop:
            return Response({"status": 404, "success": False, "message": "Property not found"}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = PropertyDetailSerializer(prop, context={'request': request})
        total_bookings = Booking.objects.filter(property=prop).count()
        
        return Response({
            "status": 200, "message": "Property details fetched successfully",
            "success": True, "occupancy": "Not Implemented Yet",
            "total_bookings": total_bookings, "avg_stay": "Not Implemented Yet",
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
            "weekend_dates": self.parse_single_json_field(request.data.get("weekend_dates")),
            "vacations": self.parse_single_json_field(request.data.get("vacations")),
            "other_charges": clean_prices("other_charges"),
            "verified": str(request.data.get("verified", "true")).lower() in ("true", "1"),
            "sea_view": str(request.data.get("sea_view", "false")).lower() in ("true", "1")
        })
        
        # Remove keys that ended up as empty lists if they aren't required, so serializer doesn't complain if they are invalid
        for k in ["gallery", "add_ons_prices", "weekend_dates", "vacations", "other_charges", "cover"]:
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

        for price_field in ["add_ons_prices", "other_charges"]:
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