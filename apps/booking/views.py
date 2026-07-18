import datetime
from django.db.models import Avg
from django.conf import settings
from rest_framework import views, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .utils import get_final_discount_price_for_booking
from apps.auth.utils import format_serializer_errors

from .models import Booking
from apps.property.models import Property
from apps.auth.models import Document
from .serializers import (
    CreateBookingSerializer, BookingListSerializer, BookingDetailsSerializer,
    MyBookingListSerializer
)

class CalculateBookingPriceView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('property_id', OpenApiTypes.UUID, required=True),
            OpenApiParameter('price_type', OpenApiTypes.STR, required=True, description="daily or monthly"),
            OpenApiParameter('start_date', OpenApiTypes.STR, required=True, description="YYYY-MM-DD"),
            OpenApiParameter('end_date', OpenApiTypes.STR, required=True, description="YYYY-MM-DD"),
            OpenApiParameter('selected_addon_ids', OpenApiTypes.STR, required=False, description="Comma separated IDs of addons"),
        ],
        responses={200: dict}
    )
    def get(self, request):
        property_id = request.query_params.get('property_id')
        if not property_id:
            return Response({"success": False, "message": "property_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        price_type = request.query_params.get('price_type', 'daily')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        addons_str = request.query_params.get('selected_addon_ids')
        selected_addon_ids = [aid.strip() for aid in addons_str.split(",")] if addons_str else []

        try:
            prop = Property.objects.get(id=property_id)
            if not prop.verified and prop.owner != request.user:
                return Response({"success": False, "message": "Property not found"}, status=status.HTTP_404_NOT_FOUND)
            
            breakdown = get_final_discount_price_for_booking(
                property_obj_or_id=prop, 
                price_type=price_type, 
                selected_addon_ids=selected_addon_ids,
                start_date=start_date,
                end_date=end_date
            )
            
            unit_price = breakdown["final_unit_price"]
            
            # Calculate total duration if dates provided
            total_duration = 1
            if start_date and end_date:
                try:
                    s_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
                    e_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
                    if price_type == 'daily':
                        delta = (e_date - s_date).days
                        if delta > 0:
                            total_duration = delta
                    elif price_type == 'monthly':
                        months = (e_date.year - s_date.year) * 12 + e_date.month - s_date.month
                        if months > 0:
                            total_duration = months
                except ValueError:
                    pass
                 
            from apps.others.utils import get_user_currency_and_rate
            code, symbol, rate = get_user_currency_and_rate(request)

            total_price = round(unit_price * total_duration * rate, 2)
            
            # Multiply all breakdown elements by duration and rate for total transparency
            total_breakdown = {
                "base_price_total": round(breakdown["base_price"] * total_duration * rate, 2),
                "other_charges": [
                    {
                        "name": c["name"],
                        "percentage": round(c["percentage"] * rate, 2),
                        "amount": round(c["amount"] * rate, 2),
                        "total_amount": round(c["amount"] * total_duration * rate, 2)
                    }
                    for c in breakdown["other_charges"]
                ],
                "other_charges_total": round(breakdown["other_charges_total"] * total_duration * rate, 2),
                "add_ons": [
                    {
                        "name": a["name"],
                        "percentage": round(a["percentage"] * rate, 2),
                        "amount": round(a["amount"] * rate, 2),
                        "total_amount": round(a["amount"] * total_duration * rate, 2)
                    }
                    for a in breakdown["add_ons"]
                ],
                "add_ons_total": round(breakdown["add_ons_total"] * total_duration * rate, 2),
                "vacation_surcharge_total": round(breakdown["vacation_surcharge"] * total_duration * rate, 2),
                "weekend_surcharge_total": round(breakdown["weekend_surcharge"] * total_duration * rate, 2),
                "discount_total": round(breakdown["discount_amount"] * total_duration * rate, 2),
                "total_amount_before_discount": round(breakdown["total_before_discount"] * total_duration * rate, 2)
            }
            
            return Response({
                "success": True,
                "message": "Price calculated successfully",
                "price_type": price_type,
                "total_duration": total_duration,
                "base_unit_price": round(breakdown["base_price"] * rate, 2),
                "breakdown": total_breakdown,
                "unit_price_after_discount": round(unit_price * rate, 2),
                "total_price": total_price,
                "currency_code": code,
                "currency_symbol": symbol
            })
            
        except Property.DoesNotExist:
            return Response({"success": False, "message": "Property not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)



from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class GuestBookingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_queryset(self):
        queryset = Booking.objects.filter(user=self.request.user).select_related('property').annotate(
            property_avg_rating=Avg('property__reviews__rating')
        )
        status_param = self.request.query_params.get('status')
        if status_param:
            status_param = status_param.upper()
            if status_param == 'ACTIVE':
                queryset = queryset.filter(status__in=['CONFIRMED', 'CHECKED_IN'])
            elif status_param == 'PENDING':
                queryset = queryset.filter(status='PENDING')
            elif status_param == 'CANCEL' or status_param == 'CANCELLED':
                queryset = queryset.filter(status='CANCELLED')
            elif status_param != 'ALL':
                queryset = queryset.filter(status=status_param)
        return queryset
        

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateBookingSerializer
        if self.action == 'retrieve':
            return BookingDetailsSerializer
        return BookingListSerializer


    @extend_schema(request=CreateBookingSerializer)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            property_id = request.data.get('property')
            prop = Property.objects.select_related('owner').filter(id=property_id).first()
            if not prop or (not prop.verified and prop.owner != request.user):
                return Response({"status": 404, "success": False, "message": "Property not found"}, status=status.HTTP_404_NOT_FOUND)
                
            price_type = request.data.get('price_type', 'daily')
            addons_str = request.data.get('selected_addon_ids')
            if isinstance(addons_str, str):
                selected_addon_ids = [aid.strip() for aid in addons_str.split(",")] if addons_str else []
            elif isinstance(addons_str, list):
                selected_addon_ids = addons_str
            else:
                selected_addon_ids = []
                
            check_in = request.data.get('check_in')
            check_out = request.data.get('check_out')
            
            try:
                breakdown = get_final_discount_price_for_booking(
                    property_obj_or_id=prop,
                    price_type=price_type,
                    selected_addon_ids=selected_addon_ids,
                    start_date=check_in,
                    end_date=check_out
                )
                unit_price = breakdown["final_unit_price"]
                
                total_duration = 1
                if check_in and check_out:
                    s_date = datetime.datetime.strptime(check_in, "%Y-%m-%d").date()
                    e_date = datetime.datetime.strptime(check_out, "%Y-%m-%d").date()
                    if price_type == 'daily':
                        delta = (e_date - s_date).days
                        if delta > 0: total_duration = delta
                    elif price_type == 'monthly':
                        months = (e_date.year - s_date.year) * 12 + e_date.month - s_date.month
                        if months > 0: total_duration = months
                        
                final_price = unit_price * total_duration
            except Exception as e:
                print(f"Error calculating final price: {e}")
                final_price = prop.price or 0.0
                
            booking = serializer.save(
                user=request.user,
                price=final_price
            )
            
            # --- Save Documents ---
            doc_files = request.FILES.getlist('document_file')
            if hasattr(request.data, 'getlist'):
                doc_types = request.data.getlist('document_type')
            else:
                dt = request.data.get('document_type')
                doc_types = [dt] if dt else []
                
            for i, f in enumerate(doc_files):
                dtype = doc_types[i] if i < len(doc_types) else 'NID'
                Document.objects.create(
                    user=request.user,
                    document_type=dtype,
                    document_file=f
                )
            # ----------------------
            
            try:
                from apps.notify.utils import booking_reminder
                booking_reminder(prop.owner, booking)
            except Exception as e:
                print(f"Error calling booking_reminder: {e}")
                
            booking_serializer = BookingListSerializer(booking, context={'request': request})
            return Response({
                "status": 200, "success": True, "message": "Booking created successfully",
                "data": booking_serializer.data
            })
        return Response({"status": 400, "success": False, "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        for b in queryset:
            b.property.avg_rating = getattr(b, 'property_avg_rating', 0.0) or 0.0
            
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response({
            "status": 200, "success": True, "message": "Booking list fetched successfully",
            "data": serializer.data
        })


    def retrieve(self, request, *args, **kwargs):
        booking_id = kwargs.get('pk')
        booking = Booking.objects.filter(id=booking_id, user=request.user).select_related('property', 'property__owner').annotate(
            property_avg_rating=Avg('property__reviews__rating')
        ).first()
        
        if not booking:
            return Response({"status": 404, "success": False, "message": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
            
        booking.property.avg_rating = getattr(booking, 'property_avg_rating', 0.0) or 0.0
        
        serializer = self.get_serializer(booking, context={'request': request})
        
        from apps.auth.models import Document
        from apps.auth.serializers import UploadDocumentSerializer
        docs = Document.objects.filter(user=booking.user)
        docs_data = UploadDocumentSerializer(docs, many=True).data
        
        return Response({
            "status": 200, "success": True, "message": "Booking details fetched successfully",
            "data": serializer.data,
            "docs": docs_data
        })



class CancelBookingView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, booking_id):
        booking = Booking.objects.filter(id=booking_id, user=request.user).first()
        if not booking:
            return Response({"status": 404, "success": False, "message": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if booking.status == "CANCELLED":
            return Response({"status": 400, "success": False, "message": "Booking already cancelled"}, status=status.HTTP_400_BAD_REQUEST)
            
        booking.status = "CANCELLED"
        booking.save()
        return Response({"status": 200, "success": True, "message": "Booking cancelled successfully"})

class ConfirmBookingView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, booking_id):
        booking = Booking.objects.filter(id=booking_id, property__owner=request.user).first()
        if not booking:
            return Response({"status": 404, "success": False, "message": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if booking.status == "CONFIRMED":
            return Response({"status": 400, "success": False, "message": "Booking already confirmed"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check for conflicting confirmed/checked-in bookings for the same property
        conflicting_booking_exists = Booking.objects.filter(
            property=booking.property,
            status__in=['CONFIRMED', 'CHECKED_IN'],
            check_in__lt=booking.check_out,
            check_out__gt=booking.check_in
        ).exclude(id=booking.id).exists()
        
        if conflicting_booking_exists:
            return Response({
                "status": 400,
                "success": False,
                "message": "Cannot confirm booking due to date conflict with another confirmed booking."
            }, status=status.HTTP_400_BAD_REQUEST)
            
        booking.status = "CONFIRMED"
        booking.save()
        
        try:
            from apps.notify.utils import send_booking_status_notification
            send_booking_status_notification(booking)
        except Exception as e:
            print(f"Error calling send_booking_status_notification: {e}")
            
        return Response({"status": 200, "success": True, "message": "Booking confirmed successfully, and guest documents auto-approved"})


class DeclineBookingView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, booking_id):
        booking = Booking.objects.filter(id=booking_id, property__owner=request.user).first()
        if not booking:
            return Response({"status": 404, "success": False, "message": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if booking.status == "DECLINED":
            return Response({"status": 400, "success": False, "message": "Booking already declined"}, status=status.HTTP_400_BAD_REQUEST)
            
        booking.status = "DECLINED"
        booking.save()
        
        try:
            from apps.notify.utils import send_booking_status_notification
            send_booking_status_notification(booking)
        except Exception as e:
            print(f"Error calling send_booking_status_notification: {e}")
            
        return Response({"status": 200, "success": True, "message": "Booking declined successfully"})



class OwnerBookingViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BookingDetailsSerializer
        return MyBookingListSerializer
        
    def get_queryset(self):
        status_param = self.request.query_params.get('status')
        bookings = Booking.objects.filter(property__owner=self.request.user).select_related('property')
        if status_param:
            bookings = bookings.filter(status=status_param)
        return bookings

    @extend_schema(parameters=[OpenApiParameter('status', OpenApiTypes.STR, required=False)])
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = MyBookingListSerializer(queryset, many=True, context={'request': request})
        return Response({
            "status": 200, "success": True, "message": "Booking list fetched successfully",
            "count": len(serializer.data), "data": serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        booking_id = kwargs.get('pk')
        booking = Booking.objects.filter(id=booking_id, property__owner=request.user).select_related('property', 'property__owner', 'user').annotate(
            property_avg_rating=Avg('property__reviews__rating')
        ).first()
        
        if not booking:
            return Response({"status": 404, "success": False, "message": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
            
        booking.property.avg_rating = getattr(booking, 'property_avg_rating', 0.0) or 0.0
        
        from apps.auth.serializers import UploadDocumentSerializer
        docs_data = UploadDocumentSerializer(Document.objects.filter(user=booking.user), many=True).data
        
        serializer = BookingDetailsSerializer(booking, context={'request': request})
        return Response({
            "status": 200, "success": True, "message": "Booking details fetched successfully",
            "data": serializer.data, "docs": docs_data
        })
